"""分野×年でマッチした一般論文を抽出し、トヨタ論文の指標を順位（パーセンタイル）に直す（段階3-4）。

トヨタの論文の新規性が「高い」のか「低い」のかは、比べる相手がないと言えない。
同じ分野・同じ年に出た一般の論文のなかで何パーセントの位置にあるかを出す。

手順:
  1. トヨタ論文が存在する分野×年の升目を洗い出す（157升）
  2. 各升目から一般論文を無作為に N 件（既定3,000）抽出する。スナップショットを1回走査し、
     升目ごとに乱数順の順位を振って上位 N 件を取る
  3. 抽出した論文の指標を SciSciNet から引く（トヨタ論文と同じ出所でなければ比較にならない）
  4. 升目ごとに、トヨタ論文の値が一般論文の何パーセントの位置にあるかを求める

**参考文献数による層別も併せて出す。** 2026-09-08 に、新規性（下から1割の値）が
ジャーナル対の数と順位相関 -0.406 を持つことを確認している。分野と年だけを揃えても
参考文献の多寡で見かけの差が出るため、参考文献数の四分位で分けた順位も併記する。

入力: data/derived/analysis/paper_analysis.csv
      ~/scisci-data/works_slim/*.parquet
出力: data/derived/analysis/baseline_sample.csv   … 抽出した一般論文と指標
      data/derived/analysis/paper_percentiles.csv … トヨタ論文の順位

実行: ~/.venvs/scisci-rir/bin/python src/build_matched_baseline.py
"""

from __future__ import annotations

import os
from pathlib import Path

import duckdb
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
D = ROOT / "data" / "derived"
IN_ANALYSIS = D / "analysis" / "paper_analysis.csv"
OUT_SAMPLE = D / "analysis" / "baseline_sample.csv"
OUT_PCT = D / "analysis" / "paper_percentiles.csv"
SLIM_GLOB = os.environ.get(
    "SCISCI_SLIM_GLOB", str(Path.home() / "scisci-data" / "works_slim" / "*.parquet"))
SS_URL = "https://storage.googleapis.com/sciscinet-neo/v2/sciscinet_papers.parquet"
N_PER_CELL = int(os.environ.get("SCISCI_N_PER_CELL", "3000"))

METRICS = ["ss_novelty", "ss_conventionality", "ss_disruption", "ss_c10"]


