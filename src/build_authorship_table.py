"""論文×著者テーブルを、OpenAlex を背骨にして作り直す。

なぜ作り直すか:
  現行の `crossref_authors.csv` / `scopus_paper_authors.csv` は **DOI をキー**に
  している。ところが OpenAlex への対応づけは Work ID で成立するため DOI を必要と
  せず、ここに到達範囲の差が生まれる。結果、OpenAlex に正しく対応づいた213行が
  研究者表に一切届いていない。とくにトヨタ自動車未来創成センターは DOI 保有率が
  6.5%しかないため、131件対応づいているのに9件しか使えていなかった。
  このソースは自社所属著者を太字で明示する唯一のソースであり、
  所属判定の最良の正解データが94%欠落していたことになる。

設計:
  背骨は OpenAlex の `authorships`（対応づけ済みの全 Work をカバーする）。
  ここに Crossref と Scopus を、同一論文内で「姓＋名の先頭イニシャル」が
  一致するかで突き合わせる。1論文の著者は数名〜数十名なので、
  この粒度でも取り違えはほぼ起きない（著者名の全体照合ではないので表記ゆれに強い）。

  OpenAlex が取れない掲載（対応づかなかった67件）のうち DOI を持つものは
  Crossref を背骨にして拾う。

  ORCID は出所を分けて保持する。OpenAlex の `author.orcid` は**使わない**。
  過剰併合している著者エンティティ由来で、別人の ORCID が付きうるため。
  採るのは `raw_orcid`（その論文の登録データ由来）だけである。

入力: data/derived/papers/papers.csv
      data/cache/openalex_linking_cache.json
      data/derived/paper_enrichment/{crossref_authors,scopus_paper_authors}.csv
出力: data/derived/papers/authorships.csv … 主キー paper_uid + author_seq
      data/derived/papers/authorships_summary.json

実行: ~/.venvs/scisci-rir/bin/python src/build_authorship_table.py
"""
from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
IN_PAPERS = ROOT / "data" / "derived" / "papers" / "papers.csv"
IN_CACHE = ROOT / "data" / "cache" / "openalex_linking_cache.json"
IN_CROSSREF = ROOT / "data" / "derived" / "paper_enrichment" / "crossref_authors.csv"
IN_SCOPUS = ROOT / "data" / "derived" / "paper_enrichment" / "scopus_paper_authors.csv"
OUT_DIR = ROOT / "data" / "derived" / "papers"

TOYOTA_PATTERNS = ["toyota", "imra", "aisin", "tytlabs", "豊田", "トヨタ", "アイシン"]
# 部分文字列一致の偽陽性。トヨタ系企業の研究所ではないので除く。
TOYOTA_EXCLUDE = [
    "toyota technological institute",   # 豊田工業大学（教育研究機関）
    "toyota college",                   # 豊田工業高等専門学校
    "kariya toyota general hospital",   # 刈谷豊田総合病院
]


