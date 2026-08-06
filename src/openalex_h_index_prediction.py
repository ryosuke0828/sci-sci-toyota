#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""OpenAlex で「h 指数の予測力」(書籍 図2.2) を再現する。

元実験: Hirsch, "Does the h index have predictive power?", PNAS 104 (2007) /
Wang & Barabasi, "The Science of Science" (2021) 第2章 (The h-index) の 図2.2。

図2.2 の構造
------------
研究者ごとに、ある時点 t1 で測った 4 つの単一指標が、後の時点 t2 での到達度
(√C(t2) = t2 時点の累積被引用数の平方根) をどれだけ予測できるかを散布図で比較する。
縦軸は 4 枚とも √C(t2)、横軸はそれぞれ:

    左上 : h(t1)        ... t1 時点の h 指数
    右上 : √C(t1)       ... t1 時点の累積被引用数の平方根
    左下 : N(t1)        ... t1 時点の論文数
    右下 : C(t1)/N(t1)  ... t1 時点の論文あたり被引用数

Hirsch の主張は「h(t1) と √C(t1) は将来 √C(t2) をよく予測する (相関が高い) が、
N(t1) や C(t1)/N(t1) は予測力が劣る」。元実験は物理学者 (Hirsch 自身が UCSD 凝縮系
物理) を対象にしている。ここでは同じ実験を **信号処理 (Signal processing) の研究者**
で行う。

データ源: OpenAlex (https://openalex.org)。無料・APIキー不要。polite pool のため
mailto を渡す。

実装上の要点 (再現の肝)
----------------------
1) t 時点の指標復元: 各論文の counts_by_year (年ごとの被引用数) を使い、「year<=t の
   被引用数の総和」で『t 年末までにその論文が受けた被引用数』を求める。これを論文集合に
   適用して h(t)・C(t)・N(t) を任意の t について再構成する。著者あたり works 取得 1〜2
   コールで全指標が揃う (per-paper の追加コール不要)。
2) 打ち切り対策: OpenAlex の counts_by_year は概ね WINDOW_START (=2012) 年以降しか
   持たない。それ以前に出た論文は WINDOW_START 前の被引用が欠落し t1 時点の値を過小評価
   する。よって **初出版が WINDOW_START 年以降の研究者のみ** を対象にする。この条件下では
   全被引用が counts_by_year の窓に収まり、t1/t2 時点の指標を正確に復元できる。
   (代償として凝縮系物理のようなベテラン中心の母集団は扱えない。2012 年以降に始まった
    比較的若いコホートでの再現になる点に留意。)
3) 名寄せ対策: 既存モジュールと同様、日本・中国系の著者 (名寄せが不安定) は除外する。

