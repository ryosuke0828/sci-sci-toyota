"""発表資料 p.5 の散布図（自前計算と SciSciNet 公開値の比較）を作る。

zスコアは数千に達する論文があり、そのままでは点が一か所に潰れる。
符号を保ったまま対数的に縮める symlog 目盛りを使う（0付近の ±10 は線形）。
"""
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
m = pd.read_csv(ROOT / "data/derived/novelty/sciscinet_check.csv")
plt.rcParams.update({"font.family": "Hiragino Sans", "font.size": 11})

fig, axes = plt.subplots(1, 2, figsize=(9.0, 3.9), dpi=200)
panels = [("median_z", "ss_median_z", "定石らしさ（zスコアの中央値）"),
          ("p10_z", "ss_p10_z", "zスコアの下位10%（低いほど珍しい組み合わせ）")]
for ax, (a, b, title) in zip(axes, panels):
    x, y = m[a], m[b]
    ax.scatter(x, y, s=9, color="#333333", alpha=0.6, linewidths=0)
    ax.set_xscale("symlog", linthresh=10); ax.set_yscale("symlog", linthresh=10)
    lo = min(x.min(), y.min()) * 1.3; hi = max(x.max(), y.max()) * 1.3
    ax.plot([lo, hi], [lo, hi], color="#999999", lw=0.8, ls="--")  # 同じ値になる線
    ax.set_xlim(lo, hi); ax.set_ylim(lo, hi)
    ax.set_title(title, fontsize=12)
    ax.set_xlabel("自前計算"); ax.set_ylabel("SciSciNet 公開値")
    rho = x.corr(y, method="spearman")
    ax.text(0.03, 0.97, f"n = {len(m)}\n順位相関 {rho:.2f}", transform=ax.transAxes,
            va="top", ha="left", fontsize=10)
    ax.grid(color="#e5e5e5", lw=0.5); ax.set_axisbelow(True)
    for s in ("top", "right"): ax.spines[s].set_visible(False)
fig.tight_layout()
out = Path(__file__).with_name("fig_verification_scatter.png")
fig.savefig(out, facecolor="white")
print(out)
