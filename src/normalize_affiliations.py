"""所属文字列を正規化し、組織名と業種を付ける。

`affil_openalex` は同じ組織でも表記がばらばら（1,529通り）で、そのままでは組織単位の集計ができない。
段階3-5 の説明変数（産学連携の有無、組織横断性）を作るための下ごしらえ。

方針:
  - 所属文字列は Scopus（正規化済み）→ OpenAlex（網羅的）→ Crossref の順に採用する。
  - `;` で機関ごとに割り、機関ごとに正規表現で「正式名」と「業種」を当てる。
  - 業種は大学・公的研究機関・病院を先に判定し、残った企業語（Inc. / Co., Ltd. など）を企業とする。
    順序が逆だと "XX University Hospital, Inc." のようなものを取り違える。
  - 豊田工業大学・豊田高専・刈谷豊田総合病院は名前にトヨタを含むがトヨタの研究所ではないので、
    トヨタ系から除く（`authorships.csv` の `is_toyota` と同じ扱い）。

入力: data/derived/papers/authorships.csv
出力: data/derived/papers/authorship_affiliations.csv … 1行＝著者1人（authorships.csv と同じ粒度）

実行: ~/.venvs/scisci-rir/bin/python src/normalize_affiliations.py
"""

from __future__ import annotations

import html
import re
import unicodedata
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
IN_CSV = ROOT / "data" / "derived" / "papers" / "authorships.csv"
OUT_CSV = ROOT / "data" / "derived" / "papers" / "authorship_affiliations.csv"

# トヨタ系の組織。上から順に当てるので、より限定的なものを先に置く
TOYOTA_RULES: list[tuple[str, str]] = [
    (r"toyota\s*central\s*(r\s*&?\s*d|rd|research)", "豊田中央研究所"),
    (r"\btytlabs\b", "豊田中央研究所"),
    (r"imra\s*america|imra,\s*america|imra\s*boulder", "IMRA America"),
    (r"imra\s*japan", "IMRA Japan"),
    (r"imra\s*europe", "IMRA Europe"),
    (r"toyota\s*motor\s*north\s*america", "Toyota Motor North America"),
    (r"toyota\s*motor\s*(europe|europa)", "Toyota Motor Europe"),
    (r"toyota\s*research\s*institute", "Toyota Research Institute"),
    (r"toyota\s*motor\s*(corp|company)|^toyota$|toyota\s*jidosha", "トヨタ自動車"),
    (r"\baisin\b", "アイシン"),
    (r"\bdenso\b", "デンソー"),
    (r"\bjtekt\b", "JTEKT"),
    (r"toyota\s*industries|豊田自動織機", "豊田自動織機"),
    (r"toyota\s*auto\s*body|トヨタ車体", "トヨタ車体"),
    (r"woven\s*(by|planet)\s*toyota", "Woven by Toyota"),
]

# 名前にトヨタを含むがトヨタの研究所ではないもの
TOYOTA_EXCLUDE = re.compile(
    r"toyota\s*technological\s*institute|豊田工業大学"
    r"|toyota\s*(national\s*)?college|豊田工業高等専門学校"
    r"|kariya\s*toyota|刈谷豊田",
    re.I)

SECTOR_RULES: list[tuple[str, str]] = [
    # 大学・高等教育を最初に見る
    (r"universit|univ\.|college|école|ecole polytech|hochschule|politec|\bkaist\b"
     r"|institute of technology|graduate school|school of (medicine|engineering|science)"
     r"|大学|学院", "university"),
    # 公的研究機関
    (r"national institute|national laborator|national research|advanced industrial science"
     r"|\baist\b|\bcnrs\b|\briken\b|\bjaea\b|\bnims\b|max planck|helmholtz|fraunhofer"
     r"|\bcsic\b|\bnasa\b|\bnrel\b|argonne|oak ridge|sandia|los alamos|brookhaven"
     r"|j-parc|synchrotron|spring-8|research organization|研究所（国立|国立研究開発", "government"),
    # 医療機関（Medical School は上で大学に落ちている）
    (r"hospital|medical cent|clinic\b|病院|医療センター", "hospital"),
    # 企業
    (r"\binc\b|\bco\.,?\s*ltd|corporation|\bcorp\b|\bgmbh\b|\bltd\b|\bllc\b|\bs\.?a\.?s\b"
     r"|\bb\.?v\.?\b|company|株式会社|有限会社|\bag\b|\bplc\b", "company"),
]


