"""AISIN IMRA（日本・aisin.com）の論文一覧を、保存済みHTMLから解析し直す。

直した不具合（2026-09-07）:
  元の実装は `<p class="txt">` のテキストを改行で割り、1行目=タイトル・2行目=著者・3行目=掲載誌
  と決め打ちしていた。ところがサイトの書式は2種類ある。

    A) “タイトル”<br>著者<br><span class="italic">掲載誌,</span> 巻号   ← 改行あり。正しく取れる
    B) “タイトル” 著者 <span class="italic">掲載誌,</span> 巻号        ← 改行なし。1行ずれる

  B の場合、get_text('\\n') が返す断片は ["“タイトル” 著者", "掲載誌,", "巻号"] となり、
  タイトル列に著者が、著者列に掲載誌が、掲載誌列に巻号が入っていた（97件中34件）。

  直し方は、サイトが持っている手がかりを優先順に使う。
    1. タイトル … 引用符の中身。開き/閉じが “ ” " のどれでも拾う（表記が揺れている項目がある）
    2. 掲載誌   … <span class="italic"> があればその中身＋後続の巻号
                   無ければ、原文改行で割った最後の断片
    3. 著者     … タイトルと掲載誌の間

既知の残件（97件中1件）:
  "A molecularly engineered fluorene-substituted Ru-complex..." は、サイト側が掲載誌名
  "Advances in Natural Sciences: Nanoscience and Nanotechnology." を italic の外と中に
  割って書いているため、前半が著者列に残る。サイトのマークアップが壊れているだけで、
  一般化できる規則がないので手を入れていない。

ネットワークには触れない。`aisin_imra_jp_raw_pages/*.html` を読むだけ。
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pandas as pd
from bs4 import BeautifulSoup, NavigableString

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "data" / "derived" / "toyota_official_scrape" / "aisin_imra_jp_raw_pages"
OUT_CSV = ROOT / "data" / "derived" / "toyota_official_scrape" / "aisin_imra_jp.csv"

# 全角・半角どちらの引用符も拾う
# 開き・閉じどちらの記号も混在しているので、両端は文字クラスで受ける
QUOTED = re.compile(r'[“”"]\s*(.{10,}?)\s*[“”"]', re.S)


def clean(s: str | None) -> str | None:
    if s is None:
        return None
    t = re.sub(r"\s+", " ", str(s)).strip()
    t = t.strip(" ,;:")
    return t or None


def parse_item(txt_el) -> tuple[str | None, str | None, str | None]:
    """1件分の <p class="txt"> から (タイトル, 著者, 掲載誌) を取り出す。"""
    italic = txt_el.select_one("span.italic")

    # get_text("\n") は要素境界だけでなく原文の改行も残す。両方を手がかりに使う
    segs = [x.strip() for x in txt_el.get_text("\n").split("\n") if x.strip()]
    flat = clean(" ".join(segs)) or ""

    # --- 掲載誌 ---
    if italic is not None:
        journal = clean(italic.get_text(" "))
        after = flat.split(journal, 1)[1] if journal and journal in flat else ""
        venue = clean(", ".join(x for x in (journal, clean(after)) if x))
        head = flat.split(journal, 1)[0] if journal and journal in flat else flat
    elif len(segs) >= 3:
        # italic が無い項目は、原文改行の最後の断片を掲載誌とみなす
        venue = clean(segs[-1])
        head = clean(" ".join(segs[:-1])) or ""
    else:
        # 手がかりが無い。掲載誌は諦め、著者側に残す（誤って掲載誌を著者名にしないため）
        venue = None
        head = flat

    # --- タイトルと著者 ---
    m = QUOTED.search(head)
    if m:
        title = clean(m.group(1))
        authors = clean(head[m.end():])
    elif len(segs) >= 2 and italic is None:
        title, authors = clean(segs[0]), clean(" ".join(segs[1:-1]) if len(segs) > 2 else segs[1])
    else:
        title, authors = clean(head), None
    return title, authors, venue


def main() -> int:
    rows = []
    for path in sorted(RAW_DIR.glob("page*.html"), key=lambda p: int(re.search(r"\d+", p.name).group())):
        n = int(re.search(r"\d+", path.name).group())
        soup = BeautifulSoup(path.read_text(encoding="utf-8", errors="replace"), "html.parser")
        items = soup.select("article.item.d_flex")
        for it in items:
            cat_el = it.select_one(".cat")
            txt_el = it.select_one(".txt")
            link_el = it.select_one("a.link")
            title, authors, venue = parse_item(txt_el) if txt_el else (None, None, None)
            rows.append({
                "page": n,
                "category": cat_el.get_text(strip=True) if cat_el else None,
                "title": title,
                "authors_raw": authors,
                "venue": venue,
                "link": link_el.get("href") if link_el else None,
            })
        print(f"page{n}: items={len(items)}")

    df = pd.DataFrame(rows)
    df.to_csv(OUT_CSV, index=False)
    print(f"\n書き出し: {OUT_CSV} ({len(df)}行)")
    print(f"  title 平均長 {df['title'].astype(str).str.len().mean():.0f} 文字 / 最大 {df['title'].astype(str).str.len().max()}")
    print(f"  authors_raw 非NULL {df['authors_raw'].notna().sum()}")
    print(f"  venue 非NULL {df['venue'].notna().sum()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
