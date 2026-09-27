"""トヨタ論文の新規性を、条件を揃えた順位のうえで分析する（段階3-6 のやり直し）。

2026-09-08 の最初の分析は設計が不適切だったので作り直す。何が不適切だったか。

  - 被引用との相関で指標を検証しようとした。段階2の文献調査で、この関係は直線ではなく
    山なりである可能性が報告されており（Yan et al. 2019、Deng et al. 2023）、
    **被引用で新規性指標を検証してはいけない**と結論している
  - 説明変数4系統に文献の裏づけがなかった。段階2で仮説はチーム規模と国際共同の2つに絞り、
    参考文献数と学際性を統制項、産学連携・組織横断・キャリア段階は記述のみと決め直した

本スクリプトの方針。

  - 成果変数は**分野×年で揃えた順位**を使う。分野と年の効果を非母数的に除いてある
  - 仮説を立てるのはチーム規模と国際共同の2つだけ。これらは**揃えていない順位**を使う
    （チーム規模を揃えた順位を使うとチーム規模の効果自体が消えてしまう）
  - 参考文献数と学際性は必ず統制項に入れる
  - 被引用との関係は「検証」ではなく「結果」として、階級に分けて報告する
  - 産学連携・組織横断は値を出すが仮説を立てない

**新規性の向きに注意。** SciSciNet の `Atyp_10pct_Z` は値が低いほど珍しい組み合わせを含む。
読み違えを防ぐため、本スクリプトでは符号を反転した `atypicality` を作り、
**高いほど非慣習的**に統一する。

入力: data/derived/analysis/paper_analysis.csv, paper_percentiles.csv
出力: data/derived/analysis/novelty_analysis.json

実行: ~/.venvs/scisci-rir/bin/python src/analyze_novelty_v2.py
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
from scipy import stats

ROOT = Path(__file__).resolve().parent.parent
D = ROOT / "data" / "derived" / "analysis"
OUT_JSON = D / "novelty_analysis.json"


def main() -> int:
    a = pd.read_csv(D / "paper_analysis.csv")
    p = pd.read_csv(D / "paper_percentiles.csv")
    df = p.merge(a, on="paper_uid", how="left", suffixes=("", "_a"))
    # 対象は2000年以降（2026-09-08 に先生へ伝えた前提）。1990年代以前は参考文献の登録が薄い。
    # 2026-09-14 の版はこの絞り込みが抜けており、AISIN IMRA 米国の1988〜1999年の47件が入っていた
    df = df[df["year"] >= 2000].copy()

    # 符号を反転して「高いほど非慣習的」に統一する
    df["atypicality"] = 100 - df["ss_novelty_pct"]
    df["atypicality_ref"] = 100 - df["ss_novelty_pct_ref"]
    df["conventionality"] = df["ss_conventionality_pct"]
    df["disruption"] = df["ss_disruption_pct_ref_team"]
    df["citation"] = df["ss_c10_pct_ref_team"]
    df["team"] = df["ss_team_size"]
    df["n_refs"] = df["referenced_works_count"]
    df["intl"] = df["is_international"].astype(float)
    df["hhi"] = df["ref_field_hhi"]          # 高いほど単一分野（学際性の逆）
    df["ia"] = df["is_industry_academia_oa"].astype(float)
    df["cross"] = df["is_cross_org"].astype(float)

    out: dict = {"n_total": int(len(df))}

    # ---- 1. 記述 ----
    desc = df.groupby("source_org").agg(
        n=("paper_uid", "size"),
        atypicality=("atypicality", "median"),
        conventionality=("conventionality", "median"),
        disruption=("disruption", "median"),
        citation=("citation", "median"),
        team=("team", "median"),
        n_refs=("n_refs", "median"),
        hhi=("hhi", "median")).round(2)
    out["by_org"] = json.loads(desc.to_json(orient="index"))
    print("=== 組織別（順位の中央値。atypicality は高いほど非慣習的）===")
    print(desc.to_string())

    # ---- 2. 仮説1: チーム規模 ----
    d1 = df.dropna(subset=["atypicality", "team", "n_refs", "hhi"]).copy()
    d1["log_team"] = np.log(d1["team"].clip(lower=1))
    m1 = smf.ols("atypicality ~ log_team + np.log(n_refs+1) + hhi", data=d1).fit()
    out["h1_team"] = {"n": int(m1.nobs), "coef": round(float(m1.params["log_team"]), 2),
                      "p": round(float(m1.pvalues["log_team"]), 4),
                      "r2": round(float(m1.rsquared), 3)}
    print(f"\n=== 仮説1: チーム規模 → 非慣習性 （n={int(m1.nobs)}）===")
    print(f"  log(チーム規模) の係数 {m1.params['log_team']:+.2f}  p={m1.pvalues['log_team']:.4f}")
    print(f"  参考文献数と学際性を統制済み。決定係数 {m1.rsquared:.3f}")

    # ---- 3. 仮説2: 国際共同 ----
    d2 = df.dropna(subset=["atypicality", "intl", "n_refs", "hhi", "team"]).copy()
    m2 = smf.ols("atypicality ~ intl + np.log(team.clip(lower=1)) + np.log(n_refs+1) + hhi",
                 data=d2).fit()
    out["h2_intl"] = {"n": int(m2.nobs), "coef": round(float(m2.params["intl"]), 2),
                      "p": round(float(m2.pvalues["intl"]), 4)}
    g = d2.groupby(d2["intl"] > 0)["atypicality"].median()
    print(f"\n=== 仮説2: 国際共同 → 非慣習性 （n={int(m2.nobs)}）===")
    print(f"  係数 {m2.params['intl']:+.2f}  p={m2.pvalues['intl']:.4f}")
    print(f"  中央値: 国内のみ {g.get(False, float('nan')):.1f} / 国際共同 {g.get(True, float('nan')):.1f}")

    # ---- 4. 学際性との切り分け（Fontana 2020 の指摘）----
    d3 = df.dropna(subset=["atypicality", "hhi", "source_org"]).copy()
    m3a = smf.ols("atypicality ~ C(source_org)", data=d3).fit()
    m3b = smf.ols("atypicality ~ C(source_org) + hhi + np.log(n_refs+1)", data=d3).fit()
    out["org_vs_interdisciplinarity"] = {
        "n": int(m3a.nobs),
        "r2_org_only": round(float(m3a.rsquared), 3),
        "r2_with_controls": round(float(m3b.rsquared), 3),
        "f_org_only_p": round(float(m3a.f_pvalue), 6),
        "f_with_controls_p": round(float(m3b.f_pvalue), 6)}
    print(f"\n=== 組織差は学際性で説明できるか （n={int(m3a.nobs)}）===")
    print(f"  組織だけ            決定係数 {m3a.rsquared:.3f}")
    print(f"  ＋学際性・参考文献数  決定係数 {m3b.rsquared:.3f}")
    # 組織の効果が統制後も残るか（F検定）
    from statsmodels.stats.anova import anova_lm
    m3c = smf.ols("atypicality ~ hhi + np.log(n_refs+1)", data=d3).fit()
    an = anova_lm(m3c, m3b)
    pval = float(an["Pr(>F)"].iloc[1])
    out["org_effect_after_controls_p"] = round(pval, 6)
    print(f"  統制後も組織差が残るか: p={pval:.5f}  → {'残る' if pval < 0.05 else '残らない'}")

    # ---- 5. 被引用との関係（検証ではなく結果として、階級で報告）----
    d4 = df.dropna(subset=["atypicality", "citation"]).copy()
    d4["q"] = pd.qcut(d4["atypicality"], 5, labels=["最も慣習的", "やや慣習的", "中間", "やや非慣習的", "最も非慣習的"])
    tab = d4.groupby("q", observed=True).agg(n=("paper_uid", "size"),
                                             citation=("citation", "median")).round(1)
    out["citation_by_atypicality_quintile"] = json.loads(tab.to_json(orient="index"))
    print("\n=== 非慣習性の五分位ごとの被引用順位（結果であって検証ではない）===")
    print(tab.to_string())
    rho, pv = stats.spearmanr(d4["atypicality"], d4["citation"])
    out["citation_spearman"] = {"rho": round(float(rho), 3), "p": round(float(pv), 4)}
    print(f"  参考までに順位相関 {rho:+.3f} (p={pv:.4f})。ただし関係が直線とは限らない")

    # ---- 6. 仮説を立てない変数（記述のみ）----
    print("\n=== 仮説を立てない変数（記述のみ。文献の裏づけがない）===")
    desc2 = {}
    for col, lab in [("ia", "産学連携"), ("cross", "組織横断")]:
        d5 = df.dropna(subset=["atypicality", col])
        gg = d5.groupby(d5[col] > 0)["atypicality"].agg(["size", "median"]).round(1)
        u = stats.mannwhitneyu(d5[d5[col] > 0]["atypicality"], d5[d5[col] == 0]["atypicality"])
        desc2[lab] = {"n_true": int(gg.loc[True, "size"]) if True in gg.index else 0,
                      "median_true": float(gg.loc[True, "median"]) if True in gg.index else None,
                      "median_false": float(gg.loc[False, "median"]) if False in gg.index else None,
                      "p": round(float(u.pvalue), 4)}
        print(f"  {lab}: あり {desc2[lab]['n_true']}件 中央値 {desc2[lab]['median_true']} / "
              f"なし 中央値 {desc2[lab]['median_false']}  p={desc2[lab]['p']}")
    out["descriptive_only"] = desc2

    OUT_JSON.write_text(json.dumps(out, ensure_ascii=False, indent=2))
    print(f"\n出力: {OUT_JSON.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
