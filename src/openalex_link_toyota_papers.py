"""Phase 4: トヨタ関連公式サイトのスクレイピング結果を OpenAlex Work ID に紐付ける。

入力: data/derived/toyota_official_scrape/combined_papers.csv (919件)
出力: data/derived/openalex_linking/
  - openalex_links.csv       … 1論文1行。OpenAlex ID・マッチ手法・スコア・要目視フラグ
  - openalex_works_meta.csv  … 紐付いた Work のメタデータ（Phase 5 の指標計算の入力）
  - unmatched.csv            … 紐付かなかった論文
  - run_summary.json         … 実行サマリ

方針（今井先生の指示「文字列一致だけでは誤同定があるため目視確認が必要」を反映）:
  - DOI がある論文は DOI 完全一致（誤同定の余地がないので自動採用）
  - DOI がない論文はタイトル検索 + 正規化タイトルの類似度で判定し、
    スコアに応じて auto / review / no_match の3段階に振り分ける
    （review 以下は人手確認に回す想定。自動で確定させない）

実行: ~/.venvs/scisci-rir/bin/python src/openalex_link_toyota_papers.py
"""
from __future__ import annotations

import json
import os
import re
import time
import unicodedata
from difflib import SequenceMatcher
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parent.parent

# 自動実行（launchd）は Google Drive 配下を読めない（macOS のプライバシー保護により
# `Operation not permitted` になる）。そのため ~/scisci-auto/ など Drive 外の
# 作業ディレクトリでも動くよう、入出力パスを環境変数で差し替えられるようにしてある。
# 環境変数を設定しなければ従来どおり Drive 上のリポジトリ内で完結する。
IN_CSV = Path(os.environ.get(
    "SCISCI_INPUT_CSV",
    ROOT / "data" / "derived" / "toyota_official_scrape" / "combined_papers.csv"))
OUT_DIR = Path(os.environ.get(
    "SCISCI_OUT_DIR", ROOT / "data" / "derived" / "openalex_linking"))

API = "https://api.openalex.org/works"
MAILTO = "ikuraryosuke@gmail.com"  # polite pool（10 req/秒・100k/日）
SESSION = requests.Session()
SESSION.headers.update({"User-Agent": f"scisci-toyota-linking (mailto:{MAILTO})"})

SELECT = ",".join([
    "id", "doi", "title", "publication_year", "type", "cited_by_count",
    "referenced_works_count", "authorships", "primary_topic", "topics",
    "primary_location", "institutions_distinct_count",
])

# タイトル類似度のしきい値。0.95以上は自動採用、0.80以上は要目視、それ未満は不一致扱い。
AUTO_THRESHOLD = 0.95
REVIEW_THRESHOLD = 0.80

DOI_CHUNK = 50  # OpenAlex の OR フィルタ上限


def normalize_doi(raw) -> str | None:
    if raw is None or (isinstance(raw, float) and pd.isna(raw)):
        return None
    s = str(raw).strip()
    if not s or s.lower() == "nan":
        return None
    s = re.sub(r"^https?://(dx\.)?doi\.org/", "", s, flags=re.I)
    s = s.strip().rstrip(".")
    return s.lower() if s.startswith("10.") else None


