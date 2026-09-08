"""段階2-1: novelty / disruption / hot streak の文献を機械的に集める。

計画（docs/plans/novelty_hotstreak.md 段階2-1）は
「シード論文の前方・後方引用を OpenAlex スナップショットから辿り、100本超を機械収集」。

手元の works_slim（5億1,037万件、参照エッジ30.9億本）だけで完結する。
OpenAlex API は従量課金なので使わない。タイトルだけは持っていないので、
最後に必要な分だけ API で引く（1日1000件の枠内）。

手順:
  1. シード論文の DOI から work_id を引く
  2. 後方引用（シードが引いている文献）と前方引用（シードを引いている文献）を集める
  3. 何本のシードから参照されているか（被参照シード数）で並べる。
     複数のシードから引かれている文献ほど、この分野の中心にある
  4. 上位を候補一覧として出す

出力: data/derived/literature/seed_resolution.csv … シードDOIと work_id の対応
      data/derived/literature/candidates.csv      … 候補文献一覧

実行: ~/.venvs/scisci-rir/bin/python src/literature_harvest.py
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path

import duckdb
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
SLIM_GLOB = os.environ.get(
    "SCISCI_SLIM_GLOB", str(Path.home() / "scisci-data" / "works_slim" / "*.parquet"))
OUT_DIR = ROOT / "data" / "derived" / "literature"

# 計画に挙げたシード論文。DOI は本文・出版社サイトで確認したもの。
# 分類は「どの論点のシードか」であり、収集後の分類（段階2-2）とは別物。
SEEDS = [
    # --- novelty / atypicality ---
    ("10.1126/science.1240474", "Uzzi et al. 2013 Science, Atypical combinations", "novelty"),
    ("10.1016/j.respol.2014.12.009", "Lee, Walsh & Wang 2015 Res Policy, Creativity in scientific teams", "novelty"),
    ("10.1016/j.respol.2017.06.006", "Wang, Veugelers & Stephan 2017 Res Policy, Bias against novelty", "novelty"),
    ("10.1086/681257", "Foster, Rzhetsky & Evans 2015 ASR, Tradition and innovation", "novelty"),
    # --- disruption ---
    ("10.1287/mnsc.2015.2366", "Funk & Owen-Smith 2017 Manag Sci, Dynamic network measure", "disruption"),
    ("10.1038/s41586-019-0941-9", "Wu, Wang & Evans 2019 Nature, Large teams develop small teams disrupt", "disruption"),
    ("10.1038/s41586-022-05543-x", "Park, Leahey & Funk 2023 Nature, Papers and patents less disruptive", "disruption"),
    # --- hot streak / careers ---
    ("10.1038/s41586-018-0315-8", "Liu et al. 2018 Nature, Hot streaks", "hot_streak"),
    ("10.1038/s41467-021-25477-8", "Liu et al. 2021 Nat Commun, Understanding hot streaks", "hot_streak"),
    ("10.1126/science.aaf5239", "Sinatra et al. 2016 Science, Quantifying impact", "hot_streak"),
    # --- 総説・データ ---
    ("10.1126/science.aao0185", "Fortunato et al. 2018 Science, Science of science", "review"),
    ("10.1038/s41597-023-02198-9", "Lin et al. 2023 Sci Data, SciSciNet", "data"),
]


def norm_doi(d: str) -> str:
    return d.strip().lower().removeprefix("https://doi.org/")


def resolve_seeds(con: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    """シードの DOI を work_id に解決する。"""
    df = pd.DataFrame(SEEDS, columns=["doi", "label", "seed_group"])
    df["doi_norm"] = df["doi"].map(norm_doi)
    con.register("seeds_df", df)
    t = time.time()
    con.execute(f"""
        CREATE OR REPLACE TABLE seeds AS
        SELECT s.doi_norm, s.label, s.seed_group,
               w.work_id, w.publication_year, w.cited_by_count,
               len(w.referenced_works) AS n_refs
        FROM seeds_df s
        LEFT JOIN read_parquet('{SLIM_GLOB}') w
          ON lower(replace(w.doi, 'https://doi.org/', '')) = s.doi_norm
    """)
    # OpenAlex には同じ DOI に複数のレコードが登録されている例がある。
    # 2026-08-17 に確認した書誌の破損と同じ現象で、被引用0・参考文献1本のような
    # 中身のないレコードが混ざる。DOI ごとに被引用数が最大のものを残す
    con.execute("""
        CREATE OR REPLACE TABLE seeds AS
        SELECT * FROM (
            SELECT *, row_number() OVER (
                PARTITION BY doi_norm ORDER BY cited_by_count DESC NULLS LAST) AS rk
            FROM seeds
        ) WHERE rk = 1
    """)
    out = con.execute("SELECT * FROM seeds ORDER BY seed_group, publication_year").df()
    print(f"シードの解決 [{time.time()-t:.0f}秒]", flush=True)
    print(out[["doi_norm", "label", "work_id", "publication_year",
               "cited_by_count", "n_refs"]].to_string(index=False), flush=True)
    miss = out[out["work_id"].isna()]
    if len(miss):
        print(f"\n★ 解決できなかったシード {len(miss)} 件:", flush=True)
        print(miss[["doi_norm", "label"]].to_string(index=False), flush=True)
    return out


def collect(con: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    """後方引用と前方引用を集め、被参照シード数で並べる。"""
    t = time.time()
    # 後方: シードが引いている文献
    con.execute(f"""
        CREATE OR REPLACE TABLE backward AS
        SELECT s.work_id AS seed_id, unnest(w.referenced_works) AS cand
        FROM seeds s JOIN read_parquet('{SLIM_GLOB}') w ON w.work_id = s.work_id
    """)
    nb = con.execute("SELECT count(*) FROM backward").fetchone()[0]
    print(f"後方引用 {nb:,} 本  [{time.time()-t:.0f}秒]", flush=True)

    # 前方: シードを引いている文献。5億件を1回走査する
    t = time.time()
    con.execute(f"""
        CREATE OR REPLACE TABLE forward AS
        WITH e AS (
            SELECT work_id AS citing, unnest(referenced_works) AS cited
            FROM read_parquet('{SLIM_GLOB}')
            WHERE len(referenced_works) > 0
        )
        SELECT s.work_id AS seed_id, e.citing AS cand
        FROM e JOIN seeds s ON s.work_id = e.cited
    """)
    nf = con.execute("SELECT count(*) FROM forward").fetchone()[0]
    print(f"前方引用 {nf:,} 本  [{time.time()-t:.0f}秒]", flush=True)

    # 候補を統合し、何本のシードとつながっているかで並べる
    t = time.time()
    con.execute(f"""
        CREATE OR REPLACE TABLE cand AS
        WITH u AS (
            SELECT cand, seed_id, 'backward' AS direction FROM backward
            UNION ALL
            SELECT cand, seed_id, 'forward' FROM forward
        ),
        agg AS (
            SELECT cand,
                   count(DISTINCT seed_id) AS n_seeds,
                   count(DISTINCT CASE WHEN direction='backward' THEN seed_id END) AS n_back,
                   count(DISTINCT CASE WHEN direction='forward'  THEN seed_id END) AS n_fwd,
                   string_agg(DISTINCT seed_id::VARCHAR, ',') AS seed_ids
            FROM u GROUP BY cand
        )
        SELECT a.*, w.doi, w.publication_year, w.type, w.cited_by_count,
               w.source_id, w.field_id, len(w.referenced_works) AS n_refs
        FROM agg a LEFT JOIN read_parquet('{SLIM_GLOB}') w ON w.work_id = a.cand
        WHERE w.publication_year IS NOT NULL
    """)
    n = con.execute("SELECT count(*) FROM cand").fetchone()[0]
    print(f"候補 {n:,} 件  [{time.time()-t:.0f}秒]", flush=True)
    return con.execute("""
        SELECT * FROM cand ORDER BY n_seeds DESC, cited_by_count DESC
    """).df()


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect()
    con.execute("SET threads=8; SET preserve_insertion_order=false;")

    seeds = resolve_seeds(con)
    seeds.to_csv(OUT_DIR / "seed_resolution.csv", index=False)
    if seeds["work_id"].isna().all():
        print("シードが1件も解決できなかった", flush=True)
        return 1

    cand = collect(con)
    cand.to_csv(OUT_DIR / "candidates.csv", index=False)

    summary = {
        "seeds_total": int(len(seeds)),
        "seeds_resolved": int(seeds["work_id"].notna().sum()),
        "candidates": int(len(cand)),
        "by_n_seeds": cand["n_seeds"].value_counts().sort_index(ascending=False).to_dict(),
        "candidates_ge2_seeds": int((cand["n_seeds"] >= 2).sum()),
        "candidates_ge3_seeds": int((cand["n_seeds"] >= 3).sum()),
    }
    (OUT_DIR / "harvest_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print("\n" + json.dumps(summary, ensure_ascii=False, indent=2, default=str), flush=True)
    print(f"\n出力: {OUT_DIR}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