def norm(s: str) -> str:
    """HTML実体参照・全角・余分な空白を吸収する。"""
    t = html.unescape(html.unescape(str(s)))  # &amp;#x26; のような二重エスケープがある
    t = unicodedata.normalize("NFKC", t)
    return re.sub(r"\s+", " ", t).strip()


def classify(inst: str) -> tuple[str | None, str]:
    """機関文字列1つから (トヨタ系の正式名 or None, 業種) を返す。"""
    t = norm(inst)
    low = t.lower()
    toyota = None
    if not TOYOTA_EXCLUDE.search(low):
        for pat, name in TOYOTA_RULES:
            if re.search(pat, low):
                toyota = name
                break
    for pat, sector in SECTOR_RULES:
        if re.search(pat, low):
            return toyota, sector
    return toyota, ("company" if toyota else "other")


def main() -> int:
    a = pd.read_csv(IN_CSV)
    a["affil_best"] = a["affil_scopus"].fillna(a["affil_openalex"]).fillna(a["affil_crossref"])
    a["affil_source"] = (
        a["affil_scopus"].notna().map({True: "scopus", False: None})
        .fillna(a["affil_openalex"].notna().map({True: "openalex", False: None}))
        .fillna(a["affil_crossref"].notna().map({True: "crossref", False: None}))
    )

    toyota_orgs, sectors = [], []
    for s in a["affil_best"]:
        if not isinstance(s, str):
            toyota_orgs.append(None)
            sectors.append(None)
            continue
        # 正規化を先に済ませてから割る。&#x0026; のような実体参照に ; が含まれるので、
        # 先に割ると "Toyota Central R&#x0026" と "D Labs..." に分断されてしまう
        s_norm = norm(s)
        insts = [x for x in re.split(r";", s_norm) if len(x.strip()) > 3] or [s_norm]
        ts, ss = [], []
        for inst in insts:
            t, sec = classify(inst)
            if t:
                ts.append(t)
            ss.append(sec)
        toyota_orgs.append("|".join(dict.fromkeys(ts)) or None)
        sectors.append("|".join(dict.fromkeys(ss)) or None)

    a["toyota_org"] = toyota_orgs
    a["sectors"] = sectors
    for sec in ("university", "company", "government", "hospital"):
        a[f"is_{sec}"] = a["sectors"].fillna("").str.contains(sec)
    a["n_toyota_orgs"] = a["toyota_org"].fillna("").apply(lambda x: len(x.split("|")) if x else 0)
    # 収集元の4組織（中核）と、トヨタグループの他社を分ける。
    # `authorships.csv` の is_toyota は中核側の定義に近い
    CORE = {"豊田中央研究所", "IMRA America", "IMRA Japan", "IMRA Europe", "トヨタ自動車"}
    a["toyota_core"] = a["toyota_org"].fillna("").apply(
        lambda x: bool(CORE & set(x.split("|"))) if x else False)

    out = a[["paper_uid", "author_seq", "name_key", "affil_source", "affil_best",
             "toyota_org", "toyota_core", "n_toyota_orgs", "sectors",
             "is_university", "is_company", "is_government", "is_hospital", "is_toyota"]]
    out.to_csv(OUT_CSV, index=False)

    print(f"出力: {OUT_CSV.relative_to(ROOT)}  {len(out):,}行")
    print(f"\n所属文字列あり: {a['affil_best'].notna().sum():,} ({100*a['affil_best'].notna().mean():.1f}%)")
    print(f"業種を当てられた: {a['sectors'].notna().sum():,}")
    print(f"  うち other のみ: {(a['sectors']=='other').sum():,}")
    print("\nトヨタ系組織の内訳:")
    print(a["toyota_org"].dropna().str.split("|").explode().value_counts().to_string())
    print("\n業種の内訳（延べ）:")
    print(a["sectors"].dropna().str.split("|").explode().value_counts().to_string())
    print("\n既存 is_toyota との突き合わせ:")
    print(pd.crosstab(a["is_toyota"], a["toyota_org"].notna(),
                      rownames=["is_toyota"], colnames=["toyota_org あり"]).to_string())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
