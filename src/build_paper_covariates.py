"""論文単位の共変量をまとめる（段階2の残件3・段階3-5の入力）。

段階2の文献調査で決めた説明変数と統制項を、1論文1行の表にする。
指標（novelty / disruption）そのものは含めない。突き合わせは段階3で行う。

出典と根拠は `docs/reports/novelty_hotstreak_literature.md` の7節にある。要点だけ再掲する。

  - チーム規模 … Uzzi et al. 2013 本体が「チームは単著より37.7%多く新規の組み合わせを入れる」
  - 国際共同 … Wagner et al. 2019 が Uzzi の指標そのもので国際共同を扱っている
  - 学際性 … Fontana et al. 2020 の「Uzzi の指標は学際性と重なる」への切り分けに要る。**統制項**
  - 参考文献数 … 2026-09-08 の自前検証で p10_z と順位相関 -0.406。**統制しないと見かけの関係が出る**

産学連携は2通りに作る。所属文字列から作ったもの（`src/normalize_affiliations.py`）と、
OpenAlex の機関種別から作ったもの。両者は一致しないので、突き合わせて食い違いを見るために両方残す。

入力: data/derived/papers/papers.csv
      data/derived/papers/authorship_affiliations.csv
      ~/scisci-data/works_slim/*.parquet
      ~/scisci-data/institutions.parquet   （無ければ OpenAlex から作る）
出力: data/derived/papers/paper_covariates.csv

実行: ~/.venvs/scisci-rir/bin/python src/build_paper_covariates.py
"""

from __future__ import annotations

import json
import os
import urllib.request
from pathlib import Path

import duckdb
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
IN_PAPERS = ROOT / "data" / "derived" / "papers" / "papers.csv"
IN_AFFIL = ROOT / "data" / "derived" / "papers" / "authorship_affiliations.csv"
OUT_CSV = ROOT / "data" / "derived" / "papers" / "paper_covariates.csv"
SLIM_GLOB = os.environ.get(
    "SCISCI_SLIM_GLOB", str(Path.home() / "scisci-data" / "works_slim" / "*.parquet"))
INST_PARQUET = Path(os.environ.get(
    "SCISCI_INST_PARQUET", str(Path.home() / "scisci-data" / "institutions.parquet")))
INST_MANIFEST = "https://openalex.s3.amazonaws.com/data/parquet/institutions/manifest.json"


def ensure_institutions(con: duckdb.DuckDBPyConnection) -> None:
    """機関の国コードと種別の表を用意する。96MBしかないので毎回作り直してもよい。"""
    if INST_PARQUET.exists():
        con.execute(f"CREATE OR REPLACE TABLE inst AS SELECT * FROM read_parquet('{INST_PARQUET}')")
        return
    con.execute("INSTALL httpfs; LOAD httpfs;")
    with urllib.request.urlopen(INST_MANIFEST, timeout=60) as r:
        man = json.load(r)
    files = [f["url"].replace("s3://openalex/", "https://openalex.s3.amazonaws.com/")
             for f in (man["files"] if "files" in man else man["entities"][0]["files"])]
    con.execute(f"""
        CREATE OR REPLACE TABLE inst AS
        SELECT try_cast(substr(id, 23) AS UBIGINT) AS inst_id, country_code, type, display_name
        FROM read_parquet({files})
    """)
    INST_PARQUET.parent.mkdir(parents=True, exist_ok=True)
    con.execute(f"COPY inst TO '{INST_PARQUET}' (FORMAT PARQUET)")


