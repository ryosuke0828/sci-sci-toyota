"""フェーズ4: 論文単位の著者レコードを研究者単位に集約する（名寄せ）。

入力: data/derived/paper_enrichment/crossref_authors.csv
出力: data/derived/researchers/
  - researchers.csv          … 1研究者1行
  - author_records_keyed.csv … 元レコードに名寄せキーと確信度を付けたもの
  - namekey_validation.json  … 名寄せ規則の精度をORCIDで実測した結果
  - researchers_summary.json

設計:
  著者識別子のうち OpenAlex Author ID と WoS ResearcherID は
  いずれも過剰併合していることを確認済み（2026-08-03）。
  実測でクリーンだったのは ORCID だけなので、ORCID を最上位の権威とする。

  ただし ORCID は全レコードの約24%にしか付いていないため、
  残りは氏名から作ったキーで寄せる。氏名キーは
  「姓 + 名の先頭イニシャル」とする。これで
  `Martin E. Fermann` / `M. E. Fermann` / `M.E. Fermann` が1人にまとまる。

  氏名キーは当然誤る（姓とイニシャルが同じ別人を併合する）ので、
  **ORCIDが付いているレコードを正解ラベルとして、その誤り率を実測する**。
  実測値を確信度の根拠にし、低確信度のクラスタは目視確認に回す。

実行: ~/.venvs/scisci-rir/bin/python src/aggregate_researchers.py
"""
from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
IN_AUTHORS = ROOT / "data" / "derived" / "paper_enrichment" / "crossref_authors.csv"
IN_PAPERS = ROOT / "data" / "derived" / "paper_enrichment" / "crossref_papers.csv"
IN_SCOPUS = ROOT / "data" / "derived" / "paper_enrichment" / "scopus_paper_authors.csv"
OUT_DIR = ROOT / "data" / "derived" / "researchers"


