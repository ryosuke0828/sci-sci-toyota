"""分析用のテーブルを1論文1行にまとめる（段階3-5 の入力）。

4つの出力を結合する。

  papers.csv              … 基本情報（収集元・出版年・分野・被引用）
  sciscinet_metrics.csv   … 指標。**主軸**（新規性・定石らしさ・disruption・C10 ほか）
  paper_covariates.csv    … 説明変数と統制項（チーム規模・国際共同・学際性 ほか）
  paper_novelty.csv       … 自前で計算した新規性。**検証用と2025年以降の穴埋め**

指標の列は接頭辞で出所が分かるようにしてある。

  ss_*   … SciSciNet の公開値。主分析はこちら
  own_*  … 自前計算。頑健性の確認と、SciSciNet に無い2025年以降に使う

**2つを混ぜて1本の変数にしてはいけない。** 尺度が違う（新規性の中央値が自前113、公開217）。
どちらを使ったかを必ず明記する。

出力: data/derived/analysis/paper_analysis.csv

実行: ~/.venvs/scisci-rir/bin/python src/build_analysis_table.py
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
D = ROOT / "data" / "derived"
OUT_DIR = D / "analysis"
OUT_CSV = OUT_DIR / "paper_analysis.csv"


def main() -> int:
    papers = pd.read_csv(D / "papers" / "papers.csv")
    papers = papers[(papers["work_id"].notna()) & (papers["is_work_primary"])].copy()
    base = papers[["paper_uid", "work_id", "doi_norm", "source_org", "title_site",
                   "matched_title", "year_openalex", "type", "primary_field",
                   "primary_subfield", "cited_by_count", "referenced_works_count",
                   "n_authors", "institutions_distinct_count"]]

    ss = pd.read_csv(D / "papers" / "sciscinet_metrics.csv").drop(
        columns=["source_org", "year_openalex", "type"], errors="ignore")
    cov = pd.read_csv(D / "papers" / "paper_covariates.csv").drop(
        columns=["source_org", "year_openalex", "primary_field", "n_authors",
                 "referenced_works_count", "cited_by_count"], errors="ignore")
    own = pd.read_csv(D / "novelty" / "paper_novelty.csv").rename(columns={
        "median_z": "own_conventionality", "p10_z": "own_novelty",
        "n_pairs": "own_pairs", "n_pairs_with_z": "own_pairs_with_z",
        "year": "own_year"})

    df = (base.merge(ss, on="paper_uid", how="left")
               .merge(cov, on="paper_uid", how="left")
               .merge(own.drop(columns=["own_year"]), on="paper_uid", how="left"))

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT_CSV, index=False)

    print(f"出力: {OUT_CSV.relative_to(ROOT)}  {len(df):,}行 × {len(df.columns)}列\n")
    print("指標の被覆:")
    for c, lab in [("ss_novelty", "新規性(公開)"), ("own_novelty", "新規性(自前)"),
                   ("ss_disruption", "disruption(公開)"), ("ss_c10", "C10(公開)"),
                   ("ss_sleeping_beauty", "SB(公開)")]:
        print(f"  {lab:22} {df[c].notna().sum():>4} / {len(df)} ({100*df[c].notna().mean():.0f}%)")
    print("\n説明変数・統制項の被覆:")
    for c, lab in [("is_solo", "単著"), ("is_international", "国際共同"),
                   ("is_industry_academia_oa", "産学連携"), ("is_cross_org", "組織横断"),
                   ("n_ref_fields", "参考文献の分野数"), ("ref_field_hhi", "分野の集中度")]:
        s = df[c]
        if s.dtype == bool or set(s.dropna().unique()) <= {True, False}:
            print(f"  {lab:22} True {int(s.fillna(False).sum()):>4} / {len(df)}")
        else:
            print(f"  {lab:22} 非NULL {s.notna().sum():>4} / {len(df)}")
    print("\n両方の指標がある論文（頑健性の確認に使える）:")
    both = df["ss_novelty"].notna() & df["own_novelty"].notna()
    print(f"  {int(both.sum())} 件")
    print("\n公開値が無く自前値だけある論文（2025年以降が中心）:")
    only = df["ss_novelty"].isna() & df["own_novelty"].notna()
    print(f"  {int(only.sum())} 件  出版年の内訳: "
          f"{df.loc[only, 'year_openalex'].value_counts().sort_index().to_dict()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
