"""SciSciNet が公開している指標を、我々の論文について取り込む。

2026-09-14 に方針を変えた。当初「すべて自前実装、SciSciNet は検算のみ」としていたが、
被覆率を測ったところ SciSciNet は我々の852件のうち741件（87%）を持っており、
disruption は741件、新規性は580件に値が入っていた。自前計算（581件）とほぼ同数である。
自前でしか出せないのは91件で、その8割は2024年以降（SciSciNet のデータが2024年で終わるため）。

したがって **SciSciNet の値を主軸にし、自前の値は検証と2025年以降の穴埋めに使う**。
これにより段階0-3（被引用テーブルの構築）と段階3-2（CD index の自前計算）を省ける。

**自前の値と混ぜてはいけない。** 尺度が違う（新規性の中央値が自前113に対し公開217）。
別々の列として持ち、主分析は片方で通す。

入手先: gs://sciscinet-neo/v2/sciscinet_papers.parquet（5.26GB、匿名で読める Parquet）
結合キー: OpenAlex の work_id（v2 の `paperid` がそれ。`doi` は前置き付きで使いにくい）

出力: data/derived/papers/sciscinet_metrics.csv … 1論文1行

実行: ~/.venvs/scisci-rir/bin/python src/fetch_sciscinet_metrics.py
"""

from __future__ import annotations

from pathlib import Path

import duckdb
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
IN_PAPERS = ROOT / "data" / "derived" / "papers" / "papers.csv"
OUT_CSV = ROOT / "data" / "derived" / "papers" / "sciscinet_metrics.csv"
SS_URL = "https://storage.googleapis.com/sciscinet-neo/v2/sciscinet_papers.parquet"


def main() -> int:
    p = pd.read_csv(IN_PAPERS)
    p = p[(p["work_id"].notna()) & (p["is_work_primary"])].copy()
    p["paperid"] = p["work_id"].str.extract(r"(W\d+)")
    print(f"対象 {len(p)} 件", flush=True)

    con = duckdb.connect()
    con.execute("SET threads=6; INSTALL httpfs; LOAD httpfs;")
    con.register("ours", p[["paper_uid", "paperid"]])
    ss = con.execute(f"""
        SELECT s.paperid,
               s.year            AS ss_year,
               s.doctype         AS ss_doctype,
               s.is_retracted    AS ss_is_retracted,
               s.reference_count AS ss_reference_count,
               s.citation_count  AS ss_citation_count,
               s."C5"            AS ss_c5,
               s."C10"           AS ss_c10,
               s.disruption      AS ss_disruption,
               s."Atyp_Median_Z" AS ss_conventionality,
               s."Atyp_10pct_Z"  AS ss_novelty,
               s."Atyp_Pairs"    AS ss_atyp_pairs,
               s."SB_B"          AS ss_sleeping_beauty,
               s.team_size       AS ss_team_size,
               s.institution_count AS ss_institution_count,
               s.patent_count    AS ss_patent_count
        FROM read_parquet('{SS_URL}') s
        WHERE s.paperid IN (SELECT paperid FROM ours)
    """).df()
    print(f"SciSciNet に存在: {len(ss)} 件", flush=True)

    out = p[["paper_uid", "paperid", "source_org", "year_openalex", "type"]].merge(
        ss, on="paperid", how="left")
    out.to_csv(OUT_CSV, index=False)

    print(f"\n出力: {OUT_CSV.relative_to(ROOT)}  {len(out):,}行 × {len(out.columns)}列\n")
    print("指標ごとの被覆:")
    for c, lab in [("ss_novelty", "新規性"), ("ss_conventionality", "定石らしさ"),
                   ("ss_disruption", "disruption"), ("ss_c10", "C10"),
                   ("ss_sleeping_beauty", "sleeping beauty"), ("ss_team_size", "チーム規模")]:
        print(f"  {lab:18} {out[c].notna().sum():>4} / {len(out)} ({100*out[c].notna().mean():.1f}%)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