def normalize_title(raw) -> str:
    if raw is None or (isinstance(raw, float) and pd.isna(raw)):
        return ""
    s = unicodedata.normalize("NFKC", str(raw)).lower()
    s = re.sub(r"[^0-9a-z぀-ヿ一-鿿]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def clean_for_search(raw: str) -> str:
    """OpenAlex の title.search / search に安全に渡せる文字列にする。

    カンマはフィルタ区切りとして解釈され、`*` `?` はワイルドカード扱いで
    stemmed フィールドでは 400 になる。コロン・パイプ等もフィールド指定として
    誤解釈されるため、英数字・空白・CJK 以外はすべて空白に落とす。
    """
    s = unicodedata.normalize("NFKC", str(raw))
    s = re.sub(r"[^0-9A-Za-z぀-ヿ一-鿿\s]", " ", s)
    return re.sub(r"\s+", " ", s).strip()[:300]


class BudgetExhausted(RuntimeError):
    """OpenAlex の1日あたり無料枠（$0.1 / 1,000リクエスト）を使い切った。"""


CACHE_PATH = Path(os.environ.get(
    "SCISCI_CACHE_PATH", ROOT / "data" / "cache" / "openalex_linking_cache.json"))
_cache: dict[str, dict] = {}
_cache_dirty = 0


def load_cache() -> None:
    global _cache
    if CACHE_PATH.exists():
        _cache = json.loads(CACHE_PATH.read_text(encoding="utf-8"))
        print(f"キャッシュ読み込み: {len(_cache)}件", flush=True)


def save_cache() -> None:
    global _cache_dirty
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    CACHE_PATH.write_text(json.dumps(_cache, ensure_ascii=False), encoding="utf-8")
    _cache_dirty = 0


def get(params: dict, retries: int = 3) -> dict | None:
    """OpenAlex に問い合わせる。結果はディスクにキャッシュして再実行時のクォータ消費を防ぐ。

    無料枠は1日1,000リクエスト（UTC深夜リセット）しかないため、
    使い切ったら例外を投げて即座に中断し、それまでの結果を保存する。
    """
    global _cache_dirty
    key = json.dumps(params, sort_keys=True, ensure_ascii=False)
    if key in _cache:
        return _cache[key]

    req = {**params, "mailto": MAILTO}
    for attempt in range(retries):
        time.sleep(0.15)
        try:
            r = SESSION.get(API, params=req, timeout=45)
        except requests.RequestException as e:
            print(f"    例外 {type(e).__name__}: {e} (retry {attempt+1})", flush=True)
            time.sleep(2 * (attempt + 1))
            continue
        if r.status_code == 200:
            data = r.json()
            _cache[key] = data
            _cache_dirty += 1
            if _cache_dirty >= 25:
                save_cache()
            return data
        if r.status_code == 429:
            # 一時的なスロットリングか、1日の予算切れかを区別する
            if r.headers.get("X-RateLimit-Remaining") == "0":
                raise BudgetExhausted(
                    f"OpenAlex の1日の無料枠を使い切りました。"
                    f"リセットまで約{int(r.headers.get('Retry-After', 0)) // 3600}時間。"
                    f"応答: {r.text[:200]}")
            time.sleep(3 * (attempt + 1))
            continue
        if r.status_code in (500, 502, 503):
            time.sleep(3 * (attempt + 1))
            continue
        if r.status_code == 404:
            return None
        print(f"    HTTP {r.status_code}: {r.text[:200]}", flush=True)
        return None
    print(f"    リトライ上限: {params}", flush=True)
    return None


def flatten_work(w: dict) -> dict:
    """Phase 5 で使う形にフラット化する。"""
    auths = w.get("authorships") or []
    insts, countries = [], []
    for a in auths:
        for inst in a.get("institutions") or []:
            if inst.get("display_name"):
                insts.append(inst["display_name"])
            if inst.get("country_code"):
                countries.append(inst["country_code"])
    topic = w.get("primary_topic") or {}
    loc = w.get("primary_location") or {}
    src = (loc.get("source") or {}) if isinstance(loc, dict) else {}
    return {
        "openalex_id": w.get("id"),
        "openalex_doi": w.get("doi"),
        "openalex_title": w.get("title"),
        "publication_year": w.get("publication_year"),
        "type": w.get("type"),
        "cited_by_count": w.get("cited_by_count"),
        "referenced_works_count": w.get("referenced_works_count"),
        "n_authors": len(auths),
        "authors": "; ".join(
            (a.get("author") or {}).get("display_name") or "" for a in auths),
        "author_openalex_ids": "; ".join(
            (a.get("author") or {}).get("id") or "" for a in auths),
        "institutions": "; ".join(dict.fromkeys(insts)),
        "institution_countries": "; ".join(dict.fromkeys(countries)),
        "institutions_distinct_count": w.get("institutions_distinct_count"),
        "primary_topic": topic.get("display_name"),
        "primary_subfield": ((topic.get("subfield") or {}).get("display_name")),
        "primary_field": ((topic.get("field") or {}).get("display_name")),
        "primary_domain": ((topic.get("domain") or {}).get("display_name")),
        "venue_openalex": src.get("display_name"),
    }


def resolve(df: pd.DataFrame, results: dict[int, dict],
            works_by_id: dict[str, dict]) -> None:
    """OpenAlex への問い合わせ本体。予算切れなら BudgetExhausted を投げる。"""
    # ---- (1) DOI 完全一致（50件ずつまとめて問い合わせ） ----
    doi_rows = df[df["doi_norm"].notna()]
    unique_dois = sorted(set(doi_rows["doi_norm"]))
    print(f"\n[1] DOI一致: ユニークDOI {len(unique_dois)}件を"
          f"{-(-len(unique_dois)//DOI_CHUNK)}バッチで問い合わせ", flush=True)
    doi_to_work: dict[str, dict] = {}
    for i in range(0, len(unique_dois), DOI_CHUNK):
        chunk = unique_dois[i:i + DOI_CHUNK]
        data = get({"filter": "doi:" + "|".join(chunk),
                    "per-page": DOI_CHUNK, "select": SELECT})
        found = 0
        for w in (data or {}).get("results", []):
            d = normalize_doi(w.get("doi"))
            if d:
                doi_to_work[d] = w
                found += 1
        flag = "  ← 要再取得" if found == 0 else ""
        print(f"    バッチ{i//DOI_CHUNK+1}: {len(chunk)}件中 {found}件ヒット{flag}", flush=True)

    # バッチが丸ごと失敗する（レート制限等）ことがあるので、取りこぼしを個別に拾い直す。
    missing = [d for d in unique_dois if d not in doi_to_work]
    if missing:
        print(f"    バッチで取れなかった {len(missing)}件を個別に再取得", flush=True)
        recovered = 0
        for d in missing:
            data = get({"filter": f"doi:{d}", "per-page": 1, "select": SELECT})
            for w in (data or {}).get("results", []):
                nd = normalize_doi(w.get("doi"))
                if nd:
                    doi_to_work[nd] = w
                    recovered += 1
        print(f"    → 個別再取得で {recovered}件 回収", flush=True)

    for _, row in doi_rows.iterrows():
        w = doi_to_work.get(row["doi_norm"])
        if w is None:
            continue
        works_by_id[w["id"]] = w
        results[row["row_id"]] = {
            "openalex_id": w["id"], "match_method": "doi_exact",
            "match_score": 1.0, "review_status": "auto",
            "matched_title": w.get("title"),
        }
    print(f"    → DOI一致で {len(results)}件を確定", flush=True)

    # ---- (2) タイトル検索によるファジーマッチ ----
    rest = df[~df["row_id"].isin(results)]
    rest = rest[rest["title_norm"].str.len() > 0]
    print(f"\n[2] タイトル照合: {len(rest)}件", flush=True)
    for n, (_, row) in enumerate(rest.iterrows(), 1):
        if n % 25 == 0:
            print(f"    {n}/{len(rest)} ...", flush=True)
        title = str(row["title"]).strip()
        cleaned = clean_for_search(title)
        if not cleaned:
            continue
        data = get({"filter": f"title.search:{cleaned}", "per-page": 10, "select": SELECT})
        cands = (data or {}).get("results", [])
        if not cands:
            data = get({"search": cleaned, "per-page": 10, "select": SELECT})
            cands = (data or {}).get("results", [])
        best, best_score = None, 0.0
        for w in cands:
            score = SequenceMatcher(
                None, row["title_norm"], normalize_title(w.get("title"))).ratio()
            if score > best_score:
                best, best_score = w, score
        if best is None:
            continue
        if best_score >= AUTO_THRESHOLD:
            status = "auto"
        elif best_score >= REVIEW_THRESHOLD:
            status = "review"
        else:
            status = "no_match"
        if status == "no_match":
            continue
        works_by_id[best["id"]] = best
        results[row["row_id"]] = {
            "openalex_id": best["id"], "match_method": "title_fuzzy",
            "match_score": round(best_score, 4), "review_status": status,
            "matched_title": best.get("title"),
        }


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    load_cache()
    df = pd.read_csv(IN_CSV)
    df["row_id"] = range(len(df))
    df["doi_norm"] = df["doi"].map(normalize_doi)
    df["title_norm"] = df["title"].map(normalize_title)
    print(f"入力 {len(df)}件 / DOI正規化後あり {df['doi_norm'].notna().sum()}件", flush=True)
    print(df["source_org"].value_counts().to_string(), flush=True)

    results: dict[int, dict] = {}
    works_by_id: dict[str, dict] = {}
    complete = True
    try:
        resolve(df, results, works_by_id)
    except BudgetExhausted as e:
        complete = False
        print(f"\n!! 中断: {e}", flush=True)
        print("!! ここまでの結果を保存します。翌日リセット後に再実行すれば"
              "キャッシュ済み分はクォータを消費せず、続きから進みます。", flush=True)
    except KeyboardInterrupt:
        complete = False
        print("\n!! 中断（Ctrl-C）。ここまでの結果を保存します。", flush=True)
    finally:
        save_cache()

    # ---- (3) 出力 ----
    link_df = df.drop(columns=["title_norm"]).copy()
    for col in ["openalex_id", "match_method", "match_score",
                "review_status", "matched_title"]:
        link_df[col] = link_df["row_id"].map(
            lambda r, c=col: results.get(r, {}).get(c))
    link_df["matched"] = link_df["openalex_id"].notna()

    meta_df = pd.DataFrame([flatten_work(w) for w in works_by_id.values()])

    link_path = OUT_DIR / "openalex_links.csv"
    meta_path = OUT_DIR / "openalex_works_meta.csv"
    unmatched_path = OUT_DIR / "unmatched.csv"
    link_df.to_csv(link_path, index=False)
    meta_df.to_csv(meta_path, index=False)
    link_df[~link_df["matched"]].to_csv(unmatched_path, index=False)

    by_src = link_df.groupby("source_org")["matched"].agg(["size", "sum"])
    by_src["rate"] = (by_src["sum"] / by_src["size"] * 100).round(1)
    summary = {
        "complete": complete,
        "input_rows": int(len(df)),
        "matched": int(link_df["matched"].sum()),
        "match_rate_pct": round(link_df["matched"].mean() * 100, 1),
        "by_method": link_df["match_method"].value_counts().to_dict(),
        "by_review_status": link_df["review_status"].value_counts().to_dict(),
        "by_source_org": {
            k: {"total": int(v["size"]), "matched": int(v["sum"]),
                "rate_pct": float(v["rate"])}
            for k, v in by_src.iterrows()},
        "unique_openalex_works": int(len(meta_df)),
        "duplicate_openalex_ids": int(
            link_df["openalex_id"].notna().sum() - len(meta_df)),
    }
    (OUT_DIR / "run_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    print("\n===== サマリ =====", flush=True)
    print(json.dumps(summary, ensure_ascii=False, indent=2), flush=True)
    print(f"\n出力: {link_path}\n      {meta_path}\n      {unmatched_path}", flush=True)


if __name__ == "__main__":
    main()
