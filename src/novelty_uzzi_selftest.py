"""novelty_uzzi.py の計数とシャッフルが正しいかを、合成データで確かめる。

疎行列の転置積に置き換えた際（2026-09-07）、置き換え前の DuckDB 自己結合と
同じ数を返すことを担保するために書いた。スナップショットが無くても走る。

  検査1 … cooccurrence() の値が、SQL で素直に書いた計数と完全一致する
  検査2 … shuffle_strata() が Uzzi の次数保存条件を満たす
           （論文ごとの被引用年別の参照本数、ジャーナル年ごとの被引用数）
  検査3 … 出現回数で数え、同一誌どうしの対も正しく作る（2026-09-10 の仕様変更）

2026-09-10: SciSciNet に合わせて計数を「共起した論文数」から「参照の全ペアの出現回数」に
変えたので、検査1の参照実装と検査3の期待値を書き換えた。

実行: ~/.venvs/scisci-rir/bin/python src/novelty_uzzi_selftest.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from novelty_uzzi import cooccurrence, shuffle_strata  # noqa: E402


def make_edges(rng: np.random.Generator, n_src=4000, n_j_all=300, n_j_target=60, n_edges=120_000):
    """論文 → ジャーナル(被引用年つき) のエッジを乱数で作る。

    対象ジャーナルは全体の一部だけにして、対象外(-1)が混ざる状況を再現する。
    """
    si = rng.integers(0, n_src, n_edges).astype(np.int32)
    j = rng.integers(0, n_j_all, n_edges).astype(np.int32)
    cy = rng.integers(1990, 2020, n_edges).astype(np.int32)
    # 先頭 n_j_target 誌だけを対象にする
    ji = np.where(j < n_j_target, j, -1).astype(np.int32)
    order = np.argsort(cy, kind="stable")
    return si[order], j[order], ji[order], cy[order], n_src, n_j_target


def sql_counts(con, si, ji, n_j) -> np.ndarray:
    """SciSciNet の数え方を SQL で素直に書いたもの（参照実装）。

    非対角は Σ_p c_A(p)·c_B(p)、対角は Σ_p C(c_A(p), 2)。
    疎行列版と独立に書くことで、行列演算の取り違えを検出する。
    """
    con.register("e_df", pd.DataFrame({"src": si, "j": ji}))
    con.execute("CREATE OR REPLACE TABLE e AS SELECT * FROM e_df WHERE j >= 0")
    df = con.execute("""
        WITH c AS (SELECT src, j, count(*) AS cnt FROM e GROUP BY src, j)
        SELECT a.j AS j1, b.j AS j2, sum(a.cnt * b.cnt)::BIGINT AS n
        FROM c a JOIN c b ON b.src = a.src AND a.j < b.j
        GROUP BY 1, 2
        UNION ALL
        SELECT j, j, sum(cnt * (cnt - 1) / 2)::BIGINT FROM c GROUP BY j
    """).df()
    C = np.zeros((n_j, n_j), dtype=np.int64)
    C[df["j1"].values, df["j2"].values] = df["n"].values
    return C


def main() -> int:
    rng = np.random.default_rng(1234)
    con = duckdb.connect()
    ok = True

    # ---- 検査1: 計数が自己結合と一致するか
    si, j, ji, cy, n_src, n_j = make_edges(rng)
    C_sparse = np.triu(cooccurrence(si, ji, n_src, n_j), k=0)  # 対角も比べる
    C_sql = sql_counts(con, si, ji, n_j)
    same = np.array_equal(C_sparse, C_sql)
    print(f"検査1 計数の一致: {'OK' if same else 'NG'} "
          f"（非零 {int((C_sql > 0).sum()):,} 対、最大 {int(C_sql.max())}）")
    ok &= same

    # ---- 検査2: シャッフルが次数を保存するか
    bounds = np.concatenate(([0], np.flatnonzero(np.diff(cy)) + 1, [cy.size]))
    js = shuffle_strata(ji, bounds, rng)
    # 論文ごとの被引用年別の本数は、src 列と cy 列を動かさないことで保たれる。
    # 入力配列が書き換わっていないことを確かめる（in-place シャッフルの誤りを検出する）
    si_before, cy_before, ji_before = si.copy(), cy.copy(), ji.copy()
    _ = shuffle_strata(ji, bounds, rng)
    deg_ok = (np.array_equal(si, si_before) and np.array_equal(cy, cy_before)
              and np.array_equal(ji, ji_before))
    # ジャーナル年ごとの本数（対象外の -1 もひとつの類として数える）。
    # 層をまたいで入れ替えてしまうとここで落ちる
    c1 = pd.DataFrame({"j": ji, "cy": cy}).value_counts().sort_index()
    c2 = pd.DataFrame({"j": js, "cy": cy}).value_counts().sort_index()
    jy_ok = c1.equals(c2)
    moved = int((js != ji).sum())
    print(f"検査2 次数保存: 入力の非破壊 {'OK' if deg_ok else 'NG'} / "
          f"誌×年 {'OK' if jy_ok else 'NG'}（実際に動いたエッジ {moved:,}/{ji.size:,}）")
    ok &= deg_ok and jy_ok

    # ---- 検査3: 出現回数の数え方と、同一誌どうしの対
    # 論文0 … 誌0を2本・誌1を1本、論文1 … 誌0を1本・誌1を1本
    si2 = np.array([0, 0, 0, 1, 1], dtype=np.int32)
    ji2 = np.array([0, 0, 1, 0, 1], dtype=np.int32)
    C = cooccurrence(si2, ji2, 2, 2)
    # 対(0,1) = 2×1 + 1×1 = 3
    # 対(0,0) = C(2,2) + C(1,2) = 1 + 0 = 1
    # 対(1,1) = 0 + 0 = 0
    exp = {"(0,1)": (int(C[0, 1]), 3), "(0,0)": (int(C[0, 0]), 1), "(1,1)": (int(C[1, 1]), 0)}
    dup_ok = all(a == b for a, b in exp.values())
    detail = " ".join(f"{k}={a}(期待{b})" for k, (a, b) in exp.items())
    print(f"検査3 出現回数と同一誌の対: {'OK' if dup_ok else 'NG'}  {detail}")
    ok &= dup_ok

    print("\n結果:", "すべて一致" if ok else "不一致あり")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
