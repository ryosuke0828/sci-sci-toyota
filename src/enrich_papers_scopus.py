"""論文の著者の所属を Scopus Abstract Retrieval API で補う。

なぜ著者検索ではなく論文（DOI）から引くのか:
  - OpenAlex の所属は論文に書かれた文字列のままで、同じ組織が何通りにも書かれる。
    Scopus は組織名を揃えて返すので、組織単位の判定に使える
  - Scopus の Author Search で著者を引く方法は同姓同名の問題を避けられない
    （ありふれた名前だと候補が数千件になる）
  - Abstract Retrieval は「この論文のこの著者の所属」を返すので、
    人物を取り違える余地がない。どの論文かは既に確定しているため

Scopus の利用には、契約機関のネットワークからのアクセスと API キーが要る。

入力: data/derived/toyota_official_scrape/combined_papers.csv
出力: data/derived/paper_enrichment/
  - scopus_paper_authors.csv … 1論文1著者1行（所属・Scopus著者ID・トヨタ系判定）
確認用の出力（data/diagnostics/、コミットしない）: data/diagnostics/paper_enrichment/
  - scopus_papers.csv        … 1論文1行
  - scopus_summary.json

クォータ: Abstract Retrieval は 10,000件/週。対象は641件。

環境変数:
  SCOPUS_API_KEY  Scopus の API キー

実行: python src/enrich_papers_scopus.py
"""
from __future__ import annotations

import json
import os
import re
import time
import unicodedata
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parent.parent
IN_CSV = Path(os.environ.get(
    "SCISCI_INPUT_CSV",
    ROOT / "data" / "derived" / "toyota_official_scrape" / "combined_papers.csv"))
OUT_DIR = Path(os.environ.get(
    "SCISCI_SCOPUS_OUT_DIR", ROOT / "data" / "derived" / "paper_enrichment"))
DIAG_DIR = ROOT / "data" / "diagnostics" / "paper_enrichment"
CACHE_PATH = Path(os.environ.get(
    "SCISCI_SCOPUS_CACHE", ROOT / "data" / "cache" / "scopus_abstract_cache.json"))

KEY = os.environ.get("SCOPUS_API_KEY")
if not KEY:
    raise SystemExit("SCOPUS_API_KEY が環境変数にありません")
HEADERS = {"X-ELS-APIKey": KEY, "Accept": "application/json"}
BASE = "https://api.elsevier.com/content/abstract/doi"

TOYOTA_PATTERNS = ["toyota", "imra", "aisin", "tytlabs", "豊田", "トヨタ", "アイシン"]

_cache: dict[str, dict] = {}
_dirty = 0


class QuotaExhausted(RuntimeError):
    """Scopus の週次クォータを使い切った。"""


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


def as_list(x) -> list:
    """Scopus は要素が1つのとき配列でなく辞書を返すことがある。"""
    if x is None:
        return []
    return x if isinstance(x, list) else [x]


def fetch(doi: str) -> dict | None:
    global _dirty
    if doi in _cache:
        return _cache[doi]
    for attempt in range(3):
        time.sleep(0.25)
        try:
            r = requests.get(f"{BASE}/{doi}", headers=HEADERS,
                             params={"view": "FULL"}, timeout=40)
        except requests.RequestException as e:
            print(f"    例外 {type(e).__name__} ({doi})", flush=True)
            time.sleep(2 * (attempt + 1))
            continue
        if r.status_code == 200:
            d = r.json().get("abstracts-retrieval-response")
            _cache[doi] = d
            _dirty += 1
            if _dirty >= 50:
                save_cache()
            return d
        if r.status_code in (400, 404):   # Scopus未収録
            _cache[doi] = None
            return None
        if r.status_code == 429 or (
                r.status_code == 403 and "QUOTA" in r.text.upper()):
            raise QuotaExhausted(
                f"Scopus の週次クォータを使い切った可能性があります: {r.text[:200]}")
        if r.status_code in (500, 502, 503):
            time.sleep(3 * (attempt + 1))
            continue
        print(f"    HTTP {r.status_code} ({doi}): {r.text[:150]}", flush=True)
        return None
    return None


