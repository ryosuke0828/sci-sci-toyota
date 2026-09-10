"""自前で計算した Uzzi の指標を、SciSciNet の公開値と突き合わせて検算する（段階3-3）。

段階1-1 で実装の食い違いを5点見つけて直した（2026-09-10）。直したものが本当に
SciSciNet と同じ定義になっているかは、公開値との相関でしか確かめられない。

**データの入手先について（2026-09-10 に訂正）**

当初 Hugging Face の `cssi/SciSciGPT-SciSciNet` を使う予定だったが、これは
SciSciGPT のデモ用に間引いた **1,119万件の抜粋**（本体は1.34億件）で、我々の論文は
DOI がある471件中4件しか含まれていなかった。検算には使えない。

代わりに SciSciNet v2 の公式配布先である Google Cloud Storage を使う。
`gs://sciscinet-neo/v2/sciscinet_papers.parquet`（5.26GB）は**匿名で読めて Parquet
なので、必要な列だけ範囲リクエストで取れる**。ログインもトークンも要らない。

**突き合わせは OpenAlex の work_id で行う。** v2 の `paperid` は `W112393110` の形の
OpenAlex Work ID そのものなので、DOI を経由せずに結合できる（DOI が無い論文も拾える）。
なお v2 の `doi` 列は `https://doi.org/...` の形で前置きが付いており、素の DOI とは一致しない。

突き合わせる列:
  Atyp_Median_Z … 中央値 z（conventionality）。我々の median_z に対応
  Atyp_10pct_Z  … 10パーセンタイル z（novelty）。我々の p10_z に対応
  Atyp_Pairs    … 有効なジャーナル対の数。我々の n_pairs_with_z に対応。
                  同一誌どうしの対を入れたかどうかがここに出るので、修正2の直接の検証になる

出力: data/derived/novelty/sciscinet_check.csv     … 論文ごとの自前値と公開値
      data/derived/novelty/sciscinet_check.json    … 相関などの要約

実行: ~/.venvs/scisci-rir/bin/python src/verify_novelty_sciscinet.py
"""

from __future__ import annotations

import json
from pathlib import Path

import duckdb
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
IN_NOVELTY = ROOT / "data" / "derived" / "novelty" / "paper_novelty.csv"
IN_PAPERS = ROOT / "data" / "derived" / "papers" / "papers.csv"
OUT_DIR = ROOT / "data" / "derived" / "novelty"

SS_URL = "https://storage.googleapis.com/sciscinet-neo/v2/sciscinet_papers.parquet"


def main() -> int:
    nov = pd.read_csv(IN_NOVELTY)
    papers = pd.read_csv(IN_PAPERS)[["paper_uid", "work_id", "doi_norm", "source_org", "year_openalex"]]
    ours = nov.merge(papers, on="paper_uid", how="left")
    ours = ours[ours["work_id"].notna()].copy()
    ours["paperid"] = ours["work_id"].str.extract(r"(W\d+)")
    ours = ours[ours["paperid"].notna()]
    print(f"自前の値 {len(nov)} 件のうち work_id があるのは {len(ours)} 件", flush=True)

    con = duckdb.connect()
    con.execute("SET threads=6; INSTALL httpfs; LOAD httpfs;")
    con.register("ours_df", ours[["paper_uid", "paperid"]])
    ss = con.execute(f"""
        SELECT s.paperid, s.year AS ss_year, s.doctype,
               s."Atyp_Median_Z" AS ss_median_z,
               s."Atyp_10pct_Z"  AS ss_p10_z,
               s."Atyp_Pairs"    AS ss_pairs,
               s.disruption      AS ss_disruption,
               s.reference_count AS ss_ref_count
        FROM read_parquet('{SS_URL}') s
        WHERE s.paperid IN (SELECT paperid FROM ours_df)
    """).df()
    print(f"SciSciNet 側で見つかったのは {len(ss)} 件", flush=True)

    m = ours.merge(ss, on="paperid", how="inner")
    n_found = len(m)
    m = m[m["ss_median_z"].notna() & m["ss_p10_z"].notna()]
    print(f"うち公開値が入っているのは {len(m)} 件", flush=True)
    if len(m) == 0:
        print("突き合わせられる論文が無い。検算できない。")
        return 1

    out = {"n_ours": int(len(nov)), "n_with_doi": int(len(ours)),
           "n_found_in_sciscinet": int(n_found), "n_comparable": int(len(m)),
           "ss_year_range": [int(m["ss_year"].min()), int(m["ss_year"].max())]}
    for a, b, label in [("median_z", "ss_median_z", "conventionality"),
                        ("p10_z", "ss_p10_z", "novelty"),
                        ("n_pairs_with_z", "ss_pairs", "対の数")]:
        out[label] = {
            "spearman": round(float(m[a].corr(m[b], method="spearman")), 3),
            "pearson": round(float(m[a].corr(m[b], method="pearson")), 3),
            "ours_median": round(float(m[a].median()), 2),
            "sciscinet_median": round(float(m[b].median()), 2),
        }

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    m.to_csv(OUT_DIR / "sciscinet_check.csv", index=False)
    (OUT_DIR / "sciscinet_check.json").write_text(json.dumps(out, ensure_ascii=False, indent=2))

    print("\n=== 検算の結果 ===")
    for label in ("conventionality", "novelty", "対の数"):
        d = out[label]
        print(f"  {label:16} 順位相関 {d['spearman']:+.3f} / 積率相関 {d['pearson']:+.3f}"
              f"  （中央値 自前 {d['ours_median']} vs 公開 {d['sciscinet_median']}）")
    print(f"\n  SciSciNet 側の対象年: {out['ss_year_range'][0]}〜{out['ss_year_range'][1]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
