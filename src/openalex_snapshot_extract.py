"""OpenAlex の Parquet スナップショットから、novelty / disruption / hot streak に必要な列だけを抽出する。

背景: OpenAlex API は従量課金（無料枠 1日1000リクエスト）で、数千万論文の参照文献を引くには使えない。
      公開スナップショット s3://openalex/data/parquet/ を列プルーニングして読む。
      必要な列は全体 725GB の 6.9%（約50GB）で済む（実測、docs/plans/novelty_hotstreak.md）。

設計:
  - 入力ファイル1本 = 出力ファイル1本。出力が既にあればスキップするので、途中で止めても再開できる。
  - 書き込みは .tmp に出してから rename する。中断した書きかけを「完了」と誤認しないため。
  - ID は "https://openalex.org/W123" の形。前置21文字＋種別1文字を落として整数にする。
    容量が減り、後段のジャーナル対の列挙・結合が速くなる。
  - 出力先は Google Drive の外（~/scisci-data/）。Drive 内に50GBを置くと同期が破綻する。
  - 並列はスレッドで行う。当初 ProcessPoolExecutor を使ったが、親を kill しても
    ワーカーが PPID=1 の孤児として生き残り、回線を食い続ける事故が起きた（2026-08-24）。
    DuckDB はクエリ実行中に GIL を解放するので、スレッドでも並列性は落ちない。

環境変数:
  SCISCI_SNAPSHOT_OUT   出力ディレクトリ（既定 ~/scisci-data/works_slim）
  SCISCI_SNAPSHOT_JOBS  並列プロセス数（既定 8）
"""

from __future__ import annotations

import json
import os
import signal
import sys
import threading
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

MANIFEST_URL = "https://openalex.s3.amazonaws.com/data/parquet/works/manifest.json"
S3_PREFIX = "s3://openalex/"
HTTP_PREFIX = "https://openalex.s3.amazonaws.com/"

OUT_DIR = Path(os.environ.get("SCISCI_SNAPSHOT_OUT", Path.home() / "scisci-data" / "works_slim"))
JOBS = int(os.environ.get("SCISCI_SNAPSHOT_JOBS", "8"))
RETRIES = 3

# "https://openalex.org/" は21文字。22文字目が種別記号(W/A/S/I)、23文字目から数字。
# try_cast にしておき、想定外の形式は NULL に落として後で件数を数える。
SELECT_SQL = """
SELECT
    try_cast(substr(id, 23) AS UBIGINT)                              AS work_id,
    doi,
    publication_year,
    type,
    cited_by_count,
    try_cast(substr(primary_location.source.id, 23) AS UBIGINT)      AS source_id,
    try_cast(substr(primary_topic.field.id, 29) AS USMALLINT)        AS field_id,
    list_transform(referenced_works, w -> try_cast(substr(w, 23) AS UBIGINT))
                                                                     AS referenced_works,
    list_transform(authorships, a -> try_cast(substr(a.author.id, 23) AS UBIGINT))
                                                                     AS author_ids,
    flatten(list_transform(authorships,
        a -> list_transform(a.institutions, i -> try_cast(substr(i.id, 23) AS UBIGINT))))
                                                                     AS institution_ids
FROM read_parquet({urls})
"""


def load_manifest() -> list[dict]:
    with urllib.request.urlopen(MANIFEST_URL, timeout=60) as r:
        d = json.load(r)
    return d["files"] if "files" in d else d["entities"][0]["files"]


def out_name(s3_url: str) -> str:
    # s3://openalex/data/parquet/works/updated_date=2025-11-06/part_1068.parquet
    #   -> 2025-11-06__part_1068.parquet
    parts = s3_url.rstrip("/").split("/")
    return f"{parts[-2].split('=')[-1]}__{parts[-1]}"


STOP = threading.Event()


def _on_signal(signum, frame):
    print(f"\nシグナル {signum} を受けた。走行中の分を書き捨てて終了する", flush=True)
    STOP.set()


