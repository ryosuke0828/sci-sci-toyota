"""進捗報告資料（2026年9月）に載せる数字を、元の表から計算して numbers_progress_2026-09.json に書き出す。

対象は2000年以降の論文（先生に伝えた前提）。順位は src/build_matched_baseline.py の出力を使う。
スライドの生成（build_progress_2026-09.js）はこの JSON だけを読む。

実行: ~/.venvs/scisci-rir/bin/python docs/slides/make_numbers_progress_2026-09.py
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
DD = ROOT / "data" / "derived"
OUT = Path(__file__).with_name("numbers_progress_2026-09.json")
ORGS = ["豊田中央研究所", "トヨタ自動車未来創成センター", "AISIN IMRA(日本・aisin.com)", "AISIN IMRA(米国・imra.com)"]
METRICS = [("nov", "ss_novelty", True), ("conv", "ss_conventionality", False),
           ("dis", "ss_disruption", False), ("c10", "ss_c10", False)]
# 揃えた条件ごとの列の接尾辞
STAGES = {"fy": "", "ref": "_ref", "team": "_team", "both": "_ref_team"}
YEAR_FROM = 2000


def med(s: pd.Series, flip: bool = False) -> float:
    """順位の中央値。新規性は値が低いほど珍しいので、flip で「高いほど珍しい」に向きを揃える。"""
    v = float(s.dropna().median())
    return round(100 - v if flip else v, 1)


def main() -> None:
    site = pd.read_csv(DD / "openalex_linking" / "openalex_links.csv")
    ss = pd.read_csv(DD / "papers" / "sciscinet_metrics.csv")
    a = pd.read_csv(DD / "analysis" / "paper_analysis.csv")
    p = pd.read_csv(DD / "analysis" / "paper_percentiles.csv")
    smp = pd.read_csv(DD / "analysis" / "baseline_sample.csv")
    chk = pd.read_csv(DD / "novelty" / "sciscinet_check.csv")
    ana = json.loads((DD / "analysis" / "novelty_analysis.json").read_text())
    N: dict = {"year_from": YEAR_FROM}

    # ---- 材料: 組織ごとの件数（サイト掲載 → OpenAlex で特定 → 2000年以降で SciSciNet に値あり → 新規性あり）----
    ss_in = ss[ss["ss_year"].notna() & (ss["year_openalex"] >= YEAR_FROM)]
    org = []
    for o in ORGS:
        org.append({"org": o,
                    "site": int((site["source_org"] == o).sum()),
                    "matched": int(((site["source_org"] == o) & site["matched"]).sum()),
                    "ss": int((ss_in["source_org"] == o).sum()),
                    "nov": int(((ss_in["source_org"] == o) & ss_in["ss_novelty"].notna()).sum())})
    N["org"] = org
    N["tot"] = {k: sum(r[k] for r in org) for k in ("site", "matched", "ss", "nov")}

    # ---- ① 検算: 自前の計算と SciSciNet の公開値（両方に値がある論文）----
    ver = []
    for lab, own, pub in [("定石らしさ", "median_z", "ss_median_z"),
                          ("zスコアの下位10%", "p10_z", "ss_p10_z"),
                          ("雑誌の組の数", "n_pairs_with_z", "ss_pairs")]:
        x, y = chk[own], chk[pub]
        # 上下1%を除いた相関係数（極端に大きい値が少数あると、相関係数はそれに引っ張られる）
        keep = x.between(x.quantile(.01), x.quantile(.99)) & y.between(y.quantile(.01), y.quantile(.99))
        ver.append({"lab": lab, "sp": round(x.corr(y, method="spearman"), 2), "pe": round(x.corr(y), 2),
                    "pe_trim": round(x[keep].corr(y[keep]), 2),
                    "med_own": round(float(x.median()), 1), "med_ss": round(float(y.median()), 1)})
    N["ver"], N["ver_n"] = ver, int(len(chk))

    # ---- ② 世の中の論文との比較 ----
    d = p.merge(a[["paper_uid", "source_org", "ss_team_size", "referenced_works_count"]],
                on="paper_uid", how="left")
    d = d[d["year"] >= YEAR_FROM]
    cells = d[["field_id", "year"]].drop_duplicates()
    base = smp.merge(cells, on=["field_id", "year"])
    N["n_base"] = int(len(base))
    N["team_toyota"], N["team_base"] = float(d["ss_team_size"].median()), float(base["ss_team_size"].median())
    N["refs_toyota"], N["refs_base"] = float(d["referenced_works_count"].median()), float(base["n_refs"].median())
    N["stages"] = {st: {k: med(d[f"{m}_pct{suf}"], flip) for k, m, flip in METRICS} for st, suf in STAGES.items()}

    # チームの大きさ別の破壊性（Wu, Wang & Evans 2019 の「大きなチームは発展させ、小さなチームは壊す」の確認）
    bins = pd.cut(d["ss_team_size"], [0, 2, 4, 6, 1e9], labels=["1〜2人", "3〜4人", "5〜6人", "7人以上"])
    N["team_strata"] = [{"t": str(t), "n": int(g["ss_disruption_pct"].notna().sum()),
                         **{st: med(g[f"ss_disruption_pct{suf}"]) for st, suf in STAGES.items()}}
                        for t, g in d.groupby(bins, observed=True)]

    # 組織別（参考文献の数とチームの大きさの両方を揃えた順位）
    N["org_res"] = [{"org": o, "n": int(g["ss_novelty_pct"].notna().sum()),
                     **{k: med(g[f"{m}_pct_ref_team"], flip) for k, m, flip in METRICS}}
                    for o in ORGS for g in [d[d["source_org"] == o]]]

    # ---- ③ 仮説の検証（数値は src/analyze_novelty_v2.py の出力）----
    x = d.merge(a[["paper_uid", "is_international", "ref_field_hhi"]], on="paper_uid", how="left")
    x = x[x["ss_novelty_pct"].notna() & x["ss_team_size"].notna() & x["ref_field_hhi"].notna()]
    N["n_test"] = int(len(x))
    N["n_solo"] = int((x["ss_team_size"] == 1).sum())
    N["n_intl"] = int((x["is_international"] > 0).sum())
    N["ana"] = {k: ana[k] for k in ("h1_team", "h2_intl", "org_vs_interdisciplinarity",
                                    "org_effect_after_controls_p", "descriptive_only")}

    OUT.write_text(json.dumps(N, ensure_ascii=False, indent=1))
    print(json.dumps({k: v for k, v in N.items() if k not in ("ver",)}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