def norm(s) -> str:
    if s is None or (isinstance(s, float) and pd.isna(s)):
        return ""
    t = unicodedata.normalize("NFKC", str(s)).lower()
    t = re.sub(r"[^0-9a-z ]+", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def name_key(given, family) -> str:
    f, g = norm(family), norm(given)
    return f"{f}|{g[0] if g else ''}" if f else ""


def split_name(full: str) -> tuple[str, str]:
    """OpenAlex の `raw_author_name` を given / family に分ける。

    2つの表記が混在するので区別が要る:
      `Paidi Yella Reddy` … 名→姓の順。末尾トークンが姓
      `Hakuta, Yusuke`    … カンマ区切りで姓が先。**逆に読むと姓名が反転する**

    後者を末尾トークン方式で処理すると given/family が入れ替わり、
    `name_key`（姓＋名の先頭イニシャル）が壊れて Crossref/Scopus と
    一切突き合わせできなくなる（2026-08-24 に25件で実測）。
    DOI がある論文では後段で Crossref の明示的な given/family で上書きする。
    """
    s = str(full or "").strip()
    if not s or s.lower() == "nan":
        return "", ""
    if "," in s:
        fam, _, giv = s.partition(",")
        if fam.strip() and giv.strip():
            return giv.strip(), fam.strip()
    toks = s.split()
    if not toks:
        return "", ""
    return " ".join(toks[:-1]), toks[-1]


def is_toyota(*texts) -> bool:
    for t in texts:
        s = unicodedata.normalize("NFKC", str(t or "")).lower()
        if not s:
            continue
        if any(x in s for x in TOYOTA_EXCLUDE):
            continue
        if any(p in s for p in TOYOTA_PATTERNS):
            return True
    return False


def load_works() -> dict:
    cache = json.loads(IN_CACHE.read_text(encoding="utf-8"))
    works = {}
    for v in cache.values():
        if isinstance(v, dict):
            for w in (v.get("results") or []):
                if w.get("id"):
                    works[w["id"]] = w
    return works


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    papers = pd.read_csv(IN_PAPERS)
    works = load_works()
    print(f"論文 {len(papers)}件 / キャッシュ内の Work {len(works)}件", flush=True)

    cr = pd.read_csv(IN_CROSSREF)
    cr["k"] = [name_key(g, f) for g, f in zip(cr["given"], cr["family"])]
    cr["orcid"] = cr["orcid"].astype(str).str.extract(
        r"(\d{4}-\d{4}-\d{4}-[\dxX]{4})", expand=False)
    CR = {(d, k): r for d, k, r in zip(cr["doi"], cr["k"], cr.to_dict("records")) if k}

    sc = pd.read_csv(IN_SCOPUS)
    sc["k"] = [name_key(g, f) for g, f in zip(sc["given_name"], sc["surname"])]
    SC = {(d, k): r for d, k, r in zip(sc["doi"], sc["k"], sc.to_dict("records")) if k}

    rows = []
    n_oa = n_cr_spine = 0
    for p in papers.to_dict("records"):
        uid, wid, doi = p["paper_uid"], p.get("work_id"), p.get("doi_norm")
        doi = None if pd.isna(doi) else doi
        w = works.get(wid) if isinstance(wid, str) else None

        if w and (w.get("authorships") or []):
            spine = "openalex"
            n_oa += 1
            items = []
            for a in w["authorships"]:
                full = a.get("raw_author_name") or (a.get("author") or {}).get("display_name")
                g, f = split_name(full)
                items.append({
                    "name_raw": full, "given": g, "family": f,
                    "affil_openalex": "; ".join(a.get("raw_affiliation_strings") or []) or None,
                    "inst_openalex": "; ".join(
                        i.get("display_name") for i in (a.get("institutions") or [])
                        if i.get("display_name")) or None,
                    "orcid_openalex": a.get("raw_orcid"),
                    "openalex_author_id": (a.get("author") or {}).get("id"),
                    "is_corresponding": bool(a.get("is_corresponding")),
                })
        elif doi:
            spine = "crossref"
            n_cr_spine += 1
            items = [{
                "name_raw": r["full_name"], "given": r["given"], "family": r["family"],
                "affil_openalex": None, "inst_openalex": None, "orcid_openalex": None,
                "openalex_author_id": None, "is_corresponding": bool(r["is_corresponding"]),
            } for r in cr[cr["doi"] == doi].to_dict("records")]
        else:
            continue

        for seq, it in enumerate(items, 1):
            k = name_key(it["given"], it["family"])
            c = CR.get((doi, k)) if doi else None
            s = SC.get((doi, k)) if doi else None
            # Crossref は given/family を明示的に持つので、姓名の分割はそちらを優先する
            if c:
                it["given"], it["family"] = c["given"], c["family"]
                k = name_key(it["given"], it["family"])
            affil_cr = (c or {}).get("affiliation") or None
            affil_sc = (s or {}).get("affiliation") or None
            if isinstance(affil_cr, float):
                affil_cr = None
            if isinstance(affil_sc, float):
                affil_sc = None
            orcid = it["orcid_openalex"] or (c or {}).get("orcid")
            rows.append({
                "paper_uid": uid, "author_seq": seq, "work_id": wid, "doi": doi,
                "source_org": p["source_org"], "spine": spine,
                "name_raw": it["name_raw"], "given": it["given"], "family": it["family"],
                "name_key": k,
                "orcid": orcid,
                "orcid_openalex_raw": it["orcid_openalex"],
                "orcid_crossref": (c or {}).get("orcid"),
                "affiliation": affil_openalex_first(it["affil_openalex"], affil_sc, affil_cr),
                "affil_openalex": it["affil_openalex"],
                "affil_crossref": affil_cr,
                "affil_scopus": affil_sc,
                "inst_openalex": it["inst_openalex"],
                "openalex_author_id": it["openalex_author_id"],
                "scopus_author_id": (s or {}).get("scopus_author_id"),
                "is_corresponding": it["is_corresponding"],
                "is_toyota": is_toyota(it["affil_openalex"], affil_sc, affil_cr,
                                       it["inst_openalex"]),
                "matched_crossref": c is not None,
                "matched_scopus": s is not None,
            })

    A = pd.DataFrame(rows)
    assert not A.duplicated(["paper_uid", "author_seq"]).any(), "主キーが一意でない"
    A.to_csv(OUT_DIR / "authorships.csv", index=False)

    cov = lambda c: round(A[c].notna().mean() * 100, 1)
    summary = {
        "authorship_records": int(len(A)),
        "papers_covered": int(A["paper_uid"].nunique()),
        "papers_total": int(len(papers)),
        "spine_openalex_papers": n_oa,
        "spine_crossref_papers": n_cr_spine,
        "affiliation_coverage_pct": cov("affiliation"),
        "affiliation_by_source": {
            "openalex": cov("affil_openalex"),
            "scopus": cov("affil_scopus"),
            "crossref": cov("affil_crossref"),
        },
        "orcid_coverage_pct": cov("orcid"),
        "distinct_orcids": int(A["orcid"].nunique()),
        "toyota_affiliated_records": int(A["is_toyota"].sum()),
        "crossref_match_rate_pct": round(A["matched_crossref"].mean() * 100, 1),
        "scopus_match_rate_pct": round(A["matched_scopus"].mean() * 100, 1),
        "by_source_org": json.loads(A.groupby("source_org").agg(
            著者レコード=("author_seq", "size"),
            論文=("paper_uid", "nunique"),
            所属あり=("affiliation", lambda s: int(s.notna().sum())),
            トヨタ系=("is_toyota", "sum")).to_json(orient="index")),
    }
    (OUT_DIR / "authorships_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2), flush=True)


def affil_openalex_first(oa, sc, cr):
    """所属の代表値。OpenAlex の生文字列を優先し、なければ Scopus → Crossref。

    OpenAlex を先にするのは網羅率が最も高いため。Scopus は正規化済みの組織名を
    返すので、組織単位の集計では `affil_scopus` を別途使う。
    """
    for x in (oa, sc, cr):
        if x and not (isinstance(x, float) and pd.isna(x)):
            return x
    return None


if __name__ == "__main__":
    main()
