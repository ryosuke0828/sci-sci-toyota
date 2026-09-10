"""Uzzi et al. (2013) の atypicality（novelty / conventionality）を計算する。

手順は SciSciNet（Sci Data 2023）の記述に合わせた。

  1. 出版年 Y ごとにコーパスを作る（その年に出た article）。
  2. 各論文の参考文献が載っているジャーナルの組み合わせを列挙し、出現回数を数える（観測値）。
  3. 引用ネットワークをランダム化して同じ集計を10回行い、各ジャーナル対の期待値と標準偏差を得る。
     ランダム化は「被引用年」を層として引用先を入れ替える。これで各論文が各年から引く本数と、
     各ジャーナル年の被引用数が保存される（Uzzi の条件）。
  4. z = (観測 - 平均) / 標準偏差。論文ごとに z の中央値（conventionality）と
     10パーセンタイル（novelty）を取る。

**シャッフルは全参照ネットワーク上で行う**。当初、対象ジャーナルに絞ってからシャッフルしていたが、
それでは絞り込みの外にある参照が入れ替えの対象から外れ、Uzzi の次数保存の条件を満たさない。
絞り込みは数える段階だけに適用する（数える側を絞っても対象ペアの計数は変わらない）。

## 数え方: SQL の自己結合ではなく疎行列の転置積

「j1 と j2 の両方を引いている論文の数」は、論文×ジャーナルの二値疎行列 M に対する
Mᵀ M の要素そのものである。当初 DuckDB の自己結合で数えていたが、1億エッジで
1回あたり約400秒かかり（並列が効かず CPU 使用率47%で頭打ち）、26年×11回では実用にならなかった。

  M … 行 = コーパスの論文、列 = 対象ジャーナル（その年に我々の論文が作る対に現れる誌のみ）
  C = Mᵀ M … 上三角が全ジャーナル対の共起論文数。対象誌は高々数千なので密行列で持てる

シャッフルも numpy で行う。エッジを被引用年 cy で整列しておけば、層ごとの入れ替えは
連続スライスの in-place シャッフルで済む。

実測（2020年、コーパス325万論文・参照エッジ1億581万本、M2 Pro 10コア）:
  → 下部の run_year() が各段階の秒数を出力する。

入力: data/derived/papers/papers.csv
      ~/scisci-data/works_slim/*.parquet
出力: data/derived/novelty/paper_novelty.csv     … 論文ごとの median z と 10パーセンタイル z
      data/derived/novelty/pair_zscores_{year}.parquet … ジャーナル対ごとの z（検算用）

実行: ~/.venvs/scisci-rir/bin/python src/novelty_uzzi.py [年 ...]
      年を指定しなければ、対象論文が存在する年をすべて処理する。

環境変数:
  SCISCI_N_RAND     ランダム化の回数（既定 10）
  SCISCI_SEED       乱数シード（既定 20260907）
  SCISCI_SLIM_GLOB  works_slim の場所
  SCISCI_NOVELTY_DB 作業用 DuckDB ファイルの場所
  SCISCI_NOVELTY_OUT 出力先（試走で本番の出力を上書きしないため）
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd
import scipy.sparse as sp

ROOT = Path(__file__).resolve().parent.parent
IN_PAPERS = ROOT / "data" / "derived" / "papers" / "papers.csv"
SLIM_GLOB = os.environ.get(
    "SCISCI_SLIM_GLOB", str(Path.home() / "scisci-data" / "works_slim" / "*.parquet"))
DB_PATH = os.environ.get("SCISCI_NOVELTY_DB", str(Path.home() / "scisci-data" / "novelty.duckdb"))
OUT_DIR = Path(os.environ.get("SCISCI_NOVELTY_OUT", ROOT / "data" / "derived" / "novelty"))
N_RAND = int(os.environ.get("SCISCI_N_RAND", "10"))
SEED = int(os.environ.get("SCISCI_SEED", "20260907"))
MIN_YEAR = 2000


def load_our_papers() -> pd.DataFrame:
    p = pd.read_csv(IN_PAPERS)
    p = p[(p["work_id"].notna()) & (p["is_work_primary"])].copy()
    p["wid"] = p["work_id"].str.extract(r"W(\d+)").astype("Int64")
    p = p[p["year_openalex"] >= MIN_YEAR]
    # SciSciNet は焦点論文を DocType == 'Journal' に限る。合わせて雑誌論文だけにする。
    # 会議論文182件などが外れる（2026-09-10 の判断。組織ごとに落ち方が偏る点は報告書に記載）
    n_before = len(p)
    p = p[p["type"] == "article"]
    print(f"焦点論文: {len(p)} 件（type='article' 以外の {n_before - len(p)} 件を除外）", flush=True)
    return p[["paper_uid", "wid", "year_openalex"]]


def build_work_meta(con: duckdb.DuckDBPyConnection) -> None:
    """work_id → (ジャーナル, 出版年) の索引表を作る。

    年ごとに 510M行の parquet を舐め直すと参照先の解決が重い。ジャーナルと年が
    分かっている works だけを一度だけ落としておき、以後はこの表に結合する。
    一度作れば DB に残るので、次回以降は再作成しない。
    """
    exists = con.execute(
        "SELECT count(*) FROM duckdb_tables() WHERE table_name='work_meta'").fetchone()[0]
    if exists:
        n = con.execute("SELECT count(*) FROM work_meta").fetchone()[0]
        print(f"work_meta は作成済み（{n:,} 行）", flush=True)
        return
    t = time.time()
    con.execute(f"""
        CREATE TABLE work_meta AS
        SELECT work_id, source_id, publication_year AS cy
        FROM read_parquet('{SLIM_GLOB}')
        WHERE source_id IS NOT NULL AND publication_year IS NOT NULL
    """)
    n = con.execute("SELECT count(*) FROM work_meta").fetchone()[0]
    print(f"work_meta を構築: {n:,} 行  [{time.time()-t:.0f}秒]", flush=True)


def setup(con: duckdb.DuckDBPyConnection, ours: pd.DataFrame) -> None:
    """我々の論文の参考文献を誌ごとに数え、そこからジャーナル対の集合を作る。

    本数を保つ必要がある。同一誌どうしの対(A,A)は「誌Aを2本以上引いている」ときにだけ
    できるので、重複を落としてしまうと作れない。

    論文側は SciSciNet の `Paper_pair[k]`（集合）に合わせ、1論文の中で同じ対が
    何回出ても1回として扱う。コーパス側が出現回数で重み付きなのと非対称だが、これが仕様である。
    """
    con.register("ours_df", ours)
    con.execute("CREATE OR REPLACE TABLE ours AS SELECT * FROM ours_df")
    con.execute(f"""
        CREATE OR REPLACE TABLE our_ref_counts AS
        WITH e AS (
            SELECT o.paper_uid, o.year_openalex AS y, unnest(w.referenced_works) AS ref
            FROM ours o JOIN read_parquet('{SLIM_GLOB}') w ON w.work_id = o.wid
        )
        SELECT e.paper_uid, e.y, m.source_id AS j, count(*)::INTEGER AS cnt
        FROM e JOIN work_meta m ON m.work_id = e.ref
        GROUP BY 1, 2, 3
    """)
    con.execute("CREATE OR REPLACE TABLE jstar AS SELECT DISTINCT j FROM our_ref_counts")
    con.execute("""
        CREATE OR REPLACE TABLE our_pairs AS
        SELECT DISTINCT a.paper_uid, a.y, a.j AS j1, b.j AS j2
        FROM our_ref_counts a JOIN our_ref_counts b
          ON a.paper_uid = b.paper_uid AND a.j < b.j
        UNION
        -- 同一誌どうしの対。2本以上引いているときだけできる
        SELECT paper_uid, y, j AS j1, j AS j2 FROM our_ref_counts WHERE cnt >= 2
    """)
    n_j = con.execute("SELECT count(*) FROM jstar").fetchone()[0]
    n_p = con.execute("SELECT count(*) FROM our_pairs").fetchone()[0]
    n_same = con.execute("SELECT count(*) FROM our_pairs WHERE j1 = j2").fetchone()[0]
    print(f"J* {n_j:,} 誌 / 我々の論文のジャーナル対 {n_p:,}"
          f"（うち同一誌どうし {n_same:,}）", flush=True)


# ---------------------------------------------------------------- 疎行列での計数

def cooccurrence(si: np.ndarray, ji: np.ndarray, n_src: int, n_j: int) -> np.ndarray:
    """ジャーナル対ごとの出現回数を密行列 (n_j × n_j) で返す。

    SciSciNet は参考文献の**全ペア**を列挙して数える。誌Aから3本・誌Bから2本引いていれば
    対(A,B) に 3×2=6 を足す（「両方を引いた論文数」の1ではない）。
    同一誌どうしの対(A,A) も数え、誌Aから3本なら 3本から2本選ぶ組み合わせで3を足す。

    行列 M を「行=論文・列=誌・値=引いた本数」とすると、

      非対角 (A≠B) … (MᵀM)[A,B] = Σ_p c_A(p)·c_B(p)      … これがそのまま欲しい値
      対角   (A,A) … (MᵀM)[A,A] = Σ_p c_A(p)²            … 欲しいのは Σ_p C(c_A(p),2)

    なので対角だけ (Σc² − Σc)/2 に直す。Σc は M の列和である。
    c(c−1) は常に偶数なので割り切れる。
    """
    m = ji >= 0
    rows = si[m]
    cols = ji[m]
    # coo → csr で重複が合算されるので、M[p, A] は論文 p が誌 A を引いた本数になる
    M = sp.coo_matrix(
        (np.ones(rows.size, dtype=np.int64), (rows, cols)),
        shape=(n_src, n_j),
    ).tocsr()
    C = (M.T @ M).toarray()
    colsum = np.asarray(M.sum(axis=0)).ravel()
    np.fill_diagonal(C, (C.diagonal() - colsum) // 2)
    return C


def shuffle_strata(ji: np.ndarray, bounds: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    """被引用年 cy の層ごとにジャーナル列を入れ替える。

    ji は cy で整列済みなので、層は連続スライスになる。スライスを in-place で
    シャッフルすれば、各論文が各年から引く本数と各ジャーナル年の被引用数は保たれる。
    """
    out = ji.copy()
    for a, b in zip(bounds[:-1], bounds[1:]):
        if b - a > 1:
            rng.shuffle(out[a:b])
    return out


def run_year(con: duckdb.DuckDBPyConnection, year: int, rng: np.random.Generator) -> pd.DataFrame:
    t0 = time.time()
    con.execute(f"""
        CREATE OR REPLACE TABLE edges_raw AS
        WITH corpus AS (
            SELECT work_id, referenced_works FROM read_parquet('{SLIM_GLOB}')
            WHERE publication_year = {year} AND type = 'article' AND len(referenced_works) > 0
        ),
        e AS (SELECT work_id AS src, unnest(referenced_works) AS ref FROM corpus),
        j AS (SELECT e.src, m.source_id AS j, m.cy
              FROM e JOIN work_meta m ON m.work_id = e.ref),
        -- SciSciNet は参考文献1000本超の論文を飛ばす（cur_len > 1000 で continue）。
        -- 1本の総説が50万個の対を生んで計数を独占するのを防ぐため。
        -- cur_len は掲載誌が分かる参照の本数なので、結合後に数える
        big AS (SELECT src FROM j GROUP BY src HAVING count(*) > 1000)
        SELECT * FROM j WHERE src NOT IN (SELECT src FROM big)
    """)
    n_edges = con.execute("SELECT count(*) FROM edges_raw").fetchone()[0]
    con.execute(
        f"CREATE OR REPLACE TABLE target AS SELECT DISTINCT j1, j2 FROM our_pairs WHERE y = {year}")
    n_target = con.execute("SELECT count(*) FROM target").fetchone()[0]
    print(f"  {year}: エッジ {n_edges:,} / 対象ペア {n_target:,}  [{time.time()-t0:.0f}秒]", flush=True)
    if n_target == 0:
        return pd.DataFrame()

    # 対象ペアに現れる誌だけに列番号を振る。シャッフルは全ネットワーク上で済ませるので、
    # ここで絞っても対象ペアの計数は変わらない
    con.execute("""
        CREATE OR REPLACE TABLE target_j AS
        SELECT j, (row_number() OVER (ORDER BY j))::INTEGER - 1 AS ji
        FROM (SELECT j1 AS j FROM target UNION SELECT j2 FROM target)
    """)
    n_j = con.execute("SELECT count(*) FROM target_j").fetchone()[0]

    # 論文 id は最大 50億まであり int32 に収まらないので、DuckDB 側で行番号に振り直す
    con.execute("""
        CREATE OR REPLACE TABLE srcmap AS
        SELECT src, (row_number() OVER ())::INTEGER - 1 AS si
        FROM (SELECT DISTINCT src FROM edges_raw)
    """)
    n_src = con.execute("SELECT count(*) FROM srcmap").fetchone()[0]
    print(f"    対象ジャーナル {n_j:,} 誌 / コーパス論文 {n_src:,} 件", flush=True)

    t = time.time()
    arr = con.execute("""
        SELECT s.si, COALESCE(t.ji, -1)::INTEGER AS ji, e.cy::INTEGER AS cy
        FROM edges_raw e
        JOIN srcmap s ON s.src = e.src
        LEFT JOIN target_j t ON t.j = e.j
        ORDER BY cy
    """).to_arrow_table()
    si = arr.column("si").to_numpy(zero_copy_only=False)
    ji = arr.column("ji").to_numpy(zero_copy_only=False)
    cy = arr.column("cy").to_numpy(zero_copy_only=False)
    del arr
    # 層の境界。cy で整列済みなので、値が変わる位置が層の切れ目になる
    bounds = np.concatenate(([0], np.flatnonzero(np.diff(cy)) + 1, [cy.size]))
    del cy
    print(f"    配列化 {si.size:,} エッジ / 層 {len(bounds)-1} 個  [{time.time()-t:.0f}秒]", flush=True)

    ti, tj = con.execute("""
        SELECT a.ji AS i1, b.ji AS i2 FROM target t
        JOIN target_j a ON a.j = t.j1 JOIN target_j b ON b.j = t.j2
    """).to_arrow_table().to_pandas().values.T
    ti = ti.astype(np.int32)
    tj = tj.astype(np.int32)

    t = time.time()
    observed = cooccurrence(si, ji, n_src, n_j)[ti, tj]
    print(f"    観測集計 {time.time()-t:.1f}秒", flush=True)

    rand = np.empty((N_RAND, ti.size), dtype=np.int64)
    for r in range(N_RAND):
        t = time.time()
        js = shuffle_strata(ji, bounds, rng)
        t_sh = time.time() - t
        rand[r] = cooccurrence(si, js, n_src, n_j)[ti, tj]
        print(f"    ランダム化 {r+1}/{N_RAND}  {time.time()-t:.1f}秒"
              f"（うちシャッフル {t_sh:.1f}秒）", flush=True)
    del si, ji

    mu = rand.mean(axis=0)
    sd = rand.std(axis=0, ddof=0)  # SciSciNet は np.std（母標準偏差）
    # ランダム化で一度も出なかった対は sd=0 になる。観測も0なら z=0、
    # 観測が正なら z が定義できないので NaN にして後段の中央値・10パーセンタイルから外す。
    # この扱いは「偶然では出ないのに実際には出た対」を捨てることになるので、
    # 割合を毎回出しておく（多ければランダム化回数を増やすか、扱いを決め直す）
    z = np.where(sd > 0, (observed - mu) / np.where(sd > 0, sd, 1.0),
                 np.where(observed - mu == 0, 0.0, np.nan))
    n_nan = int(np.isnan(z).sum())
    print(f"    z が定義できない対 {n_nan:,}/{z.size:,}"
          f"（{n_nan/max(z.size,1)*100:.1f}%、ランダム化 {N_RAND} 回）", flush=True)

    pair_z = pd.DataFrame({"i1": ti, "i2": tj, "observed": observed, "mu": mu, "sd": sd, "z": z})
    jmap = con.execute("SELECT j, ji FROM target_j").df()
    idx2j = jmap.sort_values("ji")["j"].values
    pair_z["j1"] = idx2j[pair_z["i1"].values]
    pair_z["j2"] = idx2j[pair_z["i2"].values]
    pair_z = pair_z[["j1", "j2", "observed", "mu", "sd", "z"]]

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    pair_z.to_parquet(OUT_DIR / f"pair_zscores_{year}.parquet", index=False)

    con.register("pair_z_df", pair_z)
    res = con.execute(f"""
        SELECT p.paper_uid, {year} AS year,
               count(*) AS n_pairs,
               count(z.z) AS n_pairs_with_z,
               median(z.z) AS median_z,
               quantile_cont(z.z, 0.1) AS p10_z
        FROM our_pairs p JOIN pair_z_df z ON z.j1 = p.j1 AND z.j2 = p.j2
        WHERE p.y = {year}
        GROUP BY p.paper_uid
    """).df()
    print(f"  {year}: 論文 {len(res)} 件 完了  [合計 {time.time()-t0:.0f}秒]", flush=True)
    return res


def main() -> int:
    ours = load_our_papers()
    years = [int(x) for x in sys.argv[1:]] or sorted(
        int(y) for y in ours["year_openalex"].dropna().unique())
    rng = np.random.default_rng(SEED)
    con = duckdb.connect(DB_PATH)
    con.execute("SET threads=8; SET preserve_insertion_order=false;")
    build_work_meta(con)
    setup(con, ours)

    out = [d for y in years if len(d := run_year(con, y, rng))]
    if not out:
        print("対象ペアのある年がなかった。出力は書き換えない", flush=True)
        return 1
    res = pd.concat(out, ignore_index=True)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUT_DIR / "paper_novelty.csv"
    if path.exists() and len(sys.argv) > 1:
        # 年を指定して部分実行したときは既存分とマージする
        old = pd.read_csv(path)
        res = pd.concat([old[~old["year"].isin(years)], res], ignore_index=True)
    res.sort_values(["year", "paper_uid"]).to_csv(path, index=False)
    print(f"\n出力: {path}  {len(res)} 件")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
