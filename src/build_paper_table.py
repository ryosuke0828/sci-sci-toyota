"""論文テーブルを、位置に依存しない安定した主キーで作り直す。

なぜ必要か:
  `combined_papers.csv` には単独で一意な列がない。現行の `row_id` は
  `openalex_link_toyota_papers.py` が `range(len(df))` で振った**行の位置**であり、
  入力の行順が変われば別の論文を指す。目視判断（`data/review/openalex_review_decisions.csv`）
  がこの row_id をキーにしているため、再スクレイピングや imra.eu の追加で
  判断が静かにずれる。

主キーの設計:
  paper_uid = sha1(収集元 | 正規化タイトル | 正規化DOI) の先頭12桁。
  - 収集元を含めるのは、同一論文が複数サイトに載る場合を別の掲載として残すため
    （未来創成センターと豊田中研の共著論文がこれにあたる。正常な重複であり、
      「どのサイトに載っていたか」は所属判定の情報になるので潰さない）。
  - imra.com 内の完全重複1件は同じ uid に落ちるので、ここで解消される。
  - 入力の行順・件数の増減に影響されない。

入力: data/derived/toyota_official_scrape/combined_papers.csv
      data/derived/openalex_linking/openalex_links_reviewed.csv
      data/derived/openalex_linking/openalex_works_meta.csv
出力: data/derived/papers/papers.csv      … 1掲載1行。主キー paper_uid
      data/derived/papers/rowid_map.csv   … 旧 row_id → paper_uid の対応表（判断表の移行用）
      data/derived/papers/summary.json

実行: ~/.venvs/scisci-rir/bin/python src/build_paper_table.py
"""
from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
IN_COMBINED = ROOT / "data" / "derived" / "toyota_official_scrape" / "combined_papers.csv"
IN_LINKS = ROOT / "data" / "derived" / "openalex_linking" / "openalex_links_reviewed.csv"
IN_WORKS = ROOT / "data" / "derived" / "openalex_linking" / "openalex_works_meta.csv"
OUT_DIR = ROOT / "data" / "derived" / "papers"


def normalize_doi(raw) -> str | None:
    if raw is None or (isinstance(raw, float) and pd.isna(raw)):
        return None
    s = str(raw).strip()
    if not s or s.lower() == "nan":
        return None
    s = re.sub(r"^https?://(dx\.)?doi\.org/", "", s, flags=re.I).strip().rstrip(".")
    return s.lower() if s.startswith("10.") else None


def normalize_title(raw) -> str:
    if raw is None or (isinstance(raw, float) and pd.isna(raw)):
        return ""
    s = unicodedata.normalize("NFKC", str(raw)).lower()
    s = re.sub(r"[^0-9a-z぀-ヿ一-鿿]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def paper_uid(source_org, title, doi) -> str:
    """位置に依存しない安定キー。入力が同じなら常に同じ値になる。"""
    basis = f"{str(source_org).strip()}|{normalize_title(title)}|{normalize_doi(doi) or ''}"
    return hashlib.sha1(basis.encode("utf-8")).hexdigest()[:12]


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    links = pd.read_csv(IN_LINKS)
    works = pd.read_csv(IN_WORKS)
    print(f"入力: 掲載 {len(links)}行 / OpenAlex Work {len(works)}件", flush=True)

    links["paper_uid"] = [paper_uid(s, t, d) for s, t, d
                          in zip(links["source_org"], links["title"], links["doi"])]

    # 旧 row_id との対応を先に残す（判断表の移行に使う）
    links[["row_id", "paper_uid", "source_org", "title", "doi", "openalex_id"]] \
        .to_csv(OUT_DIR / "rowid_map.csv", index=False)

    dup = int(links["paper_uid"].duplicated().sum())
    if dup:
        d = links[links["paper_uid"].duplicated(keep=False)].sort_values("paper_uid")
        print(f"\n同一 paper_uid に落ちた掲載 {dup}件（サイト内の重複掲載。統合する）:", flush=True)
        for _, r in d.iterrows():
            print(f"    {r.paper_uid}  {str(r.source_org)[:22]:24s} {str(r.title)[:56]}", flush=True)
    papers = links.drop_duplicates("paper_uid", keep="first").copy()

    # OpenAlex Work の属性を結合する
    papers = papers.merge(works, on="openalex_id", how="left", suffixes=("", "_work"))

    # 列を整理する。サイト由来の値と OpenAlex 由来の値を名前で区別する
    papers = papers.rename(columns={
        "title": "title_site", "venue": "venue_site", "year": "year_site",
        "authors_raw": "authors_site",
        "toyota_affiliated_authors": "toyota_authors_site",
        "openalex_id": "work_id",
        "publication_year": "year_openalex", "venue_openalex": "venue_openalex",
    })
    cols = [
        "paper_uid", "source_org", "title_site", "authors_site", "venue_site",
        "year_site", "link", "doi", "doi_norm", "toyota_authors_site",
        "work_id", "match_method", "match_score", "review_status",
        "review_decision", "review_reason", "matched", "is_work_primary", "matched_title",
        "year_openalex", "type", "cited_by_count", "referenced_works_count",
        "n_authors", "institutions_distinct_count",
        "primary_topic", "primary_subfield", "primary_field", "primary_domain",
        "venue_openalex", "openalex_doi",
    ]
    papers = papers.sort_values(["source_org", "paper_uid"]).reset_index(drop=True)

    # 同一 Work を指す掲載が5件ある（組織横断の共著論文。両サイトに載るのは正常）。
    # 掲載単位のまま被引用数を合計すると二重計上になるため、Work あたり1行に
    # True を立てておく。Work 単位の集計は必ずこの列で絞る。
    # 対応づかなかった掲載は Work を持たないので、すべて True にする。
    papers["is_work_primary"] = True
    has = papers["work_id"].notna()
    papers.loc[has, "is_work_primary"] = ~papers.loc[has].duplicated("work_id")

    papers = papers[[c for c in cols if c in papers.columns]]
    papers.to_csv(OUT_DIR / "papers.csv", index=False)

    assert papers["paper_uid"].is_unique, "paper_uid が一意でない"

    by_src = papers.groupby("source_org").agg(
        掲載=("paper_uid", "size"),
        対応づけ済=("matched", "sum"),
        DOIあり=("doi_norm", lambda s: int(s.notna().sum())))
    summary = {
        "papers": int(len(papers)),
        "collapsed_duplicate_listings": dup,
        "matched_to_openalex": int(papers["matched"].sum()),
        "distinct_works": int(papers["work_id"].nunique()),
        "listings_sharing_a_work": int(
            papers["work_id"].notna().sum() - papers["work_id"].nunique()),
        "with_doi": int(papers["doi_norm"].notna().sum()),
        "cited_by_total_work_level": int(
            papers.loc[papers["is_work_primary"], "cited_by_count"].sum()),
        "references_total_work_level": int(
            papers.loc[papers["is_work_primary"], "referenced_works_count"].sum()),
        "by_source_org": json.loads(by_src.to_json(orient="index")),
    }
    (OUT_DIR / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    print("\n===== papers.csv =====", flush=True)
    print(by_src.to_string(), flush=True)
    print(json.dumps({k: v for k, v in summary.items() if k != "by_source_org"},
                     ensure_ascii=False, indent=2), flush=True)
    print(f"\n出力: {OUT_DIR/'papers.csv'}\n      {OUT_DIR/'rowid_map.csv'}", flush=True)


if __name__ == "__main__":
    main()
