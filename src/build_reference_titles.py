"""各論文と、その参考文献のタイトルを対応づけたテーブルを作る。

参照関係（どの論文がどれを引用したか）は OpenAlex のスナップショット抽出
（~/scisci-data/works_slim/）にある。抽出時にタイトル列は容量の都合で落としたので、
引用先のタイトルだけを OpenAlex API から補う。50件を1リクエストにまとめるので
21,745件でも約435リクエストで済む（無料枠は1日1000）。

入力: data/derived/papers/papers.csv
      ~/scisci-data/works_slim/*.parquet   （参照エッジ・DOI・出版年・掲載誌）
出力: data/derived/papers/paper_references.csv   … 1行＝(論文, 参考文献1件)
      data/derived/papers/paper_references.json  … {論文タイトル: [参考文献タイトル, ...]}
      data/cache/openalex_title_cache.json       … work_id → タイトル

クォータ切れ（HTTP 429 かつ X-RateLimit-Remaining == 0）を検出したら中断し、
途中結果とキャッシュを必ず書き出す。翌日そのまま再実行すれば続きから進む。

実行: ~/.venvs/scisci-rir/bin/python src/build_reference_titles.py
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path

import duckdb
import pandas as pd
import requests

ROOT = Path(__file__).resolve().parent.parent
IN_PAPERS = ROOT / "data" / "derived" / "papers" / "papers.csv"
SLIM_GLOB = os.environ.get(
    "SCISCI_SLIM_GLOB", str(Path.home() / "scisci-data" / "works_slim" / "*.parquet"))
OUT_DIR = ROOT / "data" / "derived" / "papers"
CACHE_PATH = ROOT / "data" / "cache" / "openalex_title_cache.json"

API = "https://api.openalex.org/works"
MAILTO = "r.ikura@msp-lab.org"
BATCH = 50


class QuotaExhausted(RuntimeError):
    pass


def load_cache() -> dict:
    if CACHE_PATH.exists():
        return json.loads(CACHE_PATH.read_text())
    return {}


def save_cache(cache: dict) -> None:
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    CACHE_PATH.write_text(json.dumps(cache, ensure_ascii=False))


def fetch_titles(ids: list[int], cache: dict) -> None:
    """未取得の work_id のタイトルを50件ずつ取得し、キャッシュに詰める。"""
    todo = [i for i in ids if str(i) not in cache]
    print(f"タイトル取得: 未取得 {len(todo)} / 全 {len(ids)}（キャッシュ済み {len(ids)-len(todo)}）", flush=True)
    for k in range(0, len(todo), BATCH):
        chunk = todo[k:k + BATCH]
        params = {
            "filter": "openalex_id:" + "|".join(f"https://openalex.org/W{i}" for i in chunk),
            "select": "id,title",
            "per_page": BATCH,
            "mailto": MAILTO,
        }
        resp = requests.get(API, params=params, timeout=60)
        if resp.status_code == 429:
            # 一時的なスロットリングと、日次予算の使い切りを区別する。
            # 後者はリトライしても回復しないので即座に中断する。
            if resp.headers.get("x-ratelimit-remaining") == "0":
                raise QuotaExhausted(f"{len(cache)} 件取得済みで日次クォータを使い切った")
            time.sleep(10)
            resp = requests.get(API, params=params, timeout=60)
        resp.raise_for_status()
        got = {w["id"].rsplit("/W", 1)[-1]: w.get("title") for w in resp.json()["results"]}
        for i in chunk:
            cache[str(i)] = got.get(str(i))  # 応答に無い ID は None を入れ、再問い合わせしない
        if (k // BATCH + 1) % 25 == 0:
            save_cache(cache)
            print(f"  {k+len(chunk)}/{len(todo)}  残クォータ {resp.headers.get('x-ratelimit-remaining')}", flush=True)
        time.sleep(0.1)
    save_cache(cache)


def main() -> int:
    papers = pd.read_csv(IN_PAPERS)
    papers = papers[(papers["work_id"].notna()) & (papers["is_work_primary"])].copy()
    papers["wid"] = papers["work_id"].str.extract(r"W(\d+)").astype("Int64")

    con = duckdb.connect()
    con.execute("SET threads=6;")
    con.register("ours", papers[["wid", "paper_uid"]])
    # 参照エッジを取り出し、引用先の DOI・出版年もスナップショットから付ける
    edges = con.execute(f"""
        WITH refs AS (
            SELECT o.paper_uid, o.wid AS src,
                   unnest(w.referenced_works) AS ref
            FROM ours o JOIN read_parquet('{SLIM_GLOB}') w ON w.work_id = o.wid
        )
        SELECT r.paper_uid, r.src, r.ref,
               s.doi AS ref_doi, s.publication_year AS ref_year
        FROM refs r LEFT JOIN read_parquet('{SLIM_GLOB}') s ON s.work_id = r.ref
    """).df()
    print(f"参照エッジ {len(edges):,} 本 / 論文 {edges['paper_uid'].nunique():,} 件", flush=True)

    ids = sorted(set(int(x) for x in edges["ref"].dropna()))
    cache = load_cache()
    partial = False
    try:
        fetch_titles(ids, cache)
    except QuotaExhausted as e:
        partial = True
        print(f"\n中断: {e}\n途中結果を書き出す。翌日そのまま再実行すれば続きから進む。", flush=True)
    finally:
        save_cache(cache)

    edges["ref_title"] = edges["ref"].map(lambda x: cache.get(str(int(x))) if pd.notna(x) else None)
    edges["ref_work_id"] = edges["ref"].map(lambda x: f"https://openalex.org/W{int(x)}" if pd.notna(x) else None)

    title_map = papers.set_index("paper_uid")["matched_title"].to_dict()
    site_map = papers.set_index("paper_uid")["title_site"].to_dict()
    edges["paper_title"] = edges["paper_uid"].map(title_map)
    edges["paper_title_site"] = edges["paper_uid"].map(site_map)
    edges["ref_seq"] = edges.groupby("paper_uid").cumcount() + 1

    out = edges[["paper_uid", "paper_title", "paper_title_site", "ref_seq",
                 "ref_work_id", "ref_doi", "ref_year", "ref_title"]]
    out = out.sort_values(["paper_uid", "ref_seq"])
    out.to_csv(OUT_DIR / "paper_references.csv", index=False)

    # 辞書形式（タイトル → 参考文献タイトルの一覧）。タイトル不明の参考文献は落とす
    d = {}
    for uid, g in out.groupby("paper_uid"):
        key = g["paper_title"].iloc[0] or g["paper_title_site"].iloc[0]
        d[key] = [t for t in g["ref_title"].tolist() if isinstance(t, str)]
    (OUT_DIR / "paper_references.json").write_text(
        json.dumps(d, ensure_ascii=False, indent=1))

    cov = out["ref_title"].notna().mean()
    print(f"\n出力: paper_references.csv  {len(out):,}行")
    print(f"      paper_references.json  {len(d):,}論文")
    print(f"      引用先タイトルの被覆 {100*cov:.1f}%")
    if partial:
        print("      ※ クォータ切れのため未完。再実行で続きが埋まる")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
