# データ

## やったこと

トヨタ関連4サイト（トヨタ自動車未来創成センター、豊田中央研究所、AISIN IMRA 日本、AISIN IMRA 米国）から
論文一覧をスクレイピングし、OpenAlex に対応づけて書誌情報（出版年・被引用・参考文献・分野・著者・所属）を
取得した。所属は Crossref と Scopus でも補った。

対応づけは DOI があれば完全一致、なければタイトル照合。919掲載のうち857件が対応づいた。

結果、テーブルは4つ。

| ファイル | 1行＝何か | 行数 | 主キー |
|---|---|---:|---|
| `derived/papers/papers.csv` | 論文1件（サイトへの掲載1件） | 917 | `paper_uid` |
| `derived/papers/authorships.csv` | 論文の著者1人 | 4,448 | `paper_uid` + `author_seq` |
| `derived/papers/paper_references.csv` | 論文の参考文献1件 | 27,247 | `paper_uid` + `ref_seq` |
| `derived/researchers/researchers.csv` | 研究者1人（名寄せ後） | 1,682 | `cluster_id` |

`paper_uid` は 収集元・タイトル・DOI から作ったハッシュ。行の位置に依存しないので再生成しても変わらない。

## 使うときの注意（先に読む）

- **Work 単位で集計するときは `is_work_primary == True` で絞る。** 同じ論文が2サイトに載っている5件を
  二重に数えないため。
- **出版年は `year_openalex` を使う。** `year_site` はサイト由来で、imra.com ではほとんど埋まらない。
- **`openalex_author_id` を名寄せに使わない。** 別人が併合されている（「S. Nakamura」が研究歴74年になる例がある）。
  著者の同定は `orcid`、無ければ `name_key`（姓＋名の頭文字）を使う。この寄せ方の精度は実測してあり、
  別人を同一人物とする誤りが 4.8%、同一人物を分ける誤りが 0.8%（ORCID 付き950レコードで実測）。
- **`inst_openalex` を所属判定に使わない。** OpenAlex がトヨタのスイス法人に誤帰属させている例が多い。
  組織単位で集計するなら `affil_scopus`（正規化済み247種）か `is_toyota` を使う。
- `authorships.csv` がカバーするのは OpenAlex に対応づいた857件のみ。残る60件には著者行がない。

---

## papers.csv（917行 × 31列）

| カラム | 非NULL | ユニーク | 意味 |
|---|---:|---:|---|
| `paper_uid` | 100% | 917 | 主キー |
| `source_org` | 100% | 4 | 収集元サイト |
| `title_site` | 100% | 916 | サイト掲載のタイトル |
| `authors_site` | 66% | 571 | サイト掲載の著者名。imra.com は常に空 |
| `venue_site` | 100% | 721 | サイト掲載の掲載誌・巻号 |
| `year_site` | 70% | 23 | サイト掲載の出版年。**集計に使わない。** `year_openalex` を使う |
| `link` | 98% | 892 | サイトのリンク先 |
| `doi` / `doi_norm` | 70% | 641 | `doi_norm` が正規化済み。結合はこちら |
| `toyota_authors_site` | 17% | 106 | 未来創成センターのみ。サイトが太字で示した自社所属著者。所属判定の正解ラベル |
| `work_id` | 93% | 852 | OpenAlex Work ID。NULL は対応づけ失敗（60件） |
| `match_method` | 94% | 2 | `doi_exact` / `title_fuzzy` |
| `match_score` | 94% | 21 | タイトル類似度。`doi_exact` は 1.0 |
| `review_status` | 94% | 4 | `auto` / `review` / `accepted_by_review` / `rejected_by_review` |
| `review_decision` / `review_reason` | 1% | 2 | 目視判断10件のみ |
| `matched` | 100% | 2 | 対応づいたか |
| `is_work_primary` | 100% | 2 | **Work単位の集計はこれで絞る**（重複掲載5件の対策） |
| `matched_title` | 93% | 852 | OpenAlex 側のタイトル。目視確認用 |
| `year_openalex` | 93% | 38 | **出版年はこちら** |
| `type` | 93% | 5 | `article` / `conference-paper` / `book-chapter` / `preprint` / `editorial` |
| `cited_by_count` | 93% | 137 | 被引用数 |
| `referenced_works_count` | 93% | 102 | 参考文献数。0 の62件は参考文献系の指標を計算できない |
| `n_authors` | 93% | 19 | 著者数 |
| `institutions_distinct_count` | 93% | 16 | 関与機関数 |
| `primary_topic` | 93% | 280 | OpenAlex の分野分類（第4階層） |
| `primary_subfield` | 93% | 80 | 同（第3階層） |
| `primary_field` | 93% | 21 | 同（第2階層） |
| `primary_domain` | 93% | 4 | 同（第1階層） |
| `venue_openalex` | 80% | 307 | OpenAlex 側の掲載誌名 |
| `openalex_doi` | 93% | 848 | OpenAlex 側の DOI。`doi_norm` と食い違えば対応づけを疑う |

## authorships.csv（4,448行 × 24列、857論文分）