def main() -> int:
    a = pd.read_csv(IN_ANALYSIS)
    ours = a[a["ss_novelty"].notna() | a["own_novelty"].notna()].copy()
    ours["paperid"] = ours["work_id"].str.extract(r"(W\d+)")
    ours["wid"] = ours["work_id"].str.extract(r"W(\d+)").astype("Int64")
    print(f"トヨタ論文（指標あり）: {len(ours)} 件", flush=True)

    con = duckdb.connect()
    con.execute("SET threads=6; SET preserve_insertion_order=false; INSTALL httpfs; LOAD httpfs;")
    con.register("ours_df", ours[["paper_uid", "wid", "paperid"]])

    # トヨタ論文の分野と年をスナップショットから取る（名称ではなく分野IDで揃える）
    con.execute(f"""
        CREATE OR REPLACE TABLE ours AS
        SELECT o.paper_uid, o.wid, o.paperid, w.field_id, w.publication_year AS year
        FROM ours_df o JOIN read_parquet('{SLIM_GLOB}') w ON w.work_id = o.wid
        WHERE w.field_id IS NOT NULL AND w.publication_year IS NOT NULL
    """)
    cells = con.execute("SELECT DISTINCT field_id, year FROM ours").df()
    print(f"分野×年の升目: {len(cells)} 個 / 1升あたり最大 {N_PER_CELL:,} 件を抽出", flush=True)

    # スナップショットを1回だけ走査し、升目ごとに乱数順で上位 N 件を取る
    con.execute(f"""
        CREATE OR REPLACE TABLE sample AS
        WITH pool AS (
            SELECT w.work_id, w.field_id, w.publication_year AS year,
                   len(w.referenced_works) AS n_refs
            FROM read_parquet('{SLIM_GLOB}') w
            SEMI JOIN (SELECT DISTINCT field_id, year FROM ours) c
              ON c.field_id = w.field_id AND c.year = w.publication_year
            WHERE w.type = 'article' AND len(w.referenced_works) > 0
              AND w.work_id NOT IN (SELECT wid FROM ours)
        ),
        ranked AS (
            SELECT *, row_number() OVER (PARTITION BY field_id, year ORDER BY random()) AS rn
            FROM pool
        )
        SELECT work_id, field_id, year, n_refs FROM ranked WHERE rn <= {N_PER_CELL}
    """)
    n = con.execute("SELECT count(*) FROM sample").fetchone()[0]
    print(f"抽出した一般論文: {n:,} 件", flush=True)

    # 抽出した論文の指標を SciSciNet から引く
    con.execute(f"""
        CREATE OR REPLACE TABLE sample_ss AS
        SELECT s.work_id, s.field_id, s.year, s.n_refs,
               x."Atyp_10pct_Z"  AS ss_novelty,
               x."Atyp_Median_Z" AS ss_conventionality,
               x.disruption      AS ss_disruption,
               x."C10"           AS ss_c10
        FROM sample s
        LEFT JOIN read_parquet('{SS_URL}') x
          ON x.paperid = 'W' || CAST(s.work_id AS VARCHAR)
    """)
    smp = con.execute("SELECT * FROM sample_ss").df()
    smp.to_csv(OUT_SAMPLE, index=False)
    print(f"\n一般論文の指標の被覆:", flush=True)
    for m in METRICS:
        print(f"  {m:20} {smp[m].notna().sum():>8,} / {len(smp):,} ({100*smp[m].notna().mean():.0f}%)")

    # 升目ごとに順位を求める
    o = con.execute("SELECT paper_uid, wid, field_id, year FROM ours").df()
    o = o.merge(a[["paper_uid"] + METRICS + ["referenced_works_count"]], on="paper_uid", how="left")
    rows = []
    for (f, y), g in o.groupby(["field_id", "year"]):
        base = smp[(smp["field_id"] == f) & (smp["year"] == y)]
        for r in g.itertuples():
            rec = {"paper_uid": r.paper_uid, "field_id": f, "year": y,
                   "n_baseline": int(len(base)), "n_refs": r.referenced_works_count}
            for m in METRICS:
                v = getattr(r, m)
                b = base[m].dropna()
                rec[f"{m}_pct"] = round(100.0 * (b < v).mean(), 1) if (pd.notna(v) and len(b) >= 30) else None
                rec[f"{m}_n_base"] = int(len(b))
            # 参考文献数まで揃えた順位。分野と年だけを揃えても参考文献の多寡で順位が動くため
            # （2026-09-14 の実測で、参考文献が少ない層の新規性順位67に対し中位層は29）、
            # その論文と参考文献数が近い一般論文（±35%の範囲）だけを相手に取り直す
            if pd.notna(r.referenced_works_count) and r.referenced_works_count > 0:
                lo, hi = r.referenced_works_count * 0.65, r.referenced_works_count * 1.35
                base_r = base[(base["n_refs"] >= lo) & (base["n_refs"] <= hi)]
                for m in METRICS:
                    v = getattr(r, m)
                    b = base_r[m].dropna()
                    rec[f"{m}_pct_ref"] = round(100.0 * (b < v).mean(), 1) if (pd.notna(v) and len(b) >= 30) else None
                    rec[f"{m}_n_base_ref"] = int(len(b))
            rows.append(rec)
    pct = pd.DataFrame(rows)
    pct.to_csv(OUT_PCT, index=False)

    print(f"\n出力: {OUT_PCT.relative_to(ROOT)}  {len(pct):,}行")
    print("順位が出せた件数（分野×年で揃えた場合／参考文献数まで揃えた場合）:")
    for m in METRICS:
        c1 = pct[f"{m}_pct"].notna().sum()
        c2 = pct[f"{m}_pct_ref"].notna().sum()
        print(f"  {m:20} {c1:>4}件 中央値 {pct[f'{m}_pct'].median():5.1f}  /  "
              f"{c2:>4}件 中央値 {pct[f'{m}_pct_ref'].median():5.1f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