def norm(s) -> str:
    """全角半角・大文字小文字・記号を吸収する。"""
    if s is None or (isinstance(s, float) and pd.isna(s)):
        return ""
    t = unicodedata.normalize("NFKC", str(s)).lower()
    t = re.sub(r"[^0-9a-z぀-ヿ一-鿿 ]+", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def name_key(given, family) -> str:
    """姓 + 名の先頭イニシャル。表記ゆれ（ピリオド有無・イニシャル化）を吸収する。"""
    f = norm(family)
    g = norm(given)
    if not f:
        return ""
    initial = g[0] if g else ""
    return f"{f}|{initial}"


def full_key(given, family) -> str:
    """姓 + 名の全体。氏名キーより厳しく、同姓同名以外は分けない。"""
    return f"{norm(family)}|{norm(given)}"


def is_initials(g) -> bool:
    """`M. E.` や `M.E.` のようにイニシャルだけかを判定する。

    正規表現 `^([A-Za-z]\\.?\\s*)+$` は `Donald` のような普通の名前にも
    マッチしてしまう（1文字ずつの繰り返しで全体を消費するため）。
    トークンごとに1文字かを見る。
    """
    toks = [t for t in str(g).replace(".", ". ").split() if t]
    return bool(toks) and all(len(t.rstrip(".")) == 1 for t in toks)


def validate_namekey(df: pd.DataFrame) -> dict:
    """ORCIDを正解ラベルとして、氏名キーの過剰併合・過剰分割を実測する。"""
    o = df[df["orcid"].notna() & (df["name_key"] != "")]
    # 過剰併合: 1つの氏名キーに複数のORCIDがぶら下がる = 別人を1人にまとめている
    per_key = o.groupby("name_key")["orcid"].nunique()
    over_merged_keys = per_key[per_key > 1]
    # 過剰分割: 1つのORCIDが複数の氏名キーに割れる = 同一人物を別人にしている
    per_orcid = o.groupby("orcid")["name_key"].nunique()
    over_split_orcids = per_orcid[per_orcid > 1]

    # 比較のため、より厳しい「姓+名フル」キーでも同じ指標を出す
    per_key_full = o.groupby("full_key")["orcid"].nunique()
    per_orcid_full = o.groupby("orcid")["full_key"].nunique()

    return {
        "labeled_records": int(len(o)),
        "distinct_orcids": int(o["orcid"].nunique()),
        "name_key": {
            "distinct_keys": int(per_key.size),
            "over_merged_keys": int(over_merged_keys.size),
            "over_merged_pct": round(over_merged_keys.size / max(per_key.size, 1) * 100, 1),
            "over_split_orcids": int(over_split_orcids.size),
            "over_split_pct": round(
                over_split_orcids.size / max(per_orcid.size, 1) * 100, 1),
            "examples_over_merged": over_merged_keys.head(5).to_dict(),
        },
        "full_key": {
            "distinct_keys": int(per_key_full.size),
            "over_merged_keys": int((per_key_full > 1).sum()),
            "over_split_orcids": int((per_orcid_full > 1).sum()),
            "over_split_pct": round(
                (per_orcid_full > 1).sum() / max(per_orcid_full.size, 1) * 100, 1),
        },
    }


def merge_scopus_affiliations(a: pd.DataFrame) -> pd.DataFrame:
    """Scopus由来の所属を著者レコードに統合する。

    Crossref の所属は網羅率34.5%しかないのに対し、Scopus Abstract Retrieval は
    99.5%の論文で所属を返す（2026-08-06実測）。両者を突き合わせて網羅率を上げる。

    突き合わせは **同一論文内で「姓 + 名の先頭イニシャル」が一致するか** で行う。
    1論文の著者は数名〜数十名しかいないため、この粒度でも取り違えはほぼ起きない
    （著者名の全体照合ではないので、表記ゆれに強い）。
    """
    if not IN_SCOPUS.exists():
        print("Scopusの所属データがないので Crossref のみで進めます。", flush=True)
        a["scopus_affiliation"] = None
        a["scopus_author_id"] = None
        a["scopus_is_toyota"] = False
        return a

    s = pd.read_csv(IN_SCOPUS)
    s["match_key"] = [f"{d}|{name_key(g, f)}" for d, g, f
                      in zip(s["doi"], s["given_name"], s["surname"])]
    # 同じ論文内で同じキーが複数ある場合（同姓同名の共著者）は先頭を採る
    s = s.drop_duplicates("match_key").set_index("match_key")

    a["match_key"] = [f"{d}|{k}" for d, k in zip(a["doi"], a["name_key"])]
    a["scopus_affiliation"] = a["match_key"].map(s["affiliation"])
    a["scopus_author_id"] = a["match_key"].map(s["scopus_author_id"])
    a["scopus_is_toyota"] = a["match_key"].map(
        s["is_toyota_affiliated"]).fillna(False).astype(bool)

    matched = a["scopus_affiliation"].notna().sum()
    print(f"Scopusとの突き合わせ: {matched}/{len(a)}件 "
          f"({matched/len(a)*100:.1f}%) の著者レコードに所属を付与", flush=True)
    return a.drop(columns=["match_key"])


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    a = pd.read_csv(IN_AUTHORS)
    papers = pd.read_csv(IN_PAPERS)
    a["name_key"] = [name_key(g, f) for g, f in zip(a["given"], a["family"])]
    a["full_key"] = [full_key(g, f) for g, f in zip(a["given"], a["family"])]
    # ORCIDのURL表記を正規化（末尾のIDだけ取る）
    a["orcid"] = a["orcid"].astype(str).str.extract(
        r"(\d{4}-\d{4}-\d{4}-[\dxX]{4})", expand=False)

    print(f"著者レコード {len(a)}件 / 氏名キー {a['name_key'].nunique()}種", flush=True)

    # ---- Scopus の所属を統合し、所属の網羅率を上げる ----
    a = merge_scopus_affiliations(a)
    # どちらかで所属が取れていれば「所属あり」、どちらかがトヨタ系なら「トヨタ系」
    a["affiliation_any"] = a["affiliation"].fillna(a["scopus_affiliation"])
    a["is_toyota_any"] = (a["is_toyota_affiliated"].fillna(False).astype(bool)
                          | a["scopus_is_toyota"])
    print(f"所属の網羅率: Crossrefのみ {a['affiliation'].notna().mean()*100:.1f}% "
          f"→ Scopus統合後 {a['affiliation_any'].notna().mean()*100:.1f}%", flush=True)
    print(f"トヨタ系と判定された著者レコード: "
          f"{int(a['is_toyota_affiliated'].fillna(False).sum())}件 "
          f"→ {int(a['is_toyota_any'].sum())}件", flush=True)

    # ---- 名寄せ規則の精度をORCIDで実測 ----
    validation = validate_namekey(a)
    print("\n===== 名寄せ規則の精度（ORCIDを正解ラベルとして実測）=====", flush=True)
    print(json.dumps(validation, ensure_ascii=False, indent=2), flush=True)

    # ---- クラスタリング: ORCIDを最優先、なければ氏名キー ----
    # 同じORCIDを持つレコードが属する氏名キーは、すべて同一人物とみなして統合する
    key_to_orcid: dict[str, str] = {}
    for orcid, grp in a[a["orcid"].notna()].groupby("orcid"):
        for k in grp["name_key"].unique():
            # 既に別ORCIDに割り当て済みのキーは、曖昧なので統合しない
            key_to_orcid[k] = orcid if k not in key_to_orcid else "__CONFLICT__"

    def cluster_id(row) -> str:
        if pd.notna(row["orcid"]):
            return f"orcid:{row['orcid']}"
        mapped = key_to_orcid.get(row["name_key"])
        if mapped and mapped != "__CONFLICT__":
            return f"orcid:{mapped}"
        return f"name:{row['name_key']}"

    a["cluster_id"] = a.apply(cluster_id, axis=1)
    a["cluster_source"] = a["cluster_id"].str.startswith("orcid:").map(
        {True: "orcid", False: "name_key"})
    a.to_csv(OUT_DIR / "author_records_keyed.csv", index=False)

    # ---- 研究者単位に集約 ----
    pmeta = papers.set_index("doi")[["source_org", "crossref_year",
                                     "is_referenced_by_count"]]
    a2 = a.join(pmeta, on="doi")

    def agg(g: pd.DataFrame) -> pd.Series:
        orcids = sorted(set(g["orcid"].dropna()))
        names = sorted(set(g["full_name"].dropna()))
        yrs = g["crossref_year"].dropna()
        return pd.Series({
            "canonical_name": max(names, key=len) if names else "",
            "n_name_variants": len(names),
            "name_variants": " / ".join(names),
            "orcid": orcids[0] if orcids else None,
            "n_orcids": len(orcids),
            "n_papers": g["doi"].nunique(),
            "first_year": int(yrs.min()) if len(yrs) else None,
            "last_year": int(yrs.max()) if len(yrs) else None,
            "source_orgs": " / ".join(sorted(set(g["source_org"].dropna()))),
            "n_source_orgs": g["source_org"].nunique(),
            "n_toyota_affiliated_records": int(g["is_toyota_any"].sum()),
            "has_affiliation_data": bool(g["affiliation_any"].notna().any()),
            "affiliations": " | ".join(dict.fromkeys(
                x for x in g["affiliation_any"].dropna() if x))[:500],
            "scopus_author_ids": "; ".join(sorted(set(
                str(x) for x in g["scopus_author_id"].dropna()))),
            "total_citations": int(g["is_referenced_by_count"].fillna(0).sum()),
        })

    r = a2.groupby("cluster_id").apply(agg, include_groups=False).reset_index()
    r["id_source"] = r["cluster_id"].str.startswith("orcid:").map(
        {True: "orcid", False: "name_key"})

    # 確信度: ORCIDで裏が取れているか / 氏名がイニシャルのみか
    initials_only = a.groupby("cluster_id")["given"].apply(
        lambda s: s.dropna().map(is_initials).all() if s.notna().any() else True)
    r["initials_only"] = r["cluster_id"].map(initials_only).fillna(False)
    r["confidence"] = "low"
    r.loc[r["id_source"] == "name_key", "confidence"] = "medium"
    r.loc[(r["id_source"] == "name_key") & r["initials_only"], "confidence"] = "low"
    r.loc[r["id_source"] == "orcid", "confidence"] = "high"

    r = r.sort_values("n_papers", ascending=False)
    r.to_csv(OUT_DIR / "researchers.csv", index=False)
    (OUT_DIR / "namekey_validation.json").write_text(
        json.dumps(validation, ensure_ascii=False, indent=2), encoding="utf-8")

    summary = {
        "input_author_records": int(len(a)),
        "researchers": int(len(r)),
        "by_id_source": r["id_source"].value_counts().to_dict(),
        "by_confidence": r["confidence"].value_counts().to_dict(),
        "researchers_with_multiple_name_variants": int((r["n_name_variants"] > 1).sum()),
        "initials_only_researchers": int(r["initials_only"].sum()),
        "cross_org_researchers": int((r["n_source_orgs"] > 1).sum()),
        "researchers_with_toyota_affiliation_evidence": int(
            (r["n_toyota_affiliated_records"] > 0).sum()),
        "namekey_validation": validation,
    }
    (OUT_DIR / "researchers_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    print("\n===== 集約結果 =====", flush=True)
    print(json.dumps({k: v for k, v in summary.items()
                      if k != "namekey_validation"}, ensure_ascii=False, indent=2),
          flush=True)
    print("\n===== 論文数の多い研究者 上位15名 =====", flush=True)
    cols = ["canonical_name", "orcid", "n_papers", "n_name_variants",
            "n_source_orgs", "confidence"]
    print(r[cols].head(15).to_string(index=False), flush=True)


if __name__ == "__main__":
    main()