| カラム | 非NULL | ユニーク | 意味 |
|---|---:|---:|---|
| `paper_uid` | 100% | 857 | 主キー1。`papers.csv` への参照 |
| `author_seq` | 100% | 25 | 主キー2。著者順（1始まり） |
| `work_id` | 100% | 852 | `papers.csv` からの冗長列。JOIN を省くため |
| `doi` | 72% | 640 | 同上 |
| `source_org` | 100% | 4 | 同上 |
| `spine` | 100% | 1 | 著者リストの取得元。全行 `openalex` |
| `name_raw` | 100% | 1,997 | 著者名の生文字列 |
| `given` / `family` | 100% | 1,189 / 1,258 | 名 / 姓 |
| `name_key` | 100% | 1,639 | 名寄せキー（`姓\|名の頭文字`） |
| `orcid` | 21% | 501 | ORCID。**著者同定はこれが最優先** |
| `orcid_openalex_raw` / `orcid_crossref` | 21% / 17% | 501 / 378 | ORCID の出所別。OpenAlex は論文の登録データ由来のみ採用 |
| `affiliation` | 99% | 1,536 | 所属の代表値 |
| `affil_openalex` | 98% | 1,529 | OpenAlex 由来。**最も網羅的だが表記がバラバラ**（豊田中研を含む文字列だけで311通り） |
| `affil_crossref` | 25% | 369 | Crossref 由来 |
| `affil_scopus` | 55% | 247 | Scopus 由来。**表記が正規化済み。組織単位の集計はこちら** |
| `inst_openalex` | 94% | 410 | OpenAlex が付けた機関名。**所属判定に使わない**（スイス法人への誤帰属を含む） |
| `openalex_author_id` | 98% | 1,910 | 保持のみ。**名寄せに使わない**（別人が併合されている） |
| `scopus_author_id` | 56% | 1,128 | 保持のみ |
| `is_corresponding` | 100% | 2 | 責任著者か |
| `is_toyota` | 100% | 2 | 所属がトヨタ系か。豊田工業大学・豊田高専・刈谷豊田総合病院は除外済み |
| `matched_crossref` / `matched_scopus` | 100% | 2 | 各DBと突き合わせできたか。DOI がなければ常に False |

---

## 既知の限界

- 公式サイトに載っているのはおおむね2018年以降の論文。それ以前は WoS 由来の分を除き網羅していない。
- 所属文字列の正規化は未完了。`affil_openalex` は同じ組織でも表記が割れるため、組織単位の集計には
  `affil_scopus` か `is_toyota` を使う。
- 目視確認待ちが `review_status == "review"` に残っている。
- AISIN IMRA 日本（aisin.com）の1件は、サイト側が掲載誌名を分割して書いているため
  `authors_site` の末尾に掲載誌の一部が残る。

---

## researchers.csv（1,682行 × 26列）

`authorships.csv` の4,448行を人単位にまとめたもの（`src/aggregate_researchers.py`）。
寄せ方は ORCID が最優先で、無ければ `name_key`（姓＋名の頭文字）。
同じ ORCID にぶら下がる氏名キーは同一人物として統合する。

| カラム | 非NULL | ユニーク | 意味 |
|---|---:|---:|---|
| `cluster_id` | 100% | 1,682 | 主キー。`orcid:...` か `name:...` |
| `canonical_name` | 100% | 1,662 | 代表表記（表記ゆれのうち最も長いもの） |
| `n_name_variants` / `name_variants` | 100% | 8 / 1,667 | 表記ゆれの数と一覧 |
| `orcid` | 30% | 501 | ORCID。`id_source == "orcid"` の行に付く |
| `n_papers` | 100% | 30 | 論文数。中央値1本、5本以上197人、10本以上64人、20本以上18人 |
| `first_year` / `last_year` / `career_span` | 100% | — | 収集済み論文の範囲での活動年。**全キャリアではない** |
| `source_orgs` / `n_source_orgs` | 100% | 12 / 3 | 掲載元サイト。2つ以上に載る人が113人いる（組織横断の共著） |
| `n_first_author` / `n_corresponding` | 100% | — | 筆頭著者・責任著者になった回数 |
| `n_toyota_records` / `toyota_orgs` | 100% / 46% | 26 / 36 | トヨタ系所属の回数と、正規化済みの組織名 |
| `sectors` | 99% | 18 | 所属の業種（university / company / government / hospital / other） |
| `affiliations` | 99% | 861 | 所属文字列の一覧（500字で切る） |
| `primary_fields` | 100% | 134 | 論文の分野（OpenAlex 第2階層）の一覧 |
| `scopus_author_ids` / `openalex_author_ids` | 64% / 99% | — | 保持のみ。**名寄せに使わない**（別人が併合されている） |
| `total_citations` | 100% | 296 | 論文単位に潰してから合計した被引用数 |
| `id_source` | 100% | 2 | `orcid`（501人）か `name_key`（1,181人） |
| `confidence` | 100% | 3 | `high` 501 / `medium` 1,008 / `low` 173。low は名がイニシャルのみ |

**使うときの注意**: `first_year` 以降の年は「トヨタ公式サイトに載った論文」の範囲でしかなく、
その人の全キャリアではない。hot streak のようにキャリア全体を要する解析には使えない。

---

## paper_references.csv（27,247行、790論文分）

各論文が何を引用しているかの一覧。引用関係は OpenAlex のスナップショットから取り、
引用先のタイトルだけ API で補った（`src/build_reference_titles.py`）。

| カラム | 意味 |
|---|---|
| `paper_uid` | `papers.csv` への参照 |
| `paper_title` / `paper_title_site` | 引用元のタイトル（OpenAlex 側 / サイト掲載） |
| `ref_seq` | 参考文献の順番 |
| `ref_work_id` / `ref_doi` / `ref_year` | 引用先の OpenAlex Work ID / DOI / 出版年 |
| `ref_title` | 引用先のタイトル |

1論文あたりの参考文献は中央値31本。`ref_title` が埋まっているのは 94.7% で、
欠損の大半（1,407件）は OpenAlex 側で統合・削除された Work ID。取得漏れではないので再実行しても埋まらない。

同じ内容を `paper_references.json`（`{論文タイトル: [参考文献タイトル, ...]}`）にも出してあるが、
タイトル不明の参考文献を落としており同名タイトルで衝突するため、正確に扱うなら CSV を使う。
