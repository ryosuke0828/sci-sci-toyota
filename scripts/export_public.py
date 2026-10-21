"""公開用リポジトリを書き出す。

載せてよいファイルの一覧（下の FILES）にあるものだけを、作業用リポジトリから
書き出し先（既定 ~/scisci-public）へコピーする。コピーのときに次の加工をする。
  - ノートブックの出力と実行回数を消す
  - Scopus の取得結果は、著者の表を作るのに使う列だけにする
  - `analyze_novelty_v2` を `analyze_novelty` に改名する
  - 所属の文字列に含まれる第三者のメールアドレスは、`@` より前を `[email]` に置き換える。
    置き換えは取得結果の保存ファイルに対して行い、それを使って工程7〜9（著者の表、所属の正規化、名寄せ）を
    書き出し先で流し直す。こうすると公開する出力は公開する入力から作ったものになり、再現の照合が崩れない。
    `@` より後（ドメイン）は残す。ドメインで組織を判定している行があるため
書き出した後、載せてはいけないものが残っていないかを検査し、見つかれば終了コード1で終わる。

書き出し先に前回の書き出しがあれば、`.git` 以外を消してから書き出す。

実行: python scripts/export_public.py [書き出し先]
計画: docs/plans/public_release.md
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
TEMPLATES = ROOT / "public_release"
DEST = Path(sys.argv[1]).expanduser() if len(sys.argv) > 1 else Path.home() / "scisci-public"

D = "data/derived"
SCRAPE = f"{D}/toyota_official_scrape"

# (作業用リポジトリでの場所, 公開用での場所)。公開用での場所が None なら同じ場所
FILES: list[tuple[str, str | None]] = [
    # 1. スクレイピング
    ("notebooks/exploration/toyota_frontier_research_center_scrape.ipynb",
     "notebooks/scraping/toyota_frontier_research_center_scrape.ipynb"),
    ("notebooks/exploration/toyota_central_rd_labs_scrape.ipynb",
     "notebooks/scraping/toyota_central_rd_labs_scrape.ipynb"),
    ("notebooks/exploration/aisin_imra_jp_scrape.ipynb", "notebooks/scraping/aisin_imra_jp_scrape.ipynb"),
    ("notebooks/exploration/imra_com_scrape.ipynb", "notebooks/scraping/imra_com_scrape.ipynb"),
    (f"{SCRAPE}/frontier_research_center.csv", None),
    (f"{SCRAPE}/frontier_research_center_meta.json", None),
    (f"{SCRAPE}/toyota_central_rd_labs.csv", None),
    (f"{SCRAPE}/toyota_central_rd_labs_meta.json", None),
    (f"{SCRAPE}/aisin_imra_jp.csv", None),
    (f"{SCRAPE}/aisin_imra_jp_meta.json", None),
    (f"{SCRAPE}/imra_com.csv", None),
    (f"{SCRAPE}/imra_com_meta.json", None),
    # 2. 統合
    ("src/rebuild_combined_papers.py", None),
    (f"{SCRAPE}/combined_papers.csv", None),
    # 3〜5. OpenAlex との対応づけ、目視判断、論文の表
    ("src/openalex_link_toyota_papers.py", None),
    ("src/apply_review_decisions.py", None),
    ("src/build_paper_table.py", None),
    ("data/cache/openalex_linking_cache.json", None),
    ("data/review/openalex_review_decisions.csv", None),
    (f"{D}/openalex_linking/openalex_links.csv", None),
    (f"{D}/openalex_linking/openalex_works_meta.csv", None),
    (f"{D}/openalex_linking/openalex_links_reviewed.csv", None),
    (f"{D}/papers/papers.csv", None),
    # 6〜10. 所属などの補完、名寄せ
    ("src/enrich_papers_scopus.py", None),
    ("src/build_authorship_table.py", None),
    ("src/normalize_affiliations.py", None),
    ("src/aggregate_researchers.py", None),
    (f"{D}/paper_enrichment/scopus_paper_authors.csv", None),
    (f"{D}/papers/authorships.csv", None),
    (f"{D}/papers/authorship_affiliations.csv", None),
    (f"{D}/researchers/researchers.csv", None),
    # 11〜14. OpenAlex の全論文データを使う工程（参考文献、論文の属性、新規性の自前計算）
    ("src/openalex_snapshot_extract.py", None),
    ("src/build_reference_titles.py", None),
    ("src/build_paper_covariates.py", None),
    ("src/novelty_uzzi.py", None),
    ("src/novelty_uzzi_selftest.py", None),
    (f"{D}/papers/paper_references.csv", None),
    (f"{D}/papers/paper_covariates.csv", None),
    (f"{D}/novelty/paper_novelty.csv", None),
    # 15〜16. SciSciNet の値と検証
    ("src/fetch_sciscinet_metrics.py", None),
    ("src/verify_novelty_sciscinet.py", None),
    (f"{D}/papers/sciscinet_metrics.csv", None),
    (f"{D}/novelty/sciscinet_check.json", None),
    # 17〜19. 分析
    ("src/build_analysis_table.py", None),
    ("src/build_matched_baseline.py", None),
    ("src/analyze_novelty_v2.py", "src/analyze_novelty.py"),
    (f"{D}/analysis/paper_analysis.csv", None),
    (f"{D}/analysis/baseline_sample.csv", None),
    (f"{D}/analysis/paper_percentiles.csv", None),
    (f"{D}/analysis/novelty_analysis.json", None),
]

# Scopus の取得結果のうち、build_authorship_table.py が使う列（と並び順の列）
SCOPUS_KEEP = ["doi", "author_position", "scopus_author_id", "surname", "given_name", "affiliation"]

RENAMES = {"analyze_novelty_v2": "analyze_novelty"}

# メールアドレスの `@` より前（ドメインが続くものだけ）
EMAIL_LOCAL = re.compile(r"[\w.+-]+@(?=[\w-]+(?:\.[\w-]+)+)")
EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
# 伏せた保存ファイルから作り直す工程（工程7〜9）
REBUILD = ["src/build_authorship_table.py", "src/normalize_affiliations.py", "src/aggregate_researchers.py"]
# 作り直した出力のうち、所属の文字列そのものを持つ列（伏せた分だけ変わってよい列）
TEXT_COLS = {"affiliation", "affil_openalex", "affil_best", "affiliations"}

# --- 検査 ---
TEXT_SUFFIXES = {".py", ".ipynb", ".md", ".txt", ".example", ".gitignore"}
# コード・文書に残っていてはいけないもの
FORBIDDEN_TEXT = [
    r"[\w.+-]+@[\w-]+\.[\w.-]+",            # メールアドレス
    r"/Users/", r"jinedinujidan", r"msp-lab", r"gmail",
    r"伊倉", r"今井", r"先生", r"Ikura", r"Imai", r"Hayashi", r"Sota",
    r"scisci-rir", r"scisci-auto", r"launchd", r"Google Drive", r"Notion",
    r"log\.md", r"STATUS\.md", r"docs/", r"段階\d", r"toyota_authors\.csv", r"toyota_data",
    r"analyze_novelty_v2",
    r"(?i)(api[_-]?key|apikey)\s*[=:]\s*[\"']?[0-9a-f]{32}",
]
# 載せてはいけないファイル名
FORBIDDEN_NAMES = [
    r"_raw\.(html|json)$", r"raw_pages", r"scopus_abstract_cache", r"scopus_papers\.csv",
    r"wos", r"pilot", r"literature", r"toyota_authors\.csv", r"analysis_summary\.json",
    r"paper_novelty_joined", r"paper_references\.json", r"\.DS_Store", r"openalex_title_cache",
    r"random_impact", r"h_index",
]
MAX_BYTES = 50 * 1024 * 1024  # GitHub が警告を出す大きさ


def mask_emails(text: str) -> str:
    return EMAIL_LOCAL.sub("[email]@", text)


def rebuild_with_masked_cache() -> list[str]:
    """伏せた保存ファイルから工程7〜9を書き出し先で流し直し、判定が変わっていないかを確かめる。"""
    for script in REBUILD:
        r = subprocess.run([sys.executable, script], cwd=DEST, capture_output=True, text=True)
        if r.returncode != 0:
            sys.exit(f"{script} が失敗した:\n{r.stdout[-2000:]}\n{r.stderr[-2000:]}")
    problems = []
    G = "data/diagnostics"
    for rel in [f"{D}/papers/authorships.csv", f"{D}/papers/authorship_affiliations.csv",
                f"{G}/researchers/author_records_keyed.csv", f"{D}/researchers/researchers.csv"]:
        old, new = pd.read_csv(ROOT / rel), pd.read_csv(DEST / rel)
        if list(old.columns) != list(new.columns) or len(old) != len(new):
            problems.append(f"作り直しで形が変わった: {rel}")
            continue
        for c in old.columns:
            if c in TEXT_COLS:
                continue
            a, b = old[c], new[c]
            n = int(((a != b) & ~(a.isna() & b.isna())).sum())
            if n:
                problems.append(f"作り直しで値が変わった: {rel} の {c}（{n}行）")
    for rel in [f"{G}/papers/authorships_summary.json", f"{G}/researchers/researchers_summary.json",
                f"{G}/researchers/namekey_validation.json"]:
        if json.loads((ROOT / rel).read_text()) != json.loads((DEST / rel).read_text()):
            problems.append(f"作り直しで要約が変わった: {rel}")
    # 確認用の出力はコミットしない（.gitignore で除外）ので、書き出し先には残さない
    shutil.rmtree(DEST / G, ignore_errors=True)
    return problems


def clean_dest() -> None:
    if DEST.exists() and any(DEST.iterdir()):
        if not (DEST / "reproduce.ipynb").exists():
            sys.exit(f"{DEST} は前回の書き出しではないので消さない。別の書き出し先を指定すること")
        for p in DEST.iterdir():
            if p.name == ".git":
                continue
            shutil.rmtree(p) if p.is_dir() else p.unlink()
    DEST.mkdir(parents=True, exist_ok=True)


def rename_text(s: str) -> str:
    for a, b in RENAMES.items():
        s = s.replace(a, b)
    return s


def copy_notebook(src: Path, dst: Path) -> None:
    nb = json.loads(src.read_text(encoding="utf-8"))
    for c in nb["cells"]:
        if c["cell_type"] == "code":
            c["outputs"] = []
            c["execution_count"] = None
        c["metadata"] = {}  # 実行時刻などが残るので消す
        c["source"] = rename_text("".join(c["source"])).splitlines(keepends=True)
    nb["metadata"] = {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
                      "language_info": {"name": "python"}}
    dst.write_text(json.dumps(nb, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


def copy_one(src_rel: str, dst_rel: str) -> None:
    src, dst = ROOT / src_rel, DEST / dst_rel
    dst.parent.mkdir(parents=True, exist_ok=True)
    name = src.name
    if name == "scopus_paper_authors.csv":
        pd.read_csv(src, dtype=str)[SCOPUS_KEEP].to_csv(dst, index=False)
    elif name == "openalex_linking_cache.json":
        dst.write_text(mask_emails(src.read_text(encoding="utf-8")), encoding="utf-8")
    elif src.suffix == ".ipynb":
        copy_notebook(src, dst)
    elif src.suffix == ".py":
        dst.write_text(rename_text(src.read_text(encoding="utf-8")), encoding="utf-8")
    else:
        shutil.copy2(src, dst)


def copy_templates() -> None:
    for src in sorted(p for p in TEMPLATES.rglob("*") if p.is_file()):
        if src.name == ".DS_Store":
            continue
        dst = DEST / src.relative_to(TEMPLATES)
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)


def check() -> list[str]:
    problems = []
    for p in sorted(x for x in DEST.rglob("*") if x.is_file() and ".git" not in x.relative_to(DEST).parts):
        rel = str(p.relative_to(DEST))
        for pat in FORBIDDEN_NAMES:
            if re.search(pat, rel):
                problems.append(f"載せないファイル: {rel}")
        if p.stat().st_size > MAX_BYTES:
            problems.append(f"50MB 超: {rel} ({p.stat().st_size / 1e6:.0f}MB)")
        if p.suffix in TEXT_SUFFIXES or p.name in {".gitignore", ".env.example"}:
            text = p.read_text(encoding="utf-8", errors="replace")
            for pat in FORBIDDEN_TEXT:
                for m in re.finditer(pat, text):
                    problems.append(f"{rel}: 「{m.group(0)}」")
        elif p.suffix == ".csv":
            cols = pd.read_csv(p, nrows=0).columns
            if any("abstract" in c.lower() for c in cols):
                problems.append(f"要旨の列: {rel}")
        if p.suffix in {".csv", ".json"}:
            text = p.read_text(encoding="utf-8", errors="replace")
            for pat in [r"/Users/", r"jinedinujidan", r"msp-lab", r"ikuraryosuke", r'"abstract"']:
                if re.search(pat, text):
                    problems.append(f"{rel}: データに「{pat}」")
            n_email = len(EMAIL.findall(text))
            if n_email:
                problems.append(f"{rel}: メールアドレスが {n_email} 件残っている")
    return problems


def main() -> int:
    missing = [s for s, _ in FILES if not (ROOT / s).exists()]
    if missing:
        sys.exit("作業用リポジトリに無いファイル:\n  " + "\n  ".join(missing))
    clean_dest()
    for src_rel, dst_rel in FILES:
        copy_one(src_rel, dst_rel or src_rel)
    copy_templates()
    rebuilt = rebuild_with_masked_cache()

    files = [x for x in DEST.rglob("*") if x.is_file() and ".git" not in x.relative_to(DEST).parts]
    total = sum(x.stat().st_size for x in files)
    print(f"書き出し: {DEST}  {len(files)} ファイル / {total / 1e6:.1f}MB")

    problems = rebuilt + check()
    if problems:
        print(f"\n検査で {len(problems)} 件見つかった:")
        for x in problems:
            print("  " + x)
        return 1
    print("検査: 問題なし")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
