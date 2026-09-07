"""4サイトのスクレイプ結果を統合して combined_papers.csv を作り直す。

`notebooks/exploration/toyota_official_scrape_consolidate.ipynb` の統合処理を、
再実行できるようスクリプトにしたもの。処理内容は同じ（単純な連結＋リンクからのDOI抽出）で、
重複の除去は行わない。行の順序も同じなので、下流が使う `row_id`（行位置）は変わらない。

2026-09-07: aisin.com の解析不具合（src/reparse_aisin_imra_jp.py 参照）を反映するために作成。

入力: data/derived/toyota_official_scrape/{frontier_research_center,toyota_central_rd_labs,
      aisin_imra_jp,imra_com}.csv
出力: data/derived/toyota_official_scrape/combined_papers.csv
"""

from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = ROOT / "data" / "derived" / "toyota_official_scrape"
DOI_PATTERN = re.compile(r"doi\.org/(.+)$", re.IGNORECASE)


def extract_doi(link):
    if not isinstance(link, str):
        return None
    m = DOI_PATTERN.search(link)
    return m.group(1).lower() if m else None


def main() -> int:
    frontier = pd.read_csv(SRC_DIR / "frontier_research_center.csv")
    frontier_std = pd.DataFrame({
        "source_org": "トヨタ自動車未来創成センター",
        "title": frontier["title"],
        "authors_raw": frontier["authors_display"],
        "venue": frontier["source"],
        "year": frontier["year"],
        "link": frontier["link"],
        "toyota_affiliated_authors": frontier["toyota_affiliated_authors"],
    })

    tytlabs = pd.read_csv(SRC_DIR / "toyota_central_rd_labs.csv")
    tytlabs_std = pd.DataFrame({
        "source_org": "豊田中央研究所",
        "title": tytlabs["title"],
        "authors_raw": tytlabs["authors_raw"],
        "venue": tytlabs["journal"],
        "year": tytlabs["year"],
        "link": tytlabs["link"],
        "toyota_affiliated_authors": None,  # このサイトには太字マーキングがない
    })

    aisin_jp = pd.read_csv(SRC_DIR / "aisin_imra_jp.csv")
    aisin_jp_std = pd.DataFrame({
        "source_org": "AISIN IMRA(日本・aisin.com)",
        "title": aisin_jp["title"],
        "authors_raw": aisin_jp["authors_raw"],
        "venue": aisin_jp["venue"],
        "year": aisin_jp["venue"].str.extract(r"((?:19|20)\d{2})")[0].astype("Float64"),
        "link": aisin_jp["link"],
        "toyota_affiliated_authors": None,
    })

    imra_com = pd.read_csv(SRC_DIR / "imra_com.csv")
    imra_com_std = pd.DataFrame({
        "source_org": "AISIN IMRA(米国・imra.com)",
        "title": imra_com["title"],
        "authors_raw": None,  # このサイトには著者記載がない
        "venue": imra_com["venue"],
        "year": imra_com["venue"].str.extract(r"\(((?:19|20)\d{2})\)")[0].astype("Float64"),
        "link": imra_com["link"],
        "toyota_affiliated_authors": None,
    })

    combined = pd.concat(
        [frontier_std, tytlabs_std, aisin_jp_std, imra_com_std], ignore_index=True
    )
    combined["doi"] = combined["link"].map(extract_doi)

    out = SRC_DIR / "combined_papers.csv"
    combined.to_csv(out, index=False)
    print("ソース別件数:")
    print(combined["source_org"].value_counts().to_string())
    print(f"\n合計 {len(combined)} 件 / DOIあり {combined['doi'].notna().sum()} 件")
    print(f"保存: {out.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