def is_toyota(text: str | None) -> bool:
    if not text:
        return False
    t = unicodedata.normalize("NFKC", str(text)).lower()
    return any(p in t for p in TOYOTA_PATTERNS)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    DIAG_DIR.mkdir(parents=True, exist_ok=True)
    load_cache()
    df = pd.read_csv(IN_CSV)
    df["doi_norm"] = df["doi"].map(normalize_doi)
    doi_rows = df[df["doi_norm"].notna()]
    unique_dois = sorted(set(doi_rows["doi_norm"]))
    print(f"入力 {len(df)}件 / ユニークDOI {len(unique_dois)}件\n", flush=True)

    author_rows, paper_rows, not_found = [], [], []
    complete = True
    try:
        for n, doi in enumerate(unique_dois, 1):
            if n % 50 == 0:
                print(f"    {n}/{len(unique_dois)} ...", flush=True)
            d = fetch(doi)
            if not d:
                not_found.append(doi)
                continue

            # 論文全体の所属一覧。著者側は所属IDしか持たないのでここで名前を引く
            afid_to_name = {}
            for af in as_list(d.get("affiliation")):
                if af.get("@id"):
                    afid_to_name[af["@id"]] = af.get("affilname")

            authors = as_list((d.get("authors") or {}).get("author"))
            n_toy = 0
            for a in authors:
                afids = [x.get("@id") for x in as_list(a.get("affiliation"))]
                names = [afid_to_name.get(i) for i in afids if afid_to_name.get(i)]
                affil_str = "; ".join(dict.fromkeys(names))
                toy = is_toyota(affil_str)
                n_toy += int(toy)
                author_rows.append({
                    "doi": doi,
                    "author_position": a.get("@seq"),
                    "scopus_author_id": a.get("@auid"),
                    "indexed_name": a.get("ce:indexed-name"),
                    "surname": a.get("ce:surname"),
                    "given_name": a.get("ce:given-name"),
                    "affiliation": affil_str,
                    "n_affiliations": len(names),
                    "is_toyota_affiliated": toy,
                })
            core = d.get("coredata") or {}
            paper_rows.append({
                "doi": doi,
                "scopus_id": core.get("dc:identifier"),
                "scopus_title": core.get("dc:title"),
                "scopus_cited_by_count": core.get("citedby-count"),
                "n_authors": len(authors),
                "n_toyota_authors": n_toy,
                "has_affiliation_data": bool(afid_to_name),
                "affiliations": "; ".join(
                    x for x in afid_to_name.values() if x),
            })
    except QuotaExhausted as e:
        complete = False
        print(f"\n!! 中断: {e}", flush=True)
        print("!! ここまでの結果を保存します。翌週リセット後に再実行すれば"
              "キャッシュ済み分は消費せず続きから進みます。", flush=True)
    except KeyboardInterrupt:
        complete = False
        print("\n!! 中断（Ctrl-C）。ここまでの結果を保存します。", flush=True)
    finally:
        save_cache()

    authors_df = pd.DataFrame(author_rows)
    papers_df = pd.DataFrame(paper_rows)
    src = doi_rows[["doi_norm", "source_org"]].drop_duplicates("doi_norm")
    papers_df = papers_df.merge(src, left_on="doi", right_on="doi_norm",
                                how="left").drop(columns=["doi_norm"])
    authors_df.to_csv(OUT_DIR / "scopus_paper_authors.csv", index=False)
    papers_df.to_csv(DIAG_DIR / "scopus_papers.csv", index=False)

    summary = {
        "complete": complete,
        "unique_dois_queried": len(unique_dois),
        "scopus_found": int(len(papers_df)),
        "scopus_not_found": len(not_found),
        "not_found_examples": not_found[:10],
        "total_author_records": int(len(authors_df)),
        "papers_with_affiliation_data": int(papers_df["has_affiliation_data"].sum())
        if len(papers_df) else 0,
        "author_records_with_affiliation": int(
            (authors_df["n_affiliations"] > 0).sum()) if len(authors_df) else 0,
        "toyota_affiliated_author_records": int(
            authors_df["is_toyota_affiliated"].sum()) if len(authors_df) else 0,
        "unique_scopus_author_ids": int(authors_df["scopus_author_id"].nunique())
        if len(authors_df) else 0,
    }
    (DIAG_DIR / "scopus_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    print("\n===== サマリ =====", flush=True)
    print(json.dumps(summary, ensure_ascii=False, indent=2), flush=True)


if __name__ == "__main__":
    main()
