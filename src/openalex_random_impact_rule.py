#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""OpenAlex で「ランダム・インパクト・ルール」を再現する。

元実験: Sinatra et al., "Quantifying the evolution of individual scientific
impact", Science 354 (2016) / Wang & Barabasi, "The Science of Science" (2021) の
キャリア章。

アイデア
--------
キャリアが MIN_CAREER_YEARS 年以上の研究者について、各論文をキャリア年次
t (= 出版年 - キャリア開始年) に並べ、各論文に c10 (出版後 10 年以内の被引用数)
を付与する。最大インパクト論文が位置する年次を t* とし、

    P(t) = 研究者全体で「最高傑作」が年次 t に出る確率

を作る。ランダム・インパクト・ルールは「最高傑作はキャリア中のどの論文にも等確率で
宿りうる (＝特別な創造ピークは無い)」と主張する。これを次の 2 つで比較して検証する:

    * REAL      : 実データの t* 分布
    * RANDOMIZED: 各研究者の論文に付いた c10 をシャッフルして t* を取り直した分布

ルールが成り立てば両曲線は重なる。

データ源: OpenAlex (https://openalex.org)。無料・APIキー不要。
polite pool を使うため --mailto にメールアドレスを渡す。

実装上の要点 (再現の肝)
----------------------
1) c10 の算出: OpenAlex の counts_by_year は直近 ~10 年しか持たないため古い論文に
   使えない。代わりに `cites:<work>` ＋ publication_date 範囲フィルタで「出版後
   10 年以内に出た引用論文数」を直接 meta.count として数える (論文1本=APIコール1回)。
2) 右側打ち切り対策: c10 を完全に測れるのは出版から 10 年経った論文だけ。よって
   CUTOFF_YEAR (= 直近の完結年 - 10) 以前の論文のみを「適格論文」とし、その範囲で
   キャリア・最大値を定義する。
3) シャッフルの等価性: 「c10 を研究者内でシャッフルして argmax を取る」操作は、
   最大値が一様ランダムな 1 本に乗るのと同じ。したがって全論文の c10 を取得せずとも、
   出版年ヒストグラムからの一様抽選 (モンテカルロ) で帰無分布を忠実に再現できる。
   これによりコール数を大幅に削減する。
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import random
import sys
import time
from collections import defaultdict
from typing import Dict, List, Optional

import requests

# ---------------------------------------------------------------------------
# 既定設定 (CLI 引数で上書き可能)
# ---------------------------------------------------------------------------
BASE_URL = "https://api.openalex.org"
DEFAULT_MAILTO = "r.ikura@msp-lab.org"

C10_WINDOW = 10               # 「出版後 N 年以内」の N
LAST_COMPLETE_YEAR = 2025     # 被引用を完全に数え切れる直近の暦年
CUTOFF_YEAR = LAST_COMPLETE_YEAR - C10_WINDOW  # = 2015。これ以前の論文のみ適格

MIN_CAREER_YEARS = 20         # キャリアスパンの下限 (適格論文の最初〜最後)
MAX_CAREER_YEARS = 60         # キャリアスパンの上限。これを超える=名寄せ破綻(複数人の併合)とみなし除外
MIN_PAPERS = 10               # 適格論文数の下限

# 名寄せが特に不安定な国の著者を除外する（docs/notes/openalex_exploration.md 参照）。空集合で無効化。
EXCLUDE_COUNTRIES = {"JP", "CN"}  # 日本・中国

# サンプリングする分野と年代 (書籍は物理学者を分析している)。
# concepts は将来廃止予定。エラー時は分野フィルタ無しに自動フォールバックする。
FIELD_FILTER = "concepts.id:C121332964"   # Physics。None で全分野
TYPE_FILTER = "type:article"               # 論文に限定。None で全種別
SEED_ERA = ("1960-01-01", "2005-12-31")    # この期間に活動していた著者を母集団にする (広めに)

TOP_K = 20                    # c10 を厳密計算する「被引用数上位」論文数 (最大値探索用)
SAMPLE_WORKS = 2000           # 候補著者を集めるためにサンプリングする works 数
MAX_AUTHORS_PER_WORK = 50     # 1 論文から拾う著者数の上限 (超多著者論文対策)
CANDIDATE_LIMIT = 800         # 評価する候補著者数の上限
N_RESEARCHERS = 150           # フィルタ通過させたい研究者数 (目標)