重いインフラ (HTTP クライアント・キャッシュ・著者サンプリング・国籍判定) は既存の
`openalex_random_impact_rule.py` から再利用する。
"""

from __future__ import annotations

import argparse
import csv
import os
import sys
from typing import Dict, List, Optional

# 既存モジュールの実証済みインフラを再利用する (同じフォルダに置かれている前提)。
from openalex_random_impact_rule import (
    OpenAlexClient,
    DEFAULT_MAILTO,
    short_id,
    _join_filters,
    harvest_candidate_authors,
    is_excluded_author,
    pearson,
    EXCLUDE_COUNTRIES,
)
import random

# ---------------------------------------------------------------------------
# 既定設定 (CLI 引数で上書き可能)
# ---------------------------------------------------------------------------
WINDOW_START = 2012           # counts_by_year が遡れる最古の年 (これ以前の被引用は欠落)
T1 = 2019                     # 予測子を測る時点 (snapshot)。2012コホートで約7年分の記録になる
T2 = 2025                     # 到達度を測る時点 (被引用を数え切れる直近の暦年)。予測幅 t2-t1=6年
MIN_RECORD_YEARS = 2          # t1 までに必要な記録年数 (first_year <= t1 - これ)
MIN_PAPERS = 5                # t1 時点の論文数の下限
MAX_PAPERS_TOTAL = 1000       # これを超える総論文数は名寄せ破綻 (複数人併合) とみなし除外

# サンプリングする分野と年代。信号処理 = Signal processing (concepts.id:C104267543)。
# concepts は将来廃止予定。エラー時は分野フィルタ無しに自動フォールバックする (再利用先の実装)。
FIELD_FILTER = "concepts.id:C104267543"    # Signal processing。None で全分野
TYPE_FILTER = "type:article"               # 論文に限定。None で全種別
# 候補著者は「2012〜t1 に信号処理の論文を出した著者」から集める (若いコホートを狙う)。
SEED_ERA = (f"{WINDOW_START}-01-01", f"{T1}-12-31")

EXCLUDE_COUNTRIES_DEFAULT = EXCLUDE_COUNTRIES  # {"JP","CN"} を流用

SAMPLE_WORKS = 10000          # 候補著者を集めるためにサンプリングする works 数
MAX_AUTHORS_PER_WORK = 30     # 1 論文から拾う著者数の上限
CANDIDATE_LIMIT = 3000        # 評価する候補著者数の上限 (採択率 ~5% 想定で 150 名狙い)
N_RESEARCHERS = 150           # フィルタ通過させたい研究者数 (目標)

RNG_SEED = 42
# モジュールの配置にかかわらず、リポジトリ内のキャッシュを既定にする。
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_CACHE = os.path.join(PROJECT_ROOT, "data", "cache", "openalex_h_index_prediction.json")

# 予測子のキーと図中ラベル (表示順 = 左上,右上,左下,右下)
PREDICTORS = [
    ("h_t1", r"$h(t_1)$"),
    ("sqrt_C_t1", r"$\sqrt{C(t_1)}$"),
    ("N_t1", r"$N(t_1)$"),
    ("CpN_t1", r"$C(t_1)/N(t_1)$"),
]


# ---------------------------------------------------------------------------
# 指標の復元ヘルパー
# ---------------------------------------------------------------------------
def citations_through(counts_by_year: Dict[int, int], year: int) -> int:
    """counts_by_year (year->count) から「year 年末までに受けた累積被引用数」を返す。"""
    return sum(c for y, c in counts_by_year.items() if y <= year)


def h_index(citation_counts: List[int]) -> int:
    """被引用数リストから h 指数を計算する。

    定義: h 本の論文がそれぞれ h 件以上の被引用を持つ最大の h。降順に並べて
    「i 番目の論文の被引用数 >= i」が成り立つ最後の i が h。
    """
    cs = sorted(citation_counts, reverse=True)
    h = 0
    for i, c in enumerate(cs, start=1):
        if c >= i:
            h = i
        else:
            break
    return h


# ---------------------------------------------------------------------------
# ステップ: 1 著者の全 works を取得
# ---------------------------------------------------------------------------
def fetch_author_works(client: OpenAlexClient, author_id: str,
                       type_filter: Optional[str]) -> List[dict]:
    """著者の全 works を cursor ページングで取得する。各 work に counts_by_year を含める。

    select で必要列だけに絞る。counts_by_year は [{'year':Y,'cited_by_count':C}, ...] の
    形で返るので year->count の dict に畳む。
    """
    flt = _join_filters([f"author.id:{author_id}", type_filter])
    works: List[dict] = []
    cursor = "*"
    while cursor:
        data = client.get("/works", {"filter": flt, "per_page": 200, "cursor": cursor,
                                     "select": "id,publication_year,cited_by_count,counts_by_year"})
        results = data.get("results", [])
        for w in results:
            y = w.get("publication_year")
            if y is None:
                continue
            cby = {}
            for c in (w.get("counts_by_year") or []):
                yr = c.get("year")
                if yr is not None:
                    cby[int(yr)] = int(c.get("cited_by_count", 0) or 0)
            works.append({"id": short_id(w["id"]), "year": int(y),
                          "cited_by_count": int(w.get("cited_by_count", 0) or 0),
                          "counts_by_year": cby})
        cursor = data.get("meta", {}).get("next_cursor")
        if not results:
            break
    return works


# ---------------------------------------------------------------------------
# ステップ: 1 著者を「研究者レコード」に変換
# ---------------------------------------------------------------------------
def build_record(client: OpenAlexClient, author_id: str, name: str,
                 type_filter: Optional[str], *, window_start: int, t1: int, t2: int,
                 min_record_years: int, min_papers: int, max_papers_total: int,
                 exclude_countries=EXCLUDE_COUNTRIES_DEFAULT) -> Optional[dict]:
    """1 著者を評価し、条件を満たせば研究者レコードを返す。満たさなければ None。"""
    # 日本・中国系は名寄せが不安定なため除外 (works 取得前に弾いてコール節約)
    if is_excluded_author(client, author_id, name, exclude_countries):
        return None

    works = fetch_author_works(client, author_id, type_filter)
    if not works:
        return None
    if len(works) > max_papers_total:        # 異常な多作 = 名寄せ破綻とみなす
        return None

    years = [w["year"] for w in works]
    first_year = min(years)
    # 打ち切り対策: counts_by_year は window_start 年以降しか持たない。first_year が
    # それ以前だと t1 時点の被引用を正確に復元できないため除外する。
    if first_year < window_start:
        return None
    # t1 までに最低 min_record_years 年の記録が必要 (h(t1) 等が意味を持つように)
    if t1 - first_year < min_record_years:
        return None

    # --- t1 時点の指標 ---
    papers_t1 = [w for w in works if w["year"] <= t1]
    if len(papers_t1) < min_papers:
        return None
    c_t1 = [citations_through(w["counts_by_year"], t1) for w in papers_t1]
    C_t1 = sum(c_t1)
    if C_t1 <= 0:
        return None
    N_t1 = len(papers_t1)
    h_t1 = h_index(c_t1)
    CpN_t1 = C_t1 / N_t1

    # --- t2 時点の到達度 (全論文。t1 以降に出た新しい論文も含む) ---
    papers_t2 = [w for w in works if w["year"] <= t2]
    c_t2 = [citations_through(w["counts_by_year"], t2) for w in papers_t2]
    C_t2 = sum(c_t2)
    if C_t2 <= 0:
        return None
    h_t2 = h_index(c_t2)

    return {
        "author_id": author_id,
        "name": name,
        "first_year": first_year,
        "last_year": max(years),
        "n_papers_total": len(works),
        # 予測子 (t1)
        "h_t1": h_t1,
        "C_t1": C_t1,
        "sqrt_C_t1": C_t1 ** 0.5,
        "N_t1": N_t1,
        "CpN_t1": CpN_t1,
        # 到達度 (t2)
        "C_t2": C_t2,
        "sqrt_C_t2": C_t2 ** 0.5,
        "h_t2": h_t2,
    }


# ---------------------------------------------------------------------------
# 一括実行 (notebook からも呼べる)
# ---------------------------------------------------------------------------
def run(client: OpenAlexClient, *,
        field_filter: Optional[str] = FIELD_FILTER,
        type_filter: Optional[str] = TYPE_FILTER,
        era: tuple = SEED_ERA,
        sample_works: int = SAMPLE_WORKS,
        max_authors_per_work: int = MAX_AUTHORS_PER_WORK,
        candidate_limit: int = CANDIDATE_LIMIT,
        n_researchers: int = N_RESEARCHERS,
        window_start: int = WINDOW_START,
        t1: int = T1, t2: int = T2,
        min_record_years: int = MIN_RECORD_YEARS,
        min_papers: int = MIN_PAPERS,
        max_papers_total: int = MAX_PAPERS_TOTAL,
        exclude_countries=EXCLUDE_COUNTRIES_DEFAULT,
        seed: int = RNG_SEED,
        verbose: bool = True) -> dict:
    """全パイプラインを実行し、結果一式を dict で返す。"""
    if verbose:
        print(f"[1/3] 候補著者をサンプリング (field={field_filter}, era={era}) ...")
    authors = harvest_candidate_authors(client, field_filter, type_filter, era,
                                        sample_works, max_authors_per_work, seed)
    if verbose:
        print(f"      候補著者 {len(authors)} 名")

    items = list(authors.items())
    random.Random(seed).shuffle(items)   # 上位著者への偏りを避けるため順序をシャッフル

    if verbose:
        excl = "/".join(sorted(exclude_countries)) if exclude_countries else "なし"
        print(f"[2/3] 各著者を評価 (初出版>={window_start}, t1={t1} までに>= {min_papers}本/"
              f">= {min_record_years}年, 除外国={excl}) ...")
    records: List[dict] = []
    evaluated = 0
    for aid, name in items:
        if len(records) >= n_researchers or evaluated >= candidate_limit:
            break
        evaluated += 1
        try:
            rec = build_record(client, aid, name, type_filter,
                               window_start=window_start, t1=t1, t2=t2,
                               min_record_years=min_record_years, min_papers=min_papers,
                               max_papers_total=max_papers_total,
                               exclude_countries=exclude_countries)
        except RuntimeError as e:
            print(f"[warn] skip {aid}: {e}", file=sys.stderr)
            continue
        if rec:
            records.append(rec)
            if verbose and len(records) % 20 == 0:
                print(f"      kept {len(records)}/{n_researchers} (evaluated {evaluated})")
    client.save_cache()

    if verbose:
        print(f"      対象研究者 {len(records)} 名 (評価 {evaluated} 名)")
    if len(records) < 5:
        raise RuntimeError(f"研究者が {len(records)} 名しか集まりませんでした。"
                           f"candidate_limit/sample_works を増やすか条件を緩めてください。")

    if verbose:
        print("[3/3] 相関を計算 ...")
    y = [r["sqrt_C_t2"] for r in records]
    corr = {}                              # 各予測子と √C(t2) の Pearson 相関
    for key, _label in PREDICTORS:
        corr[key] = pearson([r[key] for r in records], y)

    stats = {
        "n_researchers": len(records),
        "n_evaluated": evaluated,
        "t1": t1, "t2": t2,
        "window_start": window_start,
        "mean_h_t1": sum(r["h_t1"] for r in records) / len(records),
        "mean_h_t2": sum(r["h_t2"] for r in records) / len(records),
        "corr": corr,
    }
    return {"records": records, "stats": stats}


# ---------------------------------------------------------------------------
# 可視化・保存
# ---------------------------------------------------------------------------
def _linfit(xs: List[float], ys: List[float]):
    """最小二乗で y = a*x + b の (a, b) を返す (numpy 非依存)。"""
    n = len(xs)
    if n == 0:
        return 0.0, 0.0
    mx = sum(xs) / n
    my = sum(ys) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    if sxx <= 0:
        return 0.0, my
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    a = sxy / sxx
    return a, my - a * mx


def make_figure(results: dict):
    """結果から 2x2 散布図 (図2.2 相当) を作って Figure を返す。

    縦軸は 4 枚とも √C(t2)。横軸は h(t1), √C(t1), N(t1), C(t1)/N(t1)。各パネルに回帰直線と
    Pearson 相関 r を表示する。r が高いほどその指標は将来をよく予測する。
    matplotlib は標準ライブラリ外。日本語フォント未設定環境での豆腐化を避けるため軸ラベルは
    数式/英語にする。
    """
    import matplotlib.pyplot as plt

    records = results["records"]
    st = results["stats"]
    t1, t2 = st["t1"], st["t2"]
    y = [r["sqrt_C_t2"] for r in records]

    fig, axes = plt.subplots(2, 2, figsize=(11, 9))
    flat = [axes[0][0], axes[0][1], axes[1][0], axes[1][1]]  # 左上,右上,左下,右下

    for ax, (key, label) in zip(flat, PREDICTORS):
        x = [r[key] for r in records]
        ax.scatter(x, y, s=18, alpha=0.6, color="#c0392b", edgecolor="none")
        # 回帰直線 (傾向の目安)
        a, b = _linfit(x, y)
        xmin, xmax = min(x), max(x)
        ax.plot([xmin, xmax], [a * xmin + b, a * xmax + b], color="#2c3e50", lw=1.5)
        r = st["corr"][key]
        ax.set_xlabel(label)
        ax.set_ylabel(r"$\sqrt{C(t_2)}$")
        ax.set_title(f"{label}  vs  " + r"$\sqrt{C(t_2)}$" + f"   (r = {r:.2f})")

    fig.suptitle(
        f"Predictive power of single indicators (Hirsch 2007 / Fig 2.2) — Signal processing\n"
        f"N = {st['n_researchers']} researchers,  t1 = {t1},  t2 = {t2}  "
        f"(OpenAlex, careers starting >= {st['window_start']})",
        fontsize=11)
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    return fig


def save_outputs(results: dict, out_prefix: str) -> None:
    """図 (PNG)・研究者一覧 (CSV) を保存する。"""
    import matplotlib
    matplotlib.use("Agg")
    fig = make_figure(results)
    png = out_prefix + ".png"
    fig.savefig(png, dpi=150)
    print(f"  saved figure : {png}")

    rec_csv = out_prefix + "_researchers.csv"
    cols = ["author_id", "name", "first_year", "last_year", "n_papers_total",
            "h_t1", "C_t1", "sqrt_C_t1", "N_t1", "CpN_t1",
            "C_t2", "sqrt_C_t2", "h_t2"]
    with open(rec_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for r in results["records"]:
            w.writerow(r)
    print(f"  saved records: {rec_csv}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def parse_args(argv=None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Reproduce Fig 2.2 (h-index predictive power) with OpenAlex.")
    p.add_argument("--mailto", default=DEFAULT_MAILTO, help="polite pool 用メールアドレス")
    p.add_argument("--field", default=FIELD_FILTER,
                   help="works フィルタ片 (例 concepts.id:C104267543=Signal processing)。'none' で全分野")
    p.add_argument("--type", dest="type_filter", default=TYPE_FILTER,
                   help="works 種別フィルタ (例 type:article)。'none' で全種別")
    p.add_argument("--era-start", default=SEED_ERA[0])
    p.add_argument("--era-end", default=SEED_ERA[1])
    p.add_argument("--sample-works", type=int, default=SAMPLE_WORKS)
    p.add_argument("--candidate-limit", type=int, default=CANDIDATE_LIMIT)
    p.add_argument("--n-researchers", type=int, default=N_RESEARCHERS)
    p.add_argument("--window-start", type=int, default=WINDOW_START)
    p.add_argument("--t1", type=int, default=T1)
    p.add_argument("--t2", type=int, default=T2)
    p.add_argument("--min-record-years", type=int, default=MIN_RECORD_YEARS)
    p.add_argument("--min-papers", type=int, default=MIN_PAPERS)
    p.add_argument("--include-jp-cn", action="store_true",
                   help="既定では除外する日本・中国系の著者を含める")
    p.add_argument("--seed", type=int, default=RNG_SEED)
    p.add_argument("--out", default="openalex_h_index_prediction", help="出力ファイルの接頭辞")
    p.add_argument("--cache", default=DEFAULT_CACHE)
    p.add_argument("--no-cache", action="store_true")
    p.add_argument("--smoke", action="store_true", help="少数で素早く配管確認する")
    return p.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)
    field = None if str(args.field).lower() == "none" else args.field
    type_filter = None if str(args.type_filter).lower() == "none" else args.type_filter

    if args.smoke:  # 配管確認用の最小設定
        args.sample_works = min(args.sample_works, 400)
        args.candidate_limit = min(args.candidate_limit, 80)
        args.n_researchers = min(args.n_researchers, 10)

    client = OpenAlexClient(mailto=args.mailto, cache_path=args.cache,
                            use_cache=not args.no_cache)

    # 分野の確認 (concepts ID から表示名を引いてログに出す)。失敗しても続行。
    if field and field.startswith("concepts.id:"):
        try:
            cid = field.split(":", 1)[1]
            cdata = client.get(f"/concepts/{cid}", {})
            print(f"[info] field = {cdata.get('display_name')} ({cid})")
        except Exception:
            pass

    exclude_countries = set() if args.include_jp_cn else EXCLUDE_COUNTRIES_DEFAULT
    results = run(client, field_filter=field, type_filter=type_filter,
                  era=(args.era_start, args.era_end), sample_works=args.sample_works,
                  candidate_limit=args.candidate_limit, n_researchers=args.n_researchers,
                  window_start=args.window_start, t1=args.t1, t2=args.t2,
                  min_record_years=args.min_record_years, min_papers=args.min_papers,
                  exclude_countries=exclude_countries, seed=args.seed)
    client.save_cache()

    st = results["stats"]
    print("\n=== 結果サマリ ===")
    print(f"  研究者数 N           : {st['n_researchers']}")
    print(f"  t1 / t2              : {st['t1']} / {st['t2']}")
    print(f"  平均 h(t1) / h(t2)   : {st['mean_h_t1']:.1f} / {st['mean_h_t2']:.1f}")
    print("  √C(t2) との Pearson 相関 (予測力):")
    for key, label in PREDICTORS:
        # ラベルの数式記号を素のテキストに直して表示
        plain = label.replace("$", "").replace("\\sqrt", "sqrt").replace("{", "").replace("}", "")
        print(f"    {plain:14s}: r = {st['corr'][key]:.3f}")
    print("  → h(t1) と sqrt C(t1) の r が高く、N(t1)・C(t1)/N(t1) の r が低ければ"
          " Hirsch の主張を支持する。\n")

    save_outputs(results, args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
