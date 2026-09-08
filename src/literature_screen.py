"""段階2-2: 集めた候補文献を抄録つきでスクリーニングし、機械的に分類する。

計画（docs/plans/novelty_hotstreak.md 段階2-2）は
「タイトル・抄録でスクリーニングし分類（指標の定義／実証応用／批判・再現／企業研究の文脈）」。

抄録は OpenAlex の `abstract_inverted_index`（語 → 出現位置の対応）で返るので、
位置の順に語を並べ直して復元する。

分類は語句規則による**一次ふるい**である。最終的な採否（段階2-4）は本文を読んで決める。
規則で拾えるのは「その語が出てくるか」だけなので、取りこぼしも誤りも残る。
そのため各文献に、どの規則で当たったかを `match_reason` として残し、後から検証できるようにする。

入力: data/derived/literature/candidates_titled.csv
出力: data/derived/literature/candidates_screened.csv
      data/cache/openalex_abstract_cache.json

実行: ~/.venvs/scisci-rir/bin/python src/literature_screen.py
"""

from __future__ import annotations

import json
import re
import sys
import time
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parent.parent
IN = ROOT / "data" / "derived" / "literature" / "candidates_titled.csv"
OUT = ROOT / "data" / "derived" / "literature" / "candidates_screened.csv"
CACHE = ROOT / "data" / "cache" / "openalex_abstract_cache.json"
API = "https://api.openalex.org/works"
MAILTO = "r.ikura@msp-lab.org"
BATCH = 50


def invert(idx: dict | None) -> str | None:
    """`{語: [出現位置...]}` を元の語順の文章に戻す。"""
    if not idx:
        return None
    pos = [(p, w) for w, ps in idx.items() for p in ps]
    pos.sort()
    return " ".join(w for _, w in pos)


def fetch_abstracts(ids: list[int], cache: dict) -> None:
    todo = [i for i in ids if str(i) not in cache]
    print(f"抄録取得: 未取得 {len(todo)} / 全 {len(ids)}", flush=True)
    for k in range(0, len(todo), BATCH):
        chunk = todo[k:k + BATCH]
        params = {
            "filter": "openalex_id:" + "|".join(f"https://openalex.org/W{i}" for i in chunk),
            "select": "id,abstract_inverted_index",
            "per_page": BATCH, "mailto": MAILTO,
        }
        r = requests.get(API, params=params, timeout=60)
        if r.status_code == 429:
            if r.headers.get("x-ratelimit-remaining") == "0":
                print("日次クォータを使い切った。ここまでを保存する", flush=True)
                break
            time.sleep(10)
            r = requests.get(API, params=params, timeout=60)
        r.raise_for_status()
        got = {w["id"].rsplit("/W", 1)[-1]: invert(w.get("abstract_inverted_index"))
               for w in r.json()["results"]}
        for i in chunk:
            cache[str(i)] = got.get(str(i))
        time.sleep(0.1)
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    CACHE.write_text(json.dumps(cache, ensure_ascii=False))


# 語句規則。値は (正規表現, 説明)。小文字化した「タイトル + 抄録」に当てる
TOPIC = {
    "novelty": r"\b(novelty|novel combination|atypical|atypicality|originality|recombinant)\b",
    "disruption": r"\b(disrupt\w*|cd index|consolidat\w*)\b",
    "hot_streak": r"\b(hot streak|career|q-model|q model|productivity trajector)\w*\b",
    "team": r"\b(team size|team structure|collaborat\w*|co-?authorship)\b",
}
KIND = {
    "metric_definition": (
        r"(we (propose|introduce|develop|present) (a |an |the )?(new |novel )?(measure|metric|index|indicator)"
        r"|new (measure|metric|index|indicator)"
        r"|(measure|metric|index|indicator) (of|for) (novelty|disruption|atypicality))",
        "指標を新しく定義・提案している"),
    "critique_replication": (
        r"(replicat\w*|robustness|sensitiv\w*|validity|reliab\w*|caveat|pitfall|artifact|artefact"
        r"|criticis\w*|critique|misleading|bias(ed)? (measure|index)|reexamin\w*|re-examin\w*"
        r"|comment on|reply to|fail(s|ed)? to)",
        "既存指標の再現性・頑健性・妥当性を論じている"),
    "corporate": (
        r"\b(firm|firms|corporate|corporation|industr(y|ial)|R&D lab|private sector|patent\w*"
        r"|company|companies|business)\b",
        "企業・産業の文脈を扱っている"),
    "review": (r"\b(review|survey|overview|systematic review|literature review)\b",
               "総説・レビュー"),
}


def classify(text: str) -> tuple[list[str], list[str], list[str]]:
    t = (text or "").lower()
    topics = [k for k, pat in TOPIC.items() if re.search(pat, t)]
    kinds, reasons = [], []
    for k, (pat, desc) in KIND.items():
        m = re.search(pat, t)
        if m:
            kinds.append(k)
            reasons.append(f"{k}:{m.group(0)[:40]}")
    return topics, kinds, reasons


def main() -> int:
    c = pd.read_csv(IN)
    cache = json.loads(CACHE.read_text()) if CACHE.exists() else {}
    fetch_abstracts(sorted(set(int(x) for x in c["cand"])), cache)

    c["abstract"] = c["cand"].map(lambda i: cache.get(str(int(i))))
    n_abs = c["abstract"].notna().sum()
    print(f"抄録が付いたもの {n_abs:,}/{len(c):,}（{n_abs/len(c)*100:.1f}%）", flush=True)

    text = (c["title"].fillna("") + " " + c["abstract"].fillna(""))
    res = text.map(classify)
    c["topics"] = res.map(lambda r: "|".join(r[0]))
    c["kinds"] = res.map(lambda r: "|".join(r[1]))
    c["match_reason"] = res.map(lambda r: " ; ".join(r[2]))
    c["n_topics"] = res.map(lambda r: len(r[0]))

    c = c.sort_values(["n_seeds", "cited_by_count"], ascending=False)
    c.to_csv(OUT, index=False)

    print("\n===== 話題別の件数（重複あり）=====", flush=True)
    for k in TOPIC:
        print(f"  {k:12s} {int(c['topics'].str.contains(k, na=False).sum()):5d}", flush=True)
    print("\n===== 種類別の件数（重複あり）=====", flush=True)
    for k, (_, desc) in KIND.items():
        print(f"  {k:22s} {int(c['kinds'].str.contains(k, na=False).sum()):5d}   {desc}", flush=True)
    print(f"\n話題に1つも当たらなかったもの {int((c['n_topics']==0).sum()):,} 件"
          f"（抄録なし {int(c['abstract'].isna().sum()):,} 件を含む）", flush=True)
    print(f"\n出力: {OUT}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