RANDOM_REPEATS = 500          # 研究者あたりのシャッフル試行回数
RNG_SEED = 42

# モジュールの配置にかかわらず、リポジトリ内のキャッシュを既定にする。
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_CACHE = os.path.join(PROJECT_ROOT, "data", "cache", "openalex_random_impact_rule.json")
SLEEP_SEC = 0.1               # コール間の待ち (polite pool 配慮)


# ---------------------------------------------------------------------------
# OpenAlex クライアント (リトライ・キャッシュ付き)
# ---------------------------------------------------------------------------
def short_id(oid: Optional[str]) -> Optional[str]:
    """`https://openalex.org/A123` を `A123` に短縮する。None は素通し。"""
    if not oid:
        return None
    return oid.rsplit("/", 1)[-1]


class OpenAlexClient:
    """requests.Session をラップし、リトライ・指数バックオフ・ディスクキャッシュを足す。

    キャッシュはレスポンス JSON を {クエリ文字列: JSON} で保持する。c10 のカウントは
    論文ごとに 1 コール掛かるため、再実行を無料にするキャッシュが効く。
    """

    def __init__(self, mailto: str = DEFAULT_MAILTO, cache_path: Optional[str] = DEFAULT_CACHE,
                 use_cache: bool = True, sleep: float = SLEEP_SEC):
        self.mailto = mailto
        self.sleep = sleep
        self.use_cache = use_cache
        self.cache_path = cache_path
        self.session = requests.Session()
        # polite pool: User-Agent に mailto を入れる流儀 (既存ノートブックに合わせる)
        self.headers = {"User-Agent": f"random-impact-rule/1.0 (mailto:{mailto})",
                        "Accept": "application/json"}
        self.cache: Dict[str, dict] = {}
        self._dirty = 0
        if use_cache and cache_path and os.path.exists(cache_path):
            try:
                with open(cache_path, "r", encoding="utf-8") as f:
                    self.cache = json.load(f)
            except Exception:
                self.cache = {}

    # --- 内部: キャッシュキー (mailto は除外して安定化) -------------------
    @staticmethod
    def _key(path: str, params: dict) -> str:
        items = sorted((k, str(v)) for k, v in params.items() if k != "mailto")
        return path + "?" + "&".join(f"{k}={v}" for k, v in items)

    def get(self, path: str, params: Optional[dict] = None, retries: int = 5) -> dict:
        params = dict(params or {})
        key = self._key(path, params)
        if self.use_cache and key in self.cache:
            return self.cache[key]
        url = BASE_URL + path
        last_err = None
        for attempt in range(retries):
            try:
                resp = self.session.get(url, params=params, headers=self.headers, timeout=60)
            except requests.RequestException as e:
                last_err = e
                time.sleep(min(2 ** attempt, 30))
                continue
            if resp.status_code == 200:
                data = resp.json()
                if self.use_cache:
                    self.cache[key] = data
                    self._dirty += 1
                    if self._dirty >= 100:
                        self.save_cache()
                time.sleep(self.sleep)
                return data
            # レート超過・サーバ側一時障害はバックオフして再試行
            if resp.status_code in (429, 500, 502, 503, 504):
                wait = float(resp.headers.get("Retry-After", min(2 ** attempt, 30)))
                time.sleep(wait)
                last_err = RuntimeError(f"HTTP {resp.status_code}")
                continue
            raise RuntimeError(f"OpenAlex {resp.status_code}: {resp.text[:200]} ({resp.url})")
        raise RuntimeError(f"OpenAlex request failed after {retries} retries: {path} {params} ({last_err})")

    def count(self, path: str, params: dict) -> int:
        """meta.count だけ欲しいとき用 (結果本体は取得しない)。"""
        p = dict(params)
        p["per_page"] = 1
        p.setdefault("select", "id")
        data = self.get(path, p)
        return int(data.get("meta", {}).get("count", 0) or 0)

    def save_cache(self) -> None:
        if not (self.use_cache and self.cache_path):
            return
        tmp = self.cache_path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(self.cache, f)
        os.replace(tmp, self.cache_path)
        self._dirty = 0


def _join_filters(parts: List[Optional[str]]) -> str:
    """None を除いてフィルタ片をカンマ連結する。"""
    return ",".join(p for p in parts if p)


