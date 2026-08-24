"""目視確認の結果を、OpenAlex 対応づけの結果に反映する。

なぜ別ファイルに分けているか:
  対応づけの本体（`openalex_link_toyota_papers.py`）は毎日自動で実行され、
  `openalex_links.csv` を作り直す。目視確認の結果を直接そこへ書き込むと
  翌朝には消えてしまう。そのため判断は
  `data/review/openalex_review_decisions.csv` に人手で残し、
  このスクリプトで毎回上から適用する形にしている。

  今井先生のご指示「文字列一致だけでは誤同定があるため目視確認が必要」への
  対応そのものであり、判断の履歴が残ることに意味がある。

キーについて（2026-08-24 に変更）:
  以前は `row_id`（入力CSVの行番号）で突き合わせていたが、これは**行の位置**
  にすぎず、再スクレイピングや imra.eu の追加で行順が変われば
  判断が別の論文に付いてしまう。そこで位置に依存しない `paper_uid`
  （収集元＋正規化タイトル＋正規化DOI のハッシュ）に移行した。
  さらに、判断表に記録したタイトルが実際の行と一致するかを毎回照合し、
  ずれていれば適用せずに中断する。

入力:
  data/derived/openalex_linking/openalex_links.csv   … 自動生成
  data/review/openalex_review_decisions.csv          … 人手で作る判断表
出力:
  data/derived/openalex_linking/openalex_links_reviewed.csv
  data/derived/openalex_linking/reviewed_summary.json

実行: ~/.venvs/scisci-rir/bin/python src/apply_review_decisions.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
from build_paper_table import paper_uid  # noqa: E402  安定キーの定義を1箇所に保つ

LINKS = ROOT / "data" / "derived" / "openalex_linking" / "openalex_links.csv"
DECISIONS = ROOT / "data" / "review" / "openalex_review_decisions.csv"
OUT_DIR = ROOT / "data" / "derived" / "openalex_linking"


def main() -> None:
    links = pd.read_csv(LINKS)
    links["paper_uid"] = [paper_uid(s, t, d) for s, t, d
                          in zip(links["source_org"], links["title"], links["doi"])]

    if not DECISIONS.exists():
        print("判断表がありません。自動判定のまま出力します。", flush=True)
        dec = pd.DataFrame(columns=["paper_uid", "title", "decision", "reason"])
    else:
        dec = pd.read_csv(DECISIONS)

    if len(dec):
        if "paper_uid" not in dec.columns:
            raise SystemExit(
                "判断表に paper_uid 列がありません。row_id 方式の古い表と思われます。"
                "data/derived/papers/rowid_map.csv で変換してください。")

        # 判断表のキーが実在するか、記録したタイトルと一致するかを照合する。
        # 上流の再生成でタイトルが変わっていれば、ここで気づける。
        known = links.set_index("paper_uid")["title"]
        missing = dec[~dec["paper_uid"].isin(known.index)]
        if len(missing):
            raise SystemExit(
                f"判断表の {len(missing)}件が対応づけ結果に見つかりません。"
                f"上流が変わった可能性があります: "
                f"{missing[['paper_uid', 'title']].to_dict('records')}")
        drift = [(u, t, known[u]) for u, t in zip(dec["paper_uid"], dec["title"])
                 if str(known[u]) != str(t)]
        if drift:
            raise SystemExit(
                f"判断表のタイトルが対応づけ結果と一致しません（{len(drift)}件）。"
                f"判断が別の論文に付くおそれがあるため中断します: {drift}")
        print(f"判断表 {len(dec)}件をキー照合・タイトル照合とも通過", flush=True)

    d = dec.set_index("paper_uid") if len(dec) else dec
    links["review_decision"] = links["paper_uid"].map(
        d["decision"]) if len(dec) else None
    links["review_reason"] = links["paper_uid"].map(
        d["reason"]) if len(dec) else None

    # 誤対応と判断したものは対応づけを取り消す
    rejected = links["review_decision"] == "reject"
    links.loc[rejected, "openalex_id"] = None
    links.loc[rejected, "matched_title"] = None
    links.loc[rejected, "review_status"] = "rejected_by_review"
    links.loc[links["review_decision"] == "accept", "review_status"] = "accepted_by_review"
    links["matched"] = links["openalex_id"].notna()

    links.to_csv(OUT_DIR / "openalex_links_reviewed.csv", index=False)

    by_src = links.groupby("source_org")["matched"].agg(["size", "sum"])
    by_src["rate"] = (by_src["sum"] / by_src["size"] * 100).round(1)
    summary = {
        "input_rows": int(len(links)),
        "matched": int(links["matched"].sum()),
        "match_rate_pct": round(links["matched"].mean() * 100, 1),
        "reviewed": int(dec.shape[0]),
        "review_accepted": int((dec["decision"] == "accept").sum()) if len(dec) else 0,
        "review_rejected": int((dec["decision"] == "reject").sum()) if len(dec) else 0,
        "unreviewed_needing_review": int(
            (links["review_status"] == "review").sum()),
        "by_source_org": {
            k: {"total": int(v["size"]), "matched": int(v["sum"]),
                "rate_pct": float(v["rate"])} for k, v in by_src.iterrows()},
        "unique_openalex_works": int(links["openalex_id"].nunique()),
    }
    (OUT_DIR / "reviewed_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps(summary, ensure_ascii=False, indent=2), flush=True)


if __name__ == "__main__":
    main()
