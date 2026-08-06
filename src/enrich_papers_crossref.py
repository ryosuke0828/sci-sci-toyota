"""収集済み論文をCrossrefで補完する（著者名・所属・参考文献数）。

OpenAlexの無料枠（1日1,000件）と違い、Crossrefは10 req/秒・日次上限なしで使える。
そのため OpenAlex のクォータが尽きた日でもこの処理は進められる。

これを行う理由:
  - AISIN IMRA米国版(imra.com)の313件は**サイト上に著者名の記載が一切ない**
  - Crossrefは著者ごとの `affiliation` 文字列を返すので、
    「どの著者がトヨタ系所属か」を著者単位で判定できる
    （未来創成センターの太字表記に相当する情報を、他の3ソースにも与えられる）

入力: data/derived/toyota_official_scrape/combined_papers.csv
出力: data/derived/paper_enrichment/
  - crossref_papers.csv  … 1論文1行
  - crossref_authors.csv … 1論文1著者1行（所属・トヨタ系判定つき）
  - crossref_summary.json

実行: ~/.venvs/scisci-rir/bin/python src/enrich_papers_crossref.py
"""
from __future__ import annotations

import json
import re
import time
import unicodedata
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parent.parent
IN_CSV = ROOT / "data" / "derived" / "toyota_official_scrape" / "combined_papers.csv"
OUT_DIR = ROOT / "data" / "derived" / "paper_enrichment"
CACHE_PATH = ROOT / "data" / "cache" / "crossref_cache.json"

MAILTO = "ikuraryosuke@gmail.com"
SESSION = requests.Session()
SESSION.headers.update({"User-Agent": f"scisci-toyota (mailto:{MAILTO})"})

# 所属文字列がトヨタ系かの判定に使う語。日本語表記も拾う。
TOYOTA_PATTERNS = [
    "toyota", "imra", "aisin", "tytlabs",
    "豊田", "トヨタ", "アイシン",
]

_cache: dict[str, dict] = {}
_dirty = 0


def normalize_doi(raw) -> str | None:
    if raw is None or (isinstance(raw, float) and pd.isna(raw)):
        return None
    s = str(raw).strip()
    if not s or s.lower() == "nan":
        return None
    s = re.sub(r"^https?://(dx\.)?doi\.org/", "", s, flags=re.I).strip().rstrip(".")
    return s.lower() if s.startswith("10.") else None


def load_cache() -> None:
    global _cache
    if CACHE_PATH.exists():
        _cache = json.loads(CACHE_PATH.read_text(encoding="utf-8"))
        print(f"キャッシュ読み込み: {len(_cache)}件", flush=True)


def save_cache() -> None:
    global _dirty
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    CACHE_PATH.write_text(json.dumps(_cache, ensure_ascii=False), encoding="utf-8")
    _dirty = 0


def fetch(doi: str) -> dict | None:
    """Crossrefから1件取得。404（Crossref未登録）は None を返す。"""
    global _dirty
    if doi in _cache:
        return _cache[doi]
    for attempt in range(3):
        time.sleep(0.15)  # 10 req/秒 制限に対する余裕をとる
        try:
            r = SESSION.get(f"https://api.crossref.org/works/{doi}", timeout=30)
        except requests.RequestException as e:
            print(f"    例外 {type(e).__name__} ({doi})", flush=True)
            time.sleep(2 * (attempt + 1))
            continue
        if r.status_code == 200:
            msg = r.json()["message"]
            _cache[doi] = msg
            _dirty += 1
            if _dirty >= 50:
                save_cache()
            return msg
        if r.status_code == 404:
            _cache[doi] = None
            return None
        if r.status_code in (429, 500, 502, 503):
            time.sleep(3 * (attempt + 1))
            continue
        print(f"    HTTP {r.status_code} ({doi})", flush=True)
        return None
    return None


