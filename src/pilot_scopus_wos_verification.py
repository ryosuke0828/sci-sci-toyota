"""トラックA フェーズ5: toyota_authors.csv の所属主張を Scopus + WoS で照合する100名パイロット。

入力: toyota_data/toyota_authors.csv (9,429名, OpenAlex由来)
出力: data/derived/pilot_scopus_wos/
  - sample_selection.csv   … 層化サンプリングした100名
  - scopus_candidates.csv  … Scopus Author Search の候補（1名につき複数行）
  - wos_results.csv        … WoS の AU= / AU=×OG= のヒット件数
  - verdicts.csv           … 1名1行の最終判定と OpenAlex 主張との一致
  - api_call_log.csv       … 全API呼び出しの記録（クォータ見積もり用）
  - run_summary.json

設計上の反映事項（2026-07-27 Scopus探索・2026-08-03 WoS検証の知見）:
  - Scopus Author Search は AUTHOR-NAME() 不可。AUTHLASTNAME()/AUTHFIRST() を分ける
  - AF-ID() 厳密一致は取りこぼしが大きいので AFFIL() 自由文字列を使う
  - 上位1候補だけでは不十分なので候補は最大5件保持して評価する
  - OpenAlex の name は姓名の順序が不定 → 0件なら入れ替えて再試行
  - WoS は所属フィールドを返さないので OG= の複合クエリで間接判定する
  - WoS の OG= は表記ゆれを統合しないので OR 結合が必須

実行: ~/.venvs/scisci-rir/bin/python src/pilot_scopus_wos_verification.py
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parent.parent
IN_CSV = ROOT / "toyota_data" / "toyota_authors.csv"
OUT_DIR = ROOT / "data" / "derived" / "pilot_scopus_wos"

SCOPUS_KEY = os.environ.get("SCOPUS_API_KEY")
WOS_KEY = os.environ.get("WOS_API_KEY")
if not SCOPUS_KEY or not WOS_KEY:
    raise SystemExit("SCOPUS_API_KEY / WOS_API_KEY が環境変数にありません")

SCOPUS_AUTHOR = "https://api.elsevier.com/content/search/author"
WOS_DOCS = "https://api.clarivate.com/apis/wos-starter/v1/documents"

SEED = 20260803
N_NOISE, N_SWISS, N_OTHER = 30, 35, 35

# WoS の OG= は表記ゆれを統合しないので OR 結合する（2026-08-03 検証済み）
OG_MOTOR = '(OG="Toyota Motor Corporation" OR OG="Toyota Motor Co Ltd")'
OG_GROUP = ('(OG="Toyota Motor Corporation" OR OG="Toyota Motor Co Ltd" '
            'OR OG="Toyota Central R&D Labs Inc" OR OG="IMRA America Inc" '
            'OR OG="IMRA Europe" OR OG="Aisin Seiki")')

TOYOTA_TOKENS = ("toyota", "imra", "aisin", "denso")

call_log: list[dict] = []


def scopus_get(query: str, label: str) -> dict | None:
    time.sleep(0.3)
    t0 = time.time()
    try:
        r = requests.get(SCOPUS_AUTHOR,
                         headers={"X-ELS-APIKey": SCOPUS_KEY, "Accept": "application/json"},
                         params={"query": query, "count": 5}, timeout=40)
    except requests.RequestException as e:
        call_log.append({"api": "scopus", "label": label, "query": query,
                         "status": f"EXC:{type(e).__name__}", "ms": None})
        return None
    call_log.append({"api": "scopus", "label": label, "query": query,
                     "status": r.status_code, "ms": int((time.time() - t0) * 1000)})
    return r.json() if r.status_code == 200 else None


def wos_count(query: str, label: str) -> int | None:
    for attempt in range(3):
        time.sleep(0.35)
        t0 = time.time()
        try:
            r = requests.get(WOS_DOCS,
                             headers={"X-ApiKey": WOS_KEY, "Accept": "application/json"},
                             params={"q": query, "limit": 1}, timeout=40)
        except requests.RequestException as e:
            call_log.append({"api": "wos", "label": label, "query": query,
                             "status": f"EXC:{type(e).__name__}", "ms": None})
            time.sleep(2)
            continue
        call_log.append({"api": "wos", "label": label, "query": query,
                         "status": r.status_code, "ms": int((time.time() - t0) * 1000)})
        if r.status_code == 200:
            return r.json().get("metadata", {}).get("total")
        if r.status_code == 429:
            time.sleep(3 * (attempt + 1))
            continue
        return None
    return None


def split_name(full: str) -> tuple[str, str]:
    """OpenAlex の name を (given, family) に割る。末尾トークンを姓とみなす素朴な分割。"""
    parts = [p for p in str(full).replace(",", " ").split() if p]
    if len(parts) == 0:
        return "", ""
    if len(parts) == 1:
        return "", parts[0]
    return " ".join(parts[:-1]), parts[-1]


def looks_toyota(text: str | None) -> bool:
    return bool(text) and any(t in str(text).lower() for t in TOYOTA_TOKENS)


def build_sample(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["career_years"] = df["last_pub_year"] - df["first_pub_year"]
    is_noise = (df["first_pub_year"] < 1960) | (df["career_years"] > 60)
    is_swiss = df["entity_motor_corporation_switzerland"] == True   # noqa: E712
    is_cur = df["is_currently_affiliated"] == True                  # noqa: E712

    strata = {
        # 名寄せ破綻が疑われる層。OpenAlex の主張が誤りである可能性が高い
        "known_noise": df[is_noise],
        # スイス法人への誤帰属バグ（README §3-1）の検証層
        "current_swiss": df[~is_noise & is_cur & is_swiss],
        # 対照群
        "current_other": df[~is_noise & is_cur & ~is_swiss],
    }
    sizes = {"known_noise": N_NOISE, "current_swiss": N_SWISS, "current_other": N_OTHER}
    out = []
    for name, sub in strata.items():
        n = min(sizes[name], len(sub))
        s = sub.sample(n=n, random_state=SEED).copy()
        s["sample_group"] = name
        out.append(s)
        print(f"  層 {name}: 母集団{len(sub)}名 → {n}名抽出", flush=True)
    return pd.concat(out, ignore_index=True)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    df = pd.read_csv(IN_CSV)
    print(f"入力 {len(df)}名。層化サンプリング（seed={SEED}）:", flush=True)
    sample = build_sample(df)
    sample.to_csv(OUT_DIR / "sample_selection.csv", index=False)
    print(f"合計 {len(sample)}名\n", flush=True)

    cand_rows, wos_rows, verdicts = [], [], []

    for i, (_, row) in enumerate(sample.iterrows(), 1):
        name = str(row["name"])
        given, family = split_name(name)
        print(f"[{i}/{len(sample)}] {name} ({row['sample_group']})", flush=True)

        # ---- Scopus: 姓名の順序ゆれに対応しつつ Author Search ----
        scopus_entries, used_order = [], None
        for order, (fam, giv) in enumerate([(family, given), (given, family)]):
            if not fam:
                continue
            q = f"AUTHLASTNAME({fam})" + (f" AND AUTHFIRST({giv})" if giv else "")
            data = scopus_get(q, f"author_search_order{order}")
            entries = ((data or {}).get("search-results", {}).get("entry") or [])
            entries = [e for e in entries if "error" not in e]
            if entries:
                scopus_entries, used_order = entries, order
                break

        scopus_toyota_hit, scopus_best_affil = False, None
        for e in scopus_entries:
            affil = (e.get("affiliation-current") or {})
            affil_name = affil.get("affiliation-name")
            is_toy = looks_toyota(affil_name)
            scopus_toyota_hit = scopus_toyota_hit or is_toy
            if scopus_best_affil is None or (is_toy and not looks_toyota(scopus_best_affil)):
                scopus_best_affil = affil_name
            cand_rows.append({
                "openalex_id": row["openalex_id"], "name": name,
                "sample_group": row["sample_group"],
                "scopus_author_id": e.get("dc:identifier"),
                "scopus_name": ((e.get("preferred-name") or {}).get("surname", "") + ", "
                                + (e.get("preferred-name") or {}).get("given-name", "")),
                "affiliation_current": affil_name,
                "affiliation_country": affil.get("affiliation-country"),
                "document_count": e.get("document-count"),
                "is_toyota_affiliation": is_toy,
                "name_order_used": used_order,
            })

        # AFFIL() 自由文字列での広域確認（AF-ID より取りこぼしが少ない）
        affil_q = f"AUTHLASTNAME({family}) AND AFFIL(Toyota)" if family else None
        affil_total = None
        if affil_q:
            d = scopus_get(affil_q, "author_search_affil")
            try:
                affil_total = int((d or {}).get("search-results", {})
                                  .get("opensearch:totalResults", 0))
            except (TypeError, ValueError):
                affil_total = None

        # ---- WoS: AU= 単独 / AU= × OG=（所属の間接証拠） ----
        wos_name = f"{family}, {given}".strip(", ") if family else name
        n_all = wos_count(f'AU="{wos_name}"', "au_only")
        n_motor = wos_count(f'AU="{wos_name}" AND {OG_MOTOR}', "au_x_motor")
        n_group = wos_count(f'AU="{wos_name}" AND {OG_GROUP}', "au_x_group")
        wos_rows.append({
            "openalex_id": row["openalex_id"], "name": name, "wos_query_name": wos_name,
            "sample_group": row["sample_group"],
            "wos_hits_name_only": n_all, "wos_hits_toyota_motor": n_motor,
            "wos_hits_toyota_group": n_group,
        })

        # ---- 判定 ----
        wos_supports = bool(n_motor and n_motor > 0)
        wos_group_supports = bool(n_group and n_group > 0)
        if scopus_toyota_hit and wos_supports:
            verdict = "confirmed_both"
        elif scopus_toyota_hit or wos_supports:
            verdict = "confirmed_one"
        elif wos_group_supports:
            verdict = "group_only"       # トヨタ本体でなくグループ企業でヒット
        elif not scopus_entries and not n_all:
            verdict = "not_found"        # 両DBに候補なし。ノイズ確定ではない
        else:
            verdict = "contradicted"     # 候補はあるがトヨタ所属の証拠なし
        verdicts.append({
            "openalex_id": row["openalex_id"], "name": name,
            "sample_group": row["sample_group"],
            "openalex_is_currently_affiliated": row["is_currently_affiliated"],
            "openalex_matched_entities": row["matched_entities"],
            "openalex_works_count": row["works_count"],
            "openalex_first_pub_year": row["first_pub_year"],
            "openalex_career_years": row["last_pub_year"] - row["first_pub_year"],
            "n_scopus_candidates": len(scopus_entries),
            "scopus_toyota_hit": scopus_toyota_hit,
            "scopus_best_affiliation": scopus_best_affil,
            "scopus_affil_query_total": affil_total,
            "wos_hits_name_only": n_all, "wos_hits_toyota_motor": n_motor,
            "wos_hits_toyota_group": n_group,
            "verdict": verdict,
        })
        print(f"      → {verdict} (scopus候補{len(scopus_entries)}/toyota={scopus_toyota_hit}, "
              f"wos {n_all}/{n_motor}/{n_group})", flush=True)

    cand_df = pd.DataFrame(cand_rows)
    wos_df = pd.DataFrame(wos_rows)
    ver_df = pd.DataFrame(verdicts)
    log_df = pd.DataFrame(call_log)
    cand_df.to_csv(OUT_DIR / "scopus_candidates.csv", index=False)
    wos_df.to_csv(OUT_DIR / "wos_results.csv", index=False)
    ver_df.to_csv(OUT_DIR / "verdicts.csv", index=False)
    log_df.to_csv(OUT_DIR / "api_call_log.csv", index=False)

    cross = pd.crosstab(ver_df["sample_group"], ver_df["verdict"])
    summary = {
        "seed": SEED, "n_sampled": int(len(ver_df)),
        "verdict_counts": ver_df["verdict"].value_counts().to_dict(),
        "verdict_by_group": json.loads(cross.to_json(orient="index")),
        "scopus_toyota_hit_rate_pct": round(ver_df["scopus_toyota_hit"].mean() * 100, 1),
        "wos_motor_hit_rate_pct": round(
            (ver_df["wos_hits_toyota_motor"].fillna(0) > 0).mean() * 100, 1),
        "api_calls": log_df.groupby("api").size().to_dict(),
        "api_errors": int((log_df["status"] != 200).sum()),
        "median_ms": log_df.groupby("api")["ms"].median().round().to_dict(),
    }
    (OUT_DIR / "run_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    print("\n===== サマリ =====", flush=True)
    print(json.dumps(summary, ensure_ascii=False, indent=2), flush=True)
    print("\n===== 層 × 判定 =====", flush=True)
    print(cross.to_string(), flush=True)


if __name__ == "__main__":
    main()