def main() -> int:
    papers = pd.read_csv(IN_PAPERS)
    papers = papers[(papers["work_id"].notna()) & (papers["is_work_primary"])].copy()
    papers["wid"] = papers["work_id"].str.extract(r"W(\d+)").astype("Int64")

    con = duckdb.connect()
    con.execute("SET threads=6;")
    ensure_institutions(con)
    con.register("ours", papers[["wid", "paper_uid"]])

    # 機関から作る変数: 関与国数、大学の有無、企業の有無
    inst_vars = con.execute(f"""
        WITH e AS (SELECT o.paper_uid, unnest(w.institution_ids) AS iid
                   FROM ours o JOIN read_parquet('{SLIM_GLOB}') w ON w.work_id = o.wid),
             j AS (SELECT e.paper_uid, i.country_code, i.type
                   FROM e LEFT JOIN inst i ON i.inst_id = e.iid)
        SELECT paper_uid,
               count(DISTINCT country_code) AS n_countries,
               max(CASE WHEN type = 'education'  THEN 1 ELSE 0 END) AS has_university_oa,
               max(CASE WHEN type = 'company'    THEN 1 ELSE 0 END) AS has_company_oa,
               max(CASE WHEN type = 'government' THEN 1 ELSE 0 END) AS has_government_oa
        FROM j GROUP BY paper_uid
    """).df()

    # 参考文献の分野の広がり。hhi は1に近いほど単一分野に偏る（学際性の逆）
    field_vars = con.execute(f"""
        WITH refs AS (SELECT o.paper_uid, unnest(w.referenced_works) AS ref
                      FROM ours o JOIN read_parquet('{SLIM_GLOB}') w ON w.work_id = o.wid),
             f AS (SELECT r.paper_uid, s.field_id
                   FROM refs r JOIN read_parquet('{SLIM_GLOB}') s ON s.work_id = r.ref
                   WHERE s.field_id IS NOT NULL),
             byfield AS (SELECT paper_uid, field_id, count(*) AS cnt FROM f GROUP BY 1, 2)
        SELECT paper_uid,
               sum(cnt)   AS n_refs_with_field,
               count(*)   AS n_ref_fields,
               sum(pow(cnt, 2)) / pow(sum(cnt), 2) AS ref_field_hhi
        FROM byfield GROUP BY paper_uid
    """).df()

    # 所属文字列から作る変数（段階0-4 の出力）
    aff = pd.read_csv(IN_AFFIL)
    aff_vars = aff.groupby("paper_uid").agg(
        has_university_affil=("is_university", "max"),
        has_company_affil=("is_company", "max"),
        n_toyota_orgs_paper=("toyota_org", lambda s: s.dropna().str.split("|").explode().nunique()),
    ).reset_index()

    out = (papers[["paper_uid", "source_org", "year_openalex", "primary_field",
                   "n_authors", "referenced_works_count", "cited_by_count"]]
           .merge(inst_vars, on="paper_uid", how="left")
           .merge(field_vars, on="paper_uid", how="left")
           .merge(aff_vars, on="paper_uid", how="left"))

    out["is_international"] = (out["n_countries"].fillna(0) >= 2)
    out["is_solo"] = (out["n_authors"] == 1)
    # 産学連携は2通り。一致しないので両方残す
    out["is_industry_academia_oa"] = (out["has_university_oa"].fillna(0).astype(bool)
                                      & out["has_company_oa"].fillna(0).astype(bool))
    out["is_industry_academia_affil"] = (out["has_university_affil"].fillna(False).astype(bool)
                                         & out["has_company_affil"].fillna(False).astype(bool))
    out["is_cross_org"] = (out["n_toyota_orgs_paper"].fillna(0) >= 2)

    out.to_csv(OUT_CSV, index=False)
    print(f"出力: {OUT_CSV.relative_to(ROOT)}  {len(out):,}行 × {len(out.columns)}列\n")
    print("被覆:")
    for c in ["n_countries", "n_ref_fields", "has_university_affil"]:
        print(f"  {c:24} {out[c].notna().sum():>4} / {len(out)}")
    print("\n変数の分布:")
    for c in ["is_solo", "is_international", "is_industry_academia_oa",
              "is_industry_academia_affil", "is_cross_org"]:
        print(f"  {c:28} True {int(out[c].sum()):>4} / {len(out)}")
    print("\n産学連携の2通りの一致:")
    print(pd.crosstab(out["is_industry_academia_oa"], out["is_industry_academia_affil"],
                      rownames=["機関種別から"], colnames=["所属文字列から"]).to_string())
    print("\n組織別の学際性（参考文献の分野の集中度、1に近いほど単一分野）:")
    print(out.groupby("source_org").agg(
        論文=("paper_uid", "size"),
        分野数中央値=("n_ref_fields", "median"),
        集中度中央値=("ref_field_hhi", "median")).round(3).to_string())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
