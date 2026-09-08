"""段階2-2の前処理: 収集した候補文献のタイトルと掲載誌名を OpenAlex API で補う。

works_slim には容量の都合でタイトルを入れていないので、スクリーニングに必要な分だけ引く。
既存の `src/build_reference_titles.py` と同じキャッシュを共有するので、
参考文献テーブルで取得済みのものは再問い合わせしない。

既定では被参照シード数が2以上の候補（この分野の中心にあるもの）に絞る。
1シードだけの候補4,264件まで引くと無料枠を圧迫するため、必要になってから広げる。

入力: data/derived/literature/candidates.csv
出力: data/derived/literature/candidates_titled.csv
      data/cache/openalex_title_cache.json（build_reference_titles.py と共有）

実行: ~/.venvs/scisci-rir/bin/python src/literature_titles.py [最小シード数]
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_reference_titles import (  # noqa: E402
    QuotaExhausted, fetch_titles, load_cache, save_cache)

ROOT = Path(__file__).resolve().parent.parent
IN_CAND = ROOT / "data" / "derived" / "literature" / "candidates.csv"
OUT = ROOT / "data" / "derived" / "literature" / "candidates_titled.csv"
MIN_SEEDS = int(sys.argv[1]) if len(sys.argv) > 1 else 2


def main() -> int:
    c = pd.read_csv(IN_CAND)
    sel = c[c["n_seeds"] >= MIN_SEEDS].copy()
    print(f"候補 {len(c):,} 件のうち、被参照シード数 {MIN_SEEDS} 以上は {len(sel):,} 件", flush=True)

    ids = sorted(set(int(x) for x in sel["cand"].dropna()))
    cache = load_cache()
    try:
        fetch_titles(ids, cache)
    except QuotaExhausted as e:
        # 途中まででも保存し、翌日そのまま再実行すれば続きから進む
        print(f"クォータ切れ: {e}", flush=True)
        save_cache(cache)

    sel["title"] = sel["cand"].map(lambda i: cache.get(str(int(i))))
    got = sel["title"].notna().sum()
    print(f"タイトルが付いたもの {got:,}/{len(sel):,}（{got/len(sel)*100:.1f}%）", flush=True)

    sel = sel.sort_values(["n_seeds", "cited_by_count"], ascending=False)
    sel.to_csv(OUT, index=False)
    print(f"出力: {OUT}", flush=True)

    print("\n===== 被参照シード数の多い上位30件 =====", flush=True)
    cols = ["n_seeds", "n_back", "n_fwd", "publication_year", "cited_by_count", "title"]
    print(sel[cols].head(30).to_string(index=False, max_colwidth=80), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
