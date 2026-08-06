"""WoS の組織フィルタ(OG=)で、指定組織の論文を全件回収する。

用途:
  - AISIN IMRA欧州版(imra.eu)は一覧ページがなくスクレイピングの工数が大きい。
    WoS上に OG="IMRA Europe" で25件あることを確認済みなので、
    公式サイトを叩く代わりにWoSから回収して穴を埋める。
  - 同じ仕組みで他のトヨタ系組織の論文も回収でき、
    公式サイトの掲載漏れ（サイトに載っていない論文）の検出にも使える。

注意: WoS Starter のレスポンスには所属フィールドがないため、
      「この著者がその組織所属である」ことは直接は分からない。
      分かるのは「この論文の著者の誰かがその組織に所属している」ことだけ。

出力: data/derived/wos_org_harvest/
  - wos_org_papers.csv   … 1論文1行
  - wos_org_authors.csv  … 1論文1著者1行（ResearcherIDつき）
  - wos_org_summary.json

実行: ~/.venvs/scisci-rir/bin/python src/wos_harvest_org.py
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "data" / "derived" / "wos_org_harvest"
BASE = "https://api.clarivate.com/apis/wos-starter/v1/documents"

KEY = os.environ.get("WOS_API_KEY")
if not KEY:
    raise SystemExit("WOS_API_KEY が環境変数にありません")
HEADERS = {"X-ApiKey": KEY, "Accept": "application/json"}

# 2026-08-03 の機能検証で件数を確認済みの正式表記。
# OG= は表記ゆれを統合しないので、同じ組織の別表記は個別に指定する必要がある。
TARGET_ORGS = {
    "IMRA Europe": 'OG="IMRA Europe"',
    "IMRA America Inc": 'OG="IMRA America Inc"',
    "Aisin Seiki": 'OG="Aisin Seiki"',
}

PAGE_SIZE = 50  # WoS Starter の limit 上限


def wos_page(q: str, page: int) -> dict | None:
    for attempt in range(4):
        time.sleep(0.35)  # 5 req/秒 制限
        try:
            r = requests.get(BASE, headers=HEADERS,
                             params={"q": q, "limit": PAGE_SIZE, "page": page},
                             timeout=40)
        except requests.RequestException as e:
            print(f"    例外 {type(e).__name__} (retry {attempt+1})", flush=True)
            time.sleep(2 * (attempt + 1))
            continue
        if r.status_code == 200:
            return r.json()
        if r.status_code == 429:
            time.sleep(3 * (attempt + 1))
            continue
        print(f"    HTTP {r.status_code}: {r.text[:200]}", flush=True)
        return None
    return None


def harvest(label: str, q: str) -> tuple[list[dict], list[dict]]:
    papers, authors = [], []
    page = 1
    total = None
    while True:
        data = wos_page(q, page)
        if data is None:
            break
        if total is None:
            total = data.get("metadata", {}).get("total")
            print(f"  [{label}] 全{total}件", flush=True)
        hits = data.get("hits", [])
        if not hits:
            break
        for h in hits:
            ids = h.get("identifiers") or {}
            src = h.get("source") or {}
            cites = h.get("citations") or []
            wos_count = next((c.get("count") for c in cites
                              if c.get("db") == "WOS"), None)
            papers.append({
                "org": label,
                "wos_uid": h.get("uid"),
                "title": h.get("title"),
                "doi": (ids.get("doi") or "").lower() or None,
                "venue": src.get("sourceTitle"),
                "year": src.get("publishYear"),
                "type": "; ".join(h.get("types") or []),
                "wos_cited_by_count": wos_count,
            })
            for pos, a in enumerate(
                    ((h.get("names") or {}).get("authors") or []), 1):
                authors.append({
                    "org": label,
                    "wos_uid": h.get("uid"),
                    "author_position": pos,
                    "display_name": a.get("displayName"),
                    "wos_standard": a.get("wosStandard"),
                    "researcher_id": a.get("researcherId"),
                })
        if len(papers) >= (total or 0):
            break
        page += 1
        if page > 60:  # 安全弁
            print("    ページ上限に到達。打ち切ります。", flush=True)
            break
    return papers, authors


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    all_papers, all_authors = [], []
    for label, q in TARGET_ORGS.items():
        print(f"\n=== {label} ===", flush=True)
        p, a = harvest(label, q)
        print(f"  回収 {len(p)}件 / 著者レコード {len(a)}件", flush=True)
        all_papers += p
        all_authors += a

    papers = pd.DataFrame(all_papers)
    authors = pd.DataFrame(all_authors)
    authors.to_csv(OUT_DIR / "wos_org_authors.csv", index=False)

    # 既に公式サイトから収集済みの論文と重複していないか（＝サイト掲載漏れの検出）
    combined = pd.read_csv(
        ROOT / "data" / "derived" / "toyota_official_scrape" / "combined_papers.csv")
    known = set(combined["doi"].dropna().astype(str).str.lower())
    papers["already_scraped"] = papers["doi"].isin(known)
    papers.to_csv(OUT_DIR / "wos_org_papers.csv", index=False)

    by_org = papers.groupby("org").agg(
        papers=("wos_uid", "size"),
        with_doi=("doi", lambda s: s.notna().sum()),
        already_scraped=("already_scraped", "sum"),
        median_year=("year", "median"))
    summary = {
        "total_papers": int(len(papers)),
        "total_author_records": int(len(authors)),
        "authors_with_researcher_id": int(authors["researcher_id"].notna().sum())
        if len(authors) else 0,
        "unique_researcher_ids": int(authors["researcher_id"].nunique())
        if len(authors) else 0,
        "by_org": json.loads(by_org.to_json(orient="index")),
        "new_papers_not_in_scrape": int((~papers["already_scraped"]).sum()),
    }
    (OUT_DIR / "wos_org_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    print("\n===== サマリ =====", flush=True)
    print(json.dumps(summary, ensure_ascii=False, indent=2), flush=True)
    print("\n===== 組織別 =====", flush=True)
    print(by_org.to_string(), flush=True)


if __name__ == "__main__":
    main()