# ---------------------------------------------------------------------------
# ステップ 1: 候補著者の収集
# ---------------------------------------------------------------------------
def harvest_candidate_authors(client: OpenAlexClient, field_filter: Optional[str],
                              type_filter: Optional[str], era: tuple,
                              n_works: int, max_authors_per_work: int,
                              seed: int) -> Dict[str, str]:
    """指定分野・年代の works をランダムサンプリングし、著者 ID→名前 の辞書を返す。

    `sample=N&seed=S` で works を無作為抽出し (要 seed)、その authorships から著者を拾う。

    OpenAlex の制約: 1 回の sample は最大 10,000 件、かつ sample のページングも合計 10,000
    件まで (page*per_page <= 10,000)。よって n_works が 10,000 を超える場合は、seed を変えた
    複数バッチに分割して累積する (バッチ間の重複を避けるため seed をずらす)。
    """
    MAX_SAMPLE = 10000            # OpenAlex の sample 上限
    per_page = 200
    max_pages = MAX_SAMPLE // per_page  # = 50。sample ページングの上限

    base_filters = _join_filters([field_filter, type_filter,
                                  f"from_publication_date:{era[0]}",
                                  f"to_publication_date:{era[1]}"])
    fallback_filters = _join_filters([type_filter,
                                      f"from_publication_date:{era[0]}",
                                      f"to_publication_date:{era[1]}"])
    authors: Dict[str, str] = {}
    cur_filter = base_filters
    used_field = bool(field_filter)

    remaining = max(1, int(n_works))
    batch = 0
    while remaining > 0:
        sample_size = min(MAX_SAMPLE, remaining)
        pages = min(max(1, -(-sample_size // per_page)), max_pages)  # 切り上げ除算を上限でクリップ
        batch_seed = seed + batch    # バッチごとに seed を変えて別の無作為標本にする
        for page in range(1, pages + 1):
            params = {"filter": cur_filter, "sample": sample_size, "seed": batch_seed,
                      "per_page": per_page, "page": page,
                      "select": "id,authorships,publication_year"}
            try:
                data = client.get("/works", params)
            except RuntimeError as e:
                # 分野フィルタが効かない (concepts 廃止等) 場合は分野無しで再試行
                if used_field and batch == 0 and page == 1:
                    print(f"[warn] field filter failed ({e}); retry without field filter", file=sys.stderr)
                    cur_filter = fallback_filters
                    used_field = False
                    params["filter"] = cur_filter
                    data = client.get("/works", params)
                else:
                    raise
            results = data.get("results", [])
            if not results:
                break
            for w in results:
                for au in (w.get("authorships") or [])[:max_authors_per_work]:
                    a = au.get("author") or {}
                    aid = short_id(a.get("id"))  # 名寄せ未確定だと id が None になりうる
                    if aid:
                        authors.setdefault(aid, a.get("display_name") or "")
        remaining -= sample_size
        batch += 1
    return authors


# ---------------------------------------------------------------------------
# ステップ 2: 1 著者を「研究者レコード」に変換
# ---------------------------------------------------------------------------
def eligible_year_histogram(client: OpenAlexClient, author_id: str,
                            type_filter: Optional[str], cutoff_year: int) -> Dict[int, int]:
    """適格論文 (cutoff_year 以前) の出版年→本数ヒストグラムを 1 コールで得る。

    group_by=publication_year を使うと年ごとの本数が 1 リクエストで返る。これがキャリア
    スパン・本数・帰無モデル用の出版時刻分布をまとめて与える。
    """
    flt = _join_filters([f"author.id:{author_id}",
                         f"to_publication_date:{cutoff_year}-12-31", type_filter])
    # per_page は group_by が返すグループ数の上限も兼ねる。1 にすると 1 年しか返らないため
    # 200 (最大) を指定して全年次のグループを得る。
    data = client.get("/works", {"filter": flt, "group_by": "publication_year", "per_page": 200})
    hist: Dict[int, int] = {}
    for g in data.get("group_by", []):
        key = g.get("key")
        if key in (None, "unknown", ""):
            continue
        try:
            year = int(key)
        except (TypeError, ValueError):
            continue
        hist[year] = int(g.get("count", 0) or 0)
    return hist


def top_cited_eligible_works(client: OpenAlexClient, author_id: str,
                             type_filter: Optional[str], cutoff_year: int, k: int) -> List[dict]:
    """適格論文を被引用数の降順で上位 k 件取得する (最大 c10 の候補集合)。"""
    flt = _join_filters([f"author.id:{author_id}",
                         f"to_publication_date:{cutoff_year}-12-31", type_filter])
    data = client.get("/works", {"filter": flt, "sort": "cited_by_count:desc",
                                 "per_page": k, "select": "id,publication_year,cited_by_count,title"})
    out = []
    for w in data.get("results", []):
        y = w.get("publication_year")
        if y is None:
            continue
        out.append({"id": short_id(w["id"]), "year": int(y),
                    "cited_by_count": int(w.get("cited_by_count", 0) or 0),
                    "title": w.get("title")})
    return out


def c10_of_work(client: OpenAlexClient, work_id: str, pub_year: int, window: int) -> int:
    """論文 work_id が「出版年〜出版年+window 年」に受けた被引用数 (= c10)。

    cites:<work_id> で「その論文を引用している works」を絞り、publication_date 範囲で
    出版後 window 年以内に出たものに限定し、その件数 (meta.count) を返す。
    """
    lo, hi = pub_year, pub_year + window
    flt = _join_filters([f"cites:{work_id}",
                         f"from_publication_date:{lo}-01-01",
                         f"to_publication_date:{hi}-12-31"])
    return client.count("/works", {"filter": flt})


def _has_cjk(s: Optional[str]) -> bool:
    """名前に漢字・かな (= 日本/中国系の表記) が含まれるか。ハングルは対象外。"""
    if not s:
        return False
    for ch in s:
        o = ord(ch)
        if (0x4E00 <= o <= 0x9FFF) or (0x3400 <= o <= 0x4DBF) or (0x3040 <= o <= 0x30FF):
            return True
    return False


def author_country_codes(client: OpenAlexClient, author_id: str) -> List[str]:
    """著者の国コード一覧。last_known_institutions 優先、無ければ affiliations から拾う。"""
    data = client.get(f"/authors/{author_id}",
                      {"select": "id,display_name,last_known_institutions,affiliations"})
    codes: List[str] = []
    for inst in (data.get("last_known_institutions") or []):
        cc = inst.get("country_code")
        if cc:
            codes.append(cc)
    if not codes:
        for aff in (data.get("affiliations") or []):
            cc = (aff.get("institution") or {}).get("country_code")
            if cc:
                codes.append(cc)
    return codes


def is_excluded_author(client: OpenAlexClient, author_id: str, name: str,
                       exclude_countries) -> bool:
    """除外対象 (日本・中国系) なら True。名前の漢字/かな (無料) を先に見て、必要なら国を引く。"""
    if not exclude_countries:
        return False
    if _has_cjk(name):
        return True
    try:
        codes = author_country_codes(client, author_id)
    except RuntimeError:
        codes = []  # 取得失敗時は除外しない (素通し)
    return any(c in exclude_countries for c in codes)


def build_record(client: OpenAlexClient, author_id: str, name: str,
                 type_filter: Optional[str], cutoff_year: int, c10_window: int,
                 min_career_years: int, max_career_years: int, min_papers: int,
                 top_k: int, exclude_countries=EXCLUDE_COUNTRIES) -> Optional[dict]:
    """1 著者を評価し、条件を満たせば研究者レコードを返す。満たさなければ None。"""
    # 日本・中国系の著者は名寄せが不安定なため除外 (ヒストグラム取得前に弾いてコール節約)
    if is_excluded_author(client, author_id, name, exclude_countries):
        return None
    hist = eligible_year_histogram(client, author_id, type_filter, cutoff_year)
    if not hist:
        return None
    years = sorted(hist)
    first_year, last_year = years[0], years[-1]
    span = last_year - first_year
    n_eligible = sum(hist.values())
    # span が上限超 = 名寄せ破綻 (複数人の併合) とみなして除外
    if span < min_career_years or span > max_career_years or n_eligible < min_papers:
        return None

    tops = top_cited_eligible_works(client, author_id, type_filter, cutoff_year, top_k)
    if not tops:
        return None
    # 上位被引用論文についてのみ厳密 c10 を計算し、その argmax を「最高傑作」とみなす。
    # (最大 c10 の論文は被引用総数でも上位に来るため、上位 k 件で取りこぼしは実質起きない)
    best = None
    for w in tops:
        w["c10"] = c10_of_work(client, w["id"], w["year"], c10_window)
        if best is None or w["c10"] > best["c10"]:
            best = w
    if best is None or best["c10"] <= 0:
        return None

    t_star = best["year"] - first_year  # キャリア年次 (0 始まり)

    # 系列内での順位 i*/N (帰無モデルでは一様になるはず)。年内順は中点で平滑化。
    before = sum(hist[y] for y in years if y < best["year"])
    same = hist.get(best["year"], 0)
    rank = before + (same + 1) / 2.0
    rank_frac = rank / n_eligible

    return {
        "author_id": author_id,
        "name": name,
        "first_year": first_year,
        "last_year": last_year,
        "span": span,
        "n_eligible": n_eligible,
        "hist": hist,
        "t_star": t_star,
        "best_year": best["year"],
        "best_c10": best["c10"],
        "best_cited_total": best["cited_by_count"],
        "best_title": best.get("title"),
        "rank_frac": rank_frac,
    }


# ---------------------------------------------------------------------------
# ステップ 3: 分布の計算 (実データ vs シャッフル)
# ---------------------------------------------------------------------------
def compute_distributions(records: List[dict], repeats: int, seed: int):
    """P_real(t) と P_random(t) を返す。

    P_real(t)  : 研究者ごとに 1 つの t* を持ち、その度数分布を正規化。
    P_random(t): 各研究者で c10 をシャッフルし最大値の位置を取り直す操作のモンテカルロ。
                 シャッフル後の最大値は「一様ランダムな 1 本」に乗るので、出版年ヒスト
                 グラムに比例した一様抽選と等価 (本実装はこれを repeats 回繰り返す)。
                 各研究者の寄与重みは 1 に揃える (キャリア長によらず 1 人 1 票)。
    戻り値: (ts, p_real, p_random) いずれも長さ max_t+1 のリスト。
    """
    rng = random.Random(seed)
    max_t = max((r["span"] for r in records), default=0)

    real_counts = [0.0] * (max_t + 1)
    for r in records:
        t = r["t_star"]
        if 0 <= t <= max_t:
            real_counts[t] += 1.0

    rand_counts = [0.0] * (max_t + 1)
    for r in records:
        first = r["first_year"]
        ages, weights = [], []
        for y, c in r["hist"].items():
            a = y - first
            if 0 <= a <= max_t and c > 0:
                ages.append(a)
                weights.append(c)
        if not ages:
            continue
        # 出版年ヒストグラムに比例した重み付き抽選を repeats 回 (= c10 シャッフルと等価)
        draws = rng.choices(ages, weights=weights, k=repeats)
        for a in draws:
            rand_counts[a] += 1.0 / repeats  # 1 研究者あたり合計 1 票になる

    def _normalize(xs):
        s = sum(xs)
        return [x / s for x in xs] if s > 0 else xs

    ts = list(range(max_t + 1))
    return ts, _normalize(real_counts), _normalize(rand_counts)


def ks_statistic(p_real: List[float], p_random: List[float]) -> float:
    """2 つの離散分布の累積差の最大値 (Kolmogorov-Smirnov 統計量)。小さいほど一致。"""
    c1 = c2 = 0.0
    d = 0.0
    for a, b in zip(p_real, p_random):
        c1 += a
        c2 += b
        d = max(d, abs(c1 - c2))
    return d


def pearson(xs: List[float], ys: List[float]) -> float:
    """2 列の相関係数 (pandas/numpy 非依存の素朴実装)。"""
    n = len(xs)
    if n == 0:
        return float("nan")
    mx = sum(xs) / n
    my = sum(ys) / n
    cov = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    vx = sum((x - mx) ** 2 for x in xs)
    vy = sum((y - my) ** 2 for y in ys)
    if vx <= 0 or vy <= 0:
        return float("nan")
    return cov / (vx * vy) ** 0.5


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
        cutoff_year: int = CUTOFF_YEAR,
        c10_window: int = C10_WINDOW,
        min_career_years: int = MIN_CAREER_YEARS,
        max_career_years: int = MAX_CAREER_YEARS,
        min_papers: int = MIN_PAPERS,
        top_k: int = TOP_K,
        exclude_countries=EXCLUDE_COUNTRIES,
        repeats: int = RANDOM_REPEATS,
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
    random.Random(seed).shuffle(items)  # 上位著者への偏りを避けるため順序をシャッフル

    if verbose:
        excl = "/".join(sorted(exclude_countries)) if exclude_countries else "なし"
        print(f"[2/3] 各著者を評価 (キャリア {min_career_years}-{max_career_years}年, "
              f"論文>= {min_papers}本, 除外国={excl}) ...")
    records: List[dict] = []
    evaluated = 0
    for aid, name in items:
        if len(records) >= n_researchers or evaluated >= candidate_limit:
            break
        evaluated += 1
        try:
            rec = build_record(client, aid, name, type_filter, cutoff_year, c10_window,
                               min_career_years, max_career_years, min_papers, top_k,
                               exclude_countries)
        except RuntimeError as e:
            print(f"[warn] skip {aid}: {e}", file=sys.stderr)
            continue
        if rec:
            records.append(rec)
            if verbose and len(records) % 10 == 0:
                print(f"      kept {len(records)}/{n_researchers} (evaluated {evaluated})")
    client.save_cache()

    if verbose:
        print(f"      対象研究者 {len(records)} 名 (評価 {evaluated} 名)")
    if len(records) < 5:
        raise RuntimeError(f"研究者が {len(records)} 名しか集まりませんでした。"
                           f"candidate_limit/sample_works を増やすか条件を緩めてください。")

    if verbose:
        print("[3/3] 分布を計算 ...")
    ts, p_real, p_random = compute_distributions(records, repeats, seed)
    ks = ks_statistic(p_real, p_random)
    corr = pearson(p_real, p_random)

    stats = {
        "n_researchers": len(records),
        "n_evaluated": evaluated,
        "ks": ks,
        "pearson": corr,
        "mean_t_star": sum(r["t_star"] for r in records) / len(records),
        "mean_span": sum(r["span"] for r in records) / len(records),
        "cutoff_year": cutoff_year,
        "c10_window": c10_window,
    }
    return {"records": records, "ts": ts, "p_real": p_real, "p_random": p_random,
            "stats": stats}


# ---------------------------------------------------------------------------
# 可視化・保存
# ---------------------------------------------------------------------------
def make_figure(results: dict):
    """結果から 2 パネル図を作って Figure を返す (notebook では inline 表示用)。

    matplotlib は標準ライブラリ外。日本語フォント未設定環境での豆腐化を避けるため軸ラベル
    は英語にする。左: P(t) の実データ vs シャッフル。右: 系列内順位 i*/N の分布 (一様参照)。
    """
    import matplotlib
    if matplotlib.get_backend().lower() == "agg":
        pass  # CLI からは Agg のまま保存
    import matplotlib.pyplot as plt

    ts = results["ts"]
    p_real = results["p_real"]
    p_random = results["p_random"]
    records = results["records"]
    st = results["stats"]

    fig, axes = plt.subplots(1, 2, figsize=(12, 5))

    ax = axes[0]
    ax.plot(ts, p_real, "o-", color="#c0392b", label="Real (data)")
    ax.plot(ts, p_random, "s--", color="#2c3e50", label=r"Randomized (shuffled $c_{10}$)")
    ax.set_xlabel("Career age $t^*$ of highest-impact paper (years)")
    ax.set_ylabel(r"$P(t^*)$")
    ax.set_title("Random impact rule: timing of the biggest hit")
    ax.legend()

    # 右パネル: 系列内での相対位置 i*/N。ランダム・インパクト・ルールなら一様 (密度 1)。
    ax2 = axes[1]
    fracs = [r["rank_frac"] for r in records]
    ax2.hist(fracs, bins=10, range=(0, 1), density=True, color="#c0392b", alpha=0.7,
             edgecolor="white", label="Real")
    ax2.axhline(1.0, color="#2c3e50", ls="--", label="Uniform (random rule)")
    ax2.set_xlabel(r"Relative position of biggest hit in sequence ($i^*/N$)")
    ax2.set_ylabel("Probability density")
    ax2.set_title("Position of biggest hit among a scientist's papers")
    ax2.set_ylim(bottom=0)
    ax2.legend()

    fig.suptitle(f"N = {st['n_researchers']} scientists, career >= {MIN_CAREER_YEARS} yrs "
                 f"(OpenAlex; c10 window = {st['c10_window']}y, cutoff <= {st['cutoff_year']})")
    fig.tight_layout()
    return fig


def save_outputs(results: dict, out_prefix: str) -> None:
    """図 (PNG)・研究者一覧 (CSV)・分布 (CSV) を保存する。"""
    import matplotlib
    matplotlib.use("Agg")
    fig = make_figure(results)
    png = out_prefix + ".png"
    fig.savefig(png, dpi=150)
    print(f"  saved figure : {png}")

    # 研究者ごとのレコード
    rec_csv = out_prefix + "_researchers.csv"
    cols = ["author_id", "name", "first_year", "last_year", "span", "n_eligible",
            "t_star", "best_year", "best_c10", "best_cited_total", "rank_frac", "best_title"]
    with open(rec_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for r in results["records"]:
            w.writerow(r)
    print(f"  saved records: {rec_csv}")

    # 分布
    dist_csv = out_prefix + "_distribution.csv"
    with open(dist_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["t", "p_real", "p_random"])
        for t, a, b in zip(results["ts"], results["p_real"], results["p_random"]):
            w.writerow([t, a, b])
    print(f"  saved dist   : {dist_csv}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def parse_args(argv=None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Reproduce the random impact rule with OpenAlex.")
    p.add_argument("--mailto", default=DEFAULT_MAILTO, help="polite pool 用メールアドレス")
    p.add_argument("--field", default=FIELD_FILTER,
                   help="works フィルタ片 (例 concepts.id:C121332964)。'none' で全分野")
    p.add_argument("--type", dest="type_filter", default=TYPE_FILTER,
                   help="works 種別フィルタ (例 type:article)。'none' で全種別")
    p.add_argument("--era-start", default=SEED_ERA[0])
    p.add_argument("--era-end", default=SEED_ERA[1])
    p.add_argument("--sample-works", type=int, default=SAMPLE_WORKS)
    p.add_argument("--candidate-limit", type=int, default=CANDIDATE_LIMIT)
    p.add_argument("--n-researchers", type=int, default=N_RESEARCHERS)
    p.add_argument("--cutoff-year", type=int, default=CUTOFF_YEAR)
    p.add_argument("--c10-window", type=int, default=C10_WINDOW)
    p.add_argument("--min-career-years", type=int, default=MIN_CAREER_YEARS)
    p.add_argument("--max-career-years", type=int, default=MAX_CAREER_YEARS,
                   help="これを超えるキャリア長は名寄せ破綻として除外")
    p.add_argument("--include-jp-cn", action="store_true",
                   help="既定では除外する日本・中国系の著者を含める")
    p.add_argument("--min-papers", type=int, default=MIN_PAPERS)
    p.add_argument("--top-k", type=int, default=TOP_K)
    p.add_argument("--repeats", type=int, default=RANDOM_REPEATS)
    p.add_argument("--seed", type=int, default=RNG_SEED)
    p.add_argument("--out", default="openalex_random_impact_rule", help="出力ファイルの接頭辞")
    p.add_argument("--cache", default=DEFAULT_CACHE)
    p.add_argument("--no-cache", action="store_true")
    p.add_argument("--smoke", action="store_true", help="少数で素早く配管確認する")
    return p.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)
    field = None if str(args.field).lower() == "none" else args.field
    type_filter = None if str(args.type_filter).lower() == "none" else args.type_filter

    if args.smoke:  # 配管確認用の最小設定
        args.sample_works = min(args.sample_works, 200)
        args.candidate_limit = min(args.candidate_limit, 60)
        args.n_researchers = min(args.n_researchers, 8)

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

    exclude_countries = set() if args.include_jp_cn else EXCLUDE_COUNTRIES
    results = run(client, field_filter=field, type_filter=type_filter,
                  era=(args.era_start, args.era_end), sample_works=args.sample_works,
                  candidate_limit=args.candidate_limit, n_researchers=args.n_researchers,
                  cutoff_year=args.cutoff_year, c10_window=args.c10_window,
                  min_career_years=args.min_career_years, max_career_years=args.max_career_years,
                  min_papers=args.min_papers, exclude_countries=exclude_countries,
                  top_k=args.top_k, repeats=args.repeats, seed=args.seed)
    client.save_cache()

    st = results["stats"]
    print("\n=== 結果サマリ ===")
    print(f"  研究者数 N          : {st['n_researchers']}")
    print(f"  平均キャリア長       : {st['mean_span']:.1f} 年")
    print(f"  平均 t* (最高傑作位置): {st['mean_t_star']:.1f} 年目")
    print(f"  KS 統計量(実 vs ランダム): {st['ks']:.4f}  (小さいほど一致)")
    print(f"  Pearson 相関(P(t))   : {st['pearson']:.4f}  (1 に近いほど一致)")
    print("  → KS が小さく相関が高いほど『最高傑作の位置はランダム』を支持する。\n")

    save_outputs(results, args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
