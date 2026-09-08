"""計算した新規性の値を、論文の属性と突き合わせて集計する。

入力: data/derived/novelty/paper_novelty.csv   … 論文ごとの median_z / p10_z
      data/derived/papers/papers.csv
      data/derived/papers/authorships.csv
      data/derived/papers/authorship_affiliations.csv
出力: data/derived/novelty/analysis_summary.json … 下記すべての集計値
      data/derived/novelty/paper_novelty_joined.csv … 属性を付けた論文表

用語（このファイル内での呼び方）:
  median_z … 参考文献の掲載誌の組が、偶然に比べてどれくらいよく現れるかの中央値。
              大きいほど「定石どおり」。Uzzi の conventionality。
  p10_z   … 同じものの下から1割の値。小さいほど「めったにない組を含む」。
              Uzzi の novelty。

被引用数はそのまま比べられない（古い論文ほど貯まる）ので、
**同じ出版年の我々の論文の中での順位**に直してから比べる。

実行: ~/.venvs/scisci-rir/bin/python src/analyze_novelty.py
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

ROOT = Path(__file__).resolve().parent.parent
D = ROOT / "data" / "derived"
OUT_DIR = D / "novelty"


def load() -> pd.DataFrame:
    n = pd.read_csv(OUT_DIR / "paper_novelty.csv")
    p = pd.read_csv(D / "papers" / "papers.csv")
    a = pd.read_csv(D / "papers" / "authorships.csv")
    af = pd.read_csv(D / "papers" / "authorship_affiliations.csv")

    cols = ["paper_uid", "title_site", "source_org", "year_openalex", "cited_by_count",
            "n_authors", "institutions_distinct_count", "primary_field", "venue_openalex"]
    m = n.merge(p[cols], on="paper_uid", how="left")

    # 論文ごとの著者側の性質をまとめる
    g = af.groupby("paper_uid")
    per_paper = pd.DataFrame({
        "n_university": g["is_university"].sum(),
        "n_company": g["is_company"].sum(),
        "n_government": g["is_government"].sum(),
        "n_toyota_orgs": g["toyota_org"].nunique(),
        "n_authors_affil": g.size(),
    })
    # 産学連携: 同じ論文に大学所属の著者と企業所属の著者が両方いる
    per_paper["is_academia_industry"] = (
        (per_paper["n_university"] > 0) & (per_paper["n_company"] > 0))
    # 組織横断: トヨタ系の組織が2つ以上関わっている
    per_paper["is_cross_toyota_org"] = per_paper["n_toyota_orgs"] >= 2
    m = m.merge(per_paper, on="paper_uid", how="left")

    # 著者数は OpenAlex の値を使い、欠けていれば著者表の行数で補う
    n_rows = a.groupby("paper_uid").size().rename("n_authors_rows")
    m = m.merge(n_rows, on="paper_uid", how="left")
    m["team_size"] = m["n_authors"].fillna(m["n_authors_rows"])

    # 被引用数を同じ出版年の中での順位（0〜1）に直す
    m["cite_rank"] = m.groupby("year")["cited_by_count"].rank(pct=True)
    return m


def spearman(x: pd.Series, y: pd.Series) -> dict:
    """順位相関。外れ値の影響を受けにくいので、被引用数のような偏った分布に使う。"""
    d = pd.concat([x, y], axis=1).dropna()
    if len(d) < 10:
        return {"n": len(d), "rho": None, "p": None}
    r, pv = stats.spearmanr(d.iloc[:, 0], d.iloc[:, 1])
    return {"n": int(len(d)), "rho": round(float(r), 3), "p": round(float(pv), 5)}


def by_group(m: pd.DataFrame, col: str, min_n: int = 5) -> list[dict]:
    out = []
    for k, g in m.groupby(col):
        if len(g) < min_n:
            continue
        out.append({
            "group": str(k),
            "n": int(len(g)),
            "median_z_median": round(float(g["median_z"].median()), 2),
            "p10_z_median": round(float(g["p10_z"].median()), 2),
            "cited_median": float(g["cited_by_count"].median()),
        })
    return sorted(out, key=lambda d: -d["n"])


def partial_spearman(m: pd.DataFrame, x: str, y: str, z: str) -> dict:
    """z の影響を取り除いたうえでの x と y の順位相関。

    p10_z（下から1割の値）は、参考文献の組が多い論文ほど自然に極端になる。
    その効果を取り除かないと「参考文献が多い論文はよく引用される」という
    別の関係を新規性の効果と取り違える。
    """
    d = m[[x, y, z]].dropna()
    rx, ry, rz = (stats.rankdata(d[c]) for c in (x, y, z))
    ex = rx - np.poly1d(np.polyfit(rz, rx, 1))(rz)
    ey = ry - np.poly1d(np.polyfit(rz, ry, 1))(rz)
    r, pv = stats.pearsonr(ex, ey)
    return {"n": int(len(d)), "rho": round(float(r), 3), "p": round(float(pv), 5)}


def by_pairs_quartile(m: pd.DataFrame) -> list[dict]:
    """参考文献の組の数を揃えたうえで、新規性と被引用の関係を見る。"""
    d = m.dropna(subset=["n_pairs", "p10_z", "cite_rank"]).copy()
    d["q"] = pd.qcut(d["n_pairs"], 4, labels=["少", "やや少", "やや多", "多"])
    out = []
    for k, g in d.groupby("q", observed=True):
        r, pv = stats.spearmanr(g["p10_z"], g["cite_rank"])
        out.append({"group": str(k), "n": int(len(g)),
                    "n_pairs_median": float(g["n_pairs"].median()),
                    "rho": round(float(r), 3), "p": round(float(pv), 4)})
    return out


def uzzi_2x2(m: pd.DataFrame) -> dict:
    """Uzzi の中心的な主張を手元のデータで確かめる。

    「定石どおりの土台の上に、一部だけ珍しい組み合わせを混ぜた論文が最もよく引用される」。
    median_z（定石らしさ）と p10_z（踏み外しの強さ）をそれぞれ中央値で二分し、
    4つの組に分けて被引用の順位を比べる。
    """
    d = m.dropna(subset=["median_z", "p10_z", "cite_rank"]).copy()
    hi_conv = d["median_z"] >= d["median_z"].median()
    # p10_z が小さいほど踏み外しが強い
    hi_nov = d["p10_z"] <= d["p10_z"].median()
    d["cell"] = np.where(hi_conv & hi_nov, "定石高×踏み外し高",
                np.where(hi_conv & ~hi_nov, "定石高×踏み外し低",
                np.where(~hi_conv & hi_nov, "定石低×踏み外し高", "定石低×踏み外し低")))
    res = {}
    for k, g in d.groupby("cell"):
        res[k] = {
            "n": int(len(g)),
            "cite_rank_median": round(float(g["cite_rank"].median()), 3),
            "cited_median": float(g["cited_by_count"].median()),
            "top10pct_share": round(float((g["cite_rank"] >= 0.9).mean()), 3),
        }
    return res


def main() -> None:
    m = load()
    m.to_csv(OUT_DIR / "paper_novelty_joined.csv", index=False)

    s: dict = {}
    s["n_papers"] = int(len(m))
    s["years"] = [int(m["year"].min()), int(m["year"].max())]
    s["distribution"] = {
        c: {q: round(float(m[c].quantile(v)), 2)
            for q, v in [("p10", .1), ("q1", .25), ("median", .5), ("q3", .75), ("p90", .9)]}
        for c in ["median_z", "p10_z", "n_pairs"]
    }

    # ---- 新規性と被引用の関係 ----
    s["correlation_with_citation"] = {
        "median_z_vs_cite_rank": spearman(m["median_z"], m["cite_rank"]),
        "p10_z_vs_cite_rank": spearman(m["p10_z"], m["cite_rank"]),
    }
    s["uzzi_2x2"] = uzzi_2x2(m)
    # 参考文献の組の数が交絡していないかを確かめる
    s["confound_check"] = {
        "n_pairs_vs_cite_rank": spearman(m["n_pairs"], m["cite_rank"]),
        "p10_z_vs_cite_rank_controlled": partial_spearman(m, "p10_z", "cite_rank", "n_pairs"),
        "median_z_vs_cite_rank_controlled": partial_spearman(m, "median_z", "cite_rank", "n_pairs"),
        "by_pairs_quartile": by_pairs_quartile(m),
    }

    # ---- 説明変数との関係 ----
    s["correlation_with_conditions"] = {
        "team_size_vs_median_z": spearman(m["team_size"], m["median_z"]),
        "team_size_vs_p10_z": spearman(m["team_size"], m["p10_z"]),
        "institutions_vs_median_z": spearman(m["institutions_distinct_count"], m["median_z"]),
        "institutions_vs_p10_z": spearman(m["institutions_distinct_count"], m["p10_z"]),
        "n_pairs_vs_p10_z": spearman(m["n_pairs"], m["p10_z"]),
    }

    def two_group(flag: str) -> dict:
        d = m.dropna(subset=[flag])
        out = {}
        for k, g in d.groupby(flag):
            out["あり" if k else "なし"] = {
                "n": int(len(g)),
                "median_z_median": round(float(g["median_z"].median()), 2),
                "p10_z_median": round(float(g["p10_z"].median()), 2),
                "cite_rank_median": round(float(g["cite_rank"].median()), 3),
            }
        a = d[d[flag]]["p10_z"].dropna()
        b = d[~d[flag]]["p10_z"].dropna()
        if len(a) >= 5 and len(b) >= 5:
            u, pv = stats.mannwhitneyu(a, b)
            out["p10_z の差の検定"] = {"p": round(float(pv), 5)}
        return out

    s["academia_industry"] = two_group("is_academia_industry")
    s["cross_toyota_org"] = two_group("is_cross_toyota_org")

    s["by_source_org"] = by_group(m, "source_org")
    s["by_field"] = by_group(m, "primary_field", min_n=10)
    s["by_year"] = by_group(m, "year", min_n=10)

    # ---- 極端な論文 ----
    def pick(df, cols):
        return df[cols].round(2).to_dict("records")

    cols = ["year", "source_org", "median_z", "p10_z", "cited_by_count", "title_site"]
    s["most_novel"] = pick(m.nsmallest(10, "p10_z"), cols)
    s["most_conventional"] = pick(m.nlargest(10, "median_z"), cols)

    (OUT_DIR / "analysis_summary.json").write_text(
        json.dumps(s, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print(json.dumps({k: v for k, v in s.items()
                      if k not in ("most_novel", "most_conventional", "by_field", "by_year")},
                     ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()
