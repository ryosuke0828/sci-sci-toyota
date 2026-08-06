"""パイロット結果の判定を、同姓同名リスクを考慮して作り直す。

初版の判定（pilot_scopus_wos_verification.py）は
`AU="姓, 名" AND OG=Toyota` がヒットしたら所属の証拠とみなしていたが、
この複合クエリは「同姓同名の別人がトヨタと共著していた」場合にもヒットする。
実際、WoSのみを根拠に confirmed とした著者は名前のみヒット数の中央値が862件
（両DB一致した著者は10件）で、ほぼ確実に同姓同名の混入である。

そこで「名前のみヒット数」を同姓同名リスクの代理指標として使い、
証拠の強さで判定を作り直す。

実行: ~/.venvs/scisci-rir/bin/python src/pilot_revise_verdicts.py
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DIR = ROOT / "data" / "derived" / "pilot_scopus_wos"

# 名前のみヒットがこれを超えたら「よくある名前」とみなし、WoS単独の証拠は採用しない。
# 両DB一致群の75%点(≒30件)と、WoS単独根拠群の中央値(862件)の間に置いた。
COMMON_NAME_THRESHOLD = 50


def revise(r: pd.Series) -> str:
    scopus_yes = bool(r["scopus_toyota_hit"])
    wos_motor = r["wos_hits_toyota_motor"] or 0
    wos_group = r["wos_hits_toyota_group"] or 0
    name_only = r["wos_hits_name_only"] or 0
    common = name_only > COMMON_NAME_THRESHOLD

    if scopus_yes and wos_motor > 0:
        # Scopusは候補著者単位で現所属を返すので人物特定性が高い。両DB一致は最も強い
        return "strong_support"
    if scopus_yes:
        return "scopus_support"
    if wos_motor > 0 and not common:
        return "wos_support"
    if wos_motor > 0 and common:
        # 同姓同名の別人がトヨタと共著しているだけの可能性が高い。証拠として採用しない
        return "ambiguous_common_name"
    if wos_group > 0 and not common:
        return "group_support"
    if r["n_scopus_candidates"] > 0 and not scopus_yes:
        return "contradicted"
    return "no_evidence"


def main() -> None:
    v = pd.read_csv(DIR / "verdicts.csv")
    v["revised_verdict"] = v.apply(revise, axis=1)
    v["common_name_flag"] = (v["wos_hits_name_only"].fillna(0) > COMMON_NAME_THRESHOLD)
    v.to_csv(DIR / "verdicts_revised.csv", index=False)

    cross = pd.crosstab(v["sample_group"], v["revised_verdict"])
    print("===== 層 × 改訂判定 =====")
    print(cross.to_string())

    # OpenAlex が「現所属」と主張する層について、裏付けが取れた割合
    supportive = {"strong_support", "scopus_support", "wos_support"}
    v["is_supported"] = v["revised_verdict"].isin(supportive)
    print("\n===== OpenAlexの主張の裏付け率 =====")
    rate = v.groupby("sample_group")["is_supported"].agg(["size", "sum", "mean"])
    rate["pct"] = (rate["mean"] * 100).round(1)
    print(rate[["size", "sum", "pct"]].to_string())

    print("\n===== 同姓同名フラグ率（層別）=====")
    print((v.groupby("sample_group")["common_name_flag"].mean() * 100).round(1).to_string())

    # 初版の判定がなぜ誤っていたかを数字で残す
    c1 = v[v["verdict"] == "confirmed_one"]
    wos_only = c1[(c1["scopus_toyota_hit"] == False) &  # noqa: E712
                  (c1["wos_hits_toyota_motor"].fillna(0) > 0)]
    both = v[v["verdict"] == "confirmed_both"]
    evidence = {
        "wos_only_confirmed_n": int(len(wos_only)),
        "wos_only_median_name_only_hits": float(wos_only["wos_hits_name_only"].median())
        if len(wos_only) else None,
        "both_db_confirmed_n": int(len(both)),
        "both_db_median_name_only_hits": float(both["wos_hits_name_only"].median())
        if len(both) else None,
    }
    print("\n===== 初版判定が誤っていた根拠 =====")
    print(json.dumps(evidence, ensure_ascii=False, indent=2))

    summary = {
        "common_name_threshold": COMMON_NAME_THRESHOLD,
        "revised_verdict_counts": v["revised_verdict"].value_counts().to_dict(),
        "revised_by_group": json.loads(cross.to_json(orient="index")),
        "support_rate_pct_by_group": {k: float(x) for k, x in (rate["pct"]).items()},
        "common_name_pct_by_group": {
            k: round(float(x) * 100, 1)
            for k, x in v.groupby("sample_group")["common_name_flag"].mean().items()},
        "why_initial_verdict_was_wrong": evidence,
    }
    (DIR / "revised_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n出力: {DIR / 'verdicts_revised.csv'}\n      {DIR / 'revised_summary.json'}")


if __name__ == "__main__":
    main()