def extract_one(task: tuple[str, str]) -> dict:
    """1ファイルを読んで必要列だけ書き出す。ワーカースレッドで実行される。"""
    import duckdb

    s3_url, out_path_s = task
    if STOP.is_set():
        return {"url": s3_url, "ok": False, "error": "中断", "skipped": True}
    out_path = Path(out_path_s)
    http_url = s3_url.replace(S3_PREFIX, HTTP_PREFIX)
    tmp_path = out_path.with_suffix(".tmp")

    last_err = None
    for attempt in range(RETRIES):
        if STOP.is_set():
            return {"url": s3_url, "ok": False, "error": "中断", "skipped": True}
        t0 = time.time()
        try:
            con = duckdb.connect()
            # ネットワーク律速なので、プロセスあたりのスレッドは絞ってCPUの取り合いを避ける
            con.execute("SET threads=2; INSTALL httpfs; LOAD httpfs;")
            q = SELECT_SQL.format(urls=repr([http_url]))
            con.execute(
                f"COPY ({q}) TO '{tmp_path}' (FORMAT PARQUET, COMPRESSION ZSTD)"
            )
            n = con.execute(
                f"SELECT count(*) FROM read_parquet('{tmp_path}')"
            ).fetchone()[0]
            con.close()
            tmp_path.rename(out_path)
            return {
                "url": s3_url,
                "ok": True,
                "rows": n,
                "bytes": out_path.stat().st_size,
                "secs": time.time() - t0,
                "attempt": attempt + 1,
            }
        except Exception as e:  # ネットワーク断・S3の一時エラーを想定
            last_err = f"{type(e).__name__}: {e}"
            tmp_path.unlink(missing_ok=True)
            time.sleep(5 * (attempt + 1))
    return {"url": s3_url, "ok": False, "error": last_err}


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    signal.signal(signal.SIGTERM, _on_signal)
    signal.signal(signal.SIGINT, _on_signal)

    # 前回の中断で残った書きかけを掃除する
    stale = list(OUT_DIR.glob("*.tmp"))
    for f in stale:
        f.unlink(missing_ok=True)
    if stale:
        print(f"前回の書きかけ {len(stale)} 件を削除した", flush=True)

    files = load_manifest()
    total_src_bytes = sum(f["meta"]["content_length"] for f in files)
    print(f"マニフェスト: {len(files)} ファイル / 元サイズ {total_src_bytes/1e9:.1f} GB", flush=True)

    tasks = []
    skipped = 0
    for f in files:
        op = OUT_DIR / out_name(f["url"])
        if op.exists():
            skipped += 1
            continue
        tasks.append((f["url"], str(op)))
    print(f"未処理 {len(tasks)} / 済み {skipped}", flush=True)
    if not tasks:
        print("すべて完了済み", flush=True)
        return 0

    log_path = OUT_DIR.parent / "extract_progress.jsonl"
    done = failed = aborted = 0
    rows_tot = bytes_tot = 0
    t_start = time.time()

    with ThreadPoolExecutor(max_workers=JOBS) as ex, log_path.open("a") as log:
        futs = {ex.submit(extract_one, t): t for t in tasks}
        for fut in as_completed(futs):
            r = fut.result()
            log.write(json.dumps(r) + "\n")
            log.flush()
            if r["ok"]:
                done += 1
                rows_tot += r["rows"]
                bytes_tot += r["bytes"]
            elif r.get("skipped"):
                aborted += 1
                continue
            else:
                failed += 1
                print(f"  失敗: {r['url']} — {r['error']}", flush=True)
            if (done + failed) % 25 == 0 or (done + failed + aborted) == len(tasks):
                el = time.time() - t_start
                rate = (done + failed) / el
                eta = (len(tasks) - done - failed) / rate / 60 if rate > 0 else float("nan")
                print(
                    f"  {done+failed}/{len(tasks)}  成功{done} 失敗{failed}  "
                    f"{rows_tot/1e6:.1f}M行  出力{bytes_tot/1e9:.1f}GB  "
                    f"経過{el/60:.0f}分  残り約{eta:.0f}分",
                    flush=True,
                )

    print(
        f"終了: 成功{done} 失敗{failed} 中断{aborted} / {rows_tot/1e6:.1f}M行 / "
        f"出力{bytes_tot/1e9:.1f}GB / {(time.time()-t_start)/60:.0f}分",
        flush=True,
    )
    for f in OUT_DIR.glob("*.tmp"):
        f.unlink(missing_ok=True)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
