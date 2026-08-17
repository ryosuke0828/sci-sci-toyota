"""目視確認の結果を、OpenAlex 対応づけの結果に反映する。

なぜ別ファイルに分けているか:
  対応づけの本体（`openalex_link_toyota_papers.py`）は毎日自動で実行され、
  `openalex_links.csv` を作り直す。目視確認の結果を直接そこへ書き込むと
  翌朝には消えてしまう。そのため判断は
  `data/review/openalex_review_decisions.csv` に人手で残し、
  このスクリプトで毎回上から適用する形にしている。

  今井先生のご指示「文字列一致だけでは誤同定があるため目視確認が必要」への
  対応そのものであり、判断の履歴が残ることに意味がある。

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
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
LINKS = ROOT / "data" / "derived" / "openalex_linking" / "openalex_links.csv"
DECISIONS = ROOT / "data" / "review" / "openalex_review_decisions.csv"
OUT_DIR = ROOT / "data" / "derived" / "openalex_linking"


def main() -> None:
    links = pd.read_csv(LINKS)
    if not DECISIONS.exists():
        print("判断表がありません。自動判定のまま出力します。", flush=True)
        dec = pd.DataFrame(columns=["row_id", "decision", "reason"])
    else:
        dec = pd.read_csv(DECISIONS)

    # row_id は入力CSVの行番号。自動生成側と判断表で同じものを指す
    d = dec.set_index("row_id")
    links["review_decision"] = links["row_id"].map(d["decision"])
    links["review_reason"] = links["row_id"].map(d["reason"])

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