def is_toyota_affiliation(text: str | None) -> bool:
    if not text:
        return False
    t = unicodedata.normalize("NFKC", str(text)).lower()
    return any(p in t for p in TOYOTA_PATTERNS)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    load_cache()
    df = pd.read_csv(IN_CSV)
    df["doi_norm"] = df["doi"].map(normalize_doi)
    doi_rows = df[df["doi_norm"].notna()]
    unique_dois = sorted(set(doi_rows["doi_norm"]))
    print(f"入力 {len(df)}件 / DOIあり {len(doi_rows)}件 / ユニークDOI {len(unique_dois)}件\n",
          flush=True)

    paper_rows, author_rows = [], []
    not_found = []
    try:
        for n, doi in enumerate(unique_dois, 1):
            if n % 50 == 0:
                print(f"    {n}/{len(unique_dois)} ...", flush=True)
            m = fetch(doi)
            if m is None:
                not_found.append(doi)
                continue
            authors = m.get("author") or []
            # 著者ごとの所属からトヨタ系を判定する
            n_toyota = 0
            for pos, a in enumerate(authors, 1):
                affils = [x.get("name") for x in (a.get("affiliation") or [])]
                affil_str = "; ".join(x for x in affils if x)
                toy = is_toyota_affiliation(affil_str)
                n_toyota += int(toy)
                author_rows.append({
                    "doi": doi,
                    "author_position": pos,
                    "given": a.get("given"),
                    "family": a.get("family"),
                    "full_name": " ".join(
                        x for x in [a.get("given"), a.get("family")] if x)
                    or a.get("name"),
                    "orcid": a.get("ORCID"),
                    "affiliation": affil_str,
                    "is_toyota_affiliated": toy,
                    "is_corresponding": a.get("sequence") == "first",
                })
            ct = m.get("container-title") or []
            paper_rows.append({
                "doi": doi,
                "crossref_title": (m.get("title") or [None])[0],
                "crossref_venue": ct[0] if ct else None,
                "crossref_type": m.get("type"),
                "crossref_year": ((m.get("issued") or {}).get("date-parts")
                                  or [[None]])[0][0],
                "n_authors": len(authors),
                "n_toyota_authors": n_toyota,
                "has_affiliation_data": any(
                    (a.get("affiliation") or []) for a in authors),
                "reference_count": m.get("reference-count"),
                "is_referenced_by_count": m.get("is-referenced-by-count"),
                "publisher": m.get("publisher"),
            })
    except KeyboardInterrupt:
        print("\n!! 中断。ここまでの結果を保存します。", flush=True)
    finally:
        save_cache()

    papers = pd.DataFrame(paper_rows)
    authors_df = pd.DataFrame(author_rows)
    src = doi_rows[["doi_norm", "source_org", "title"]].drop_duplicates("doi_norm")
    papers = papers.merge(src, left_on="doi", right_on="doi_norm", how="left") \
                   .drop(columns=["doi_norm"])
    papers.to_csv(OUT_DIR / "crossref_papers.csv", index=False)
    authors_df.to_csv(OUT_DIR / "crossref_authors.csv", index=False)

    by_src = papers.groupby("source_org").agg(
        papers=("doi", "size"),
        with_affil=("has_affiliation_data", "sum"),
        authors=("n_authors", "sum"),
        toyota_authors=("n_toyota_authors", "sum"))
    summary = {
        "unique_dois_queried": len(unique_dois),
        "crossref_found": int(len(papers)),
        "crossref_not_found": len(not_found),
        "not_found_examples": not_found[:10],
        "total_author_records": int(len(authors_df)),
        "unique_author_names": int(authors_df["full_name"].nunique())
        if len(authors_df) else 0,
        "authors_with_orcid": int(authors_df["orcid"].notna().sum())
        if len(authors_df) else 0,
        "toyota_affiliated_author_records": int(
            authors_df["is_toyota_affiliated"].sum()) if len(authors_df) else 0,
        "papers_with_affiliation_data": int(papers["has_affiliation_data"].sum()),
        "by_source_org": json.loads(by_src.to_json(orient="index")),
    }
    (OUT_DIR / "crossref_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    print("\n===== サマリ =====", flush=True)
    print(json.dumps(summary, ensure_ascii=False, indent=2), flush=True)
    print("\n===== ソース別 =====", flush=True)
    print(by_src.to_string(), flush=True)


if __name__ == "__main__":
    main()
