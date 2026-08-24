# データ

## やったこと

トヨタ関連4サイトから論文一覧をスクレイピングし、OpenAlex に対応づけて書誌情報（出版年・被引用・参考文献・分野・著者・所属）を取得した。所属は Crossref と Scopus でも補った。

対応づけは DOI があれば完全一致、なければタイトル照合。919掲載のうち850件が対応づいた。

結果、テーブルは2つ。

| ファイル | 1行＝何か | 行数 | 主キー |
|---|---|---:|---|
| `derived/papers/papers.csv` | 論文1件 | 917 | `paper_uid` |
| `derived/papers/authorships.csv` | 論文の著者1人 | 4,407 | `paper_uid` + `author_seq` |

`paper_uid` は 収集元・タイトル・DOI から作ったハッシュ。行の位置に依存しないので再生成しても変わらない。

---

## papers.csv

| カラム | 非NULL | 意味 |
|---|---:|---|
| `paper_uid` | 100% | 主キー |
| `source_org` | 100% | 収集元サイト（4種） |
| `title_site` | 100% | サイト掲載のタイトル |
| `authors_site` | 66% | サイト掲載の著者名。imra.com は常に空 |
| `venue_site` | 100% | サイト掲載の掲載誌・巻号 |
| `year_site` | 69% | サイト掲載の出版年。**集計に使わない**（imra.com で14%しか埋まらない）。`year_openalex` を使う |
| `link` | 98% | サイトのリンク先 |
| `doi` / `doi_norm` | 70% | `doi_norm` が正規化済み。結合はこちら |
| `toyota_authors_site` | 17% | 未来創成センターのみ。サイトが太字で示した自社所属著者。所属判定の正解ラベル |
| `work_id` | 93% | OpenAlex Work ID。NULL は対応づけ失敗（67件） |
| `match_method` | 93% | `doi_exact` / `title_fuzzy` |
| `match_score` | 93% | タイトル類似度。`doi_exact` は1.0 |
| `review_status` | 93% | `auto` / `accepted_by_review` / `rejected_by_review` |
| `review_decision` / `review_reason` | 1% | 目視判断10件のみ |
| `matched` | 100% | 対応づいたか |
| `is_work_primary` | 100% | **Work単位で集計するときはこれで絞る。** 同じ論文が2サイトに載っている5件を二重に数えないため |
| `matched_title` | 93% | OpenAlex 側のタイトル。目視確認用 |
| `year_openalex` | 93% | **出版年はこちら** |
| `type` | 93% | `article` / `preprint` など |
| `cited_by_count` | 93% | 被引用数 |
| `referenced_works_count` | 93% | 参考文献数。0 の62件は参考文献系の指標を計算できない |
| `n_authors` | 93% | 著者数 |
| `institutions_distinct_count` | 93% | 関与機関数 |
| `primary_topic` / `primary_subfield` / `primary_field` / `primary_domain` | 93% | OpenAlex の分野分類（4階層） |
| `venue_openalex` | 79% | OpenAlex 側の掲載誌名 |
| `openalex_doi` | 92% | OpenAlex 側の DOI。`doi_norm` と食い違えば対応づけを疑う |

## authorships.csv

| カラム | 非NULL | 意味 |
|---|---:|---|
| `paper_uid` | 100% | 主キー1。`papers.csv` への参照 |
| `author_seq` | 100% | 主キー2。著者順（1始まり） |
| `work_id` / `doi` / `source_org` | 100/73/100% | `papers.csv` から持ってきた冗長列。JOIN を省くため |
| `spine` | 100% | 著者リストの取得元 |
| `name_raw` | 100% | 著者名の生文字列 |
| `given` / `family` | 100% | 名 / 姓 |
| `name_key` | 100% | 名寄せキー（`姓\|名の頭文字`） |
| `orcid` | 22% | ORCID |
| `orcid_openalex_raw` / `orcid_crossref` | 22% / 18% | ORCID の出所別。OpenAlex は論文の登録データ由来のみ採用 |
| `affiliation` | 99% | 所属の代表値 |
| `affil_openalex` | 98% | OpenAlex 由来。**最も網羅的だが表記がバラバラ**（豊田中研だけで129表記） |
| `affil_crossref` | 26% | Crossref 由来 |
| `affil_scopus` | 56% | Scopus 由来。**表記が正規化済み（247種）。組織単位の集計はこちら** |
| `inst_openalex` | 94% | OpenAlex が付けた機関名。**判定に使わない**（スイス法人への誤帰属を含む） |
| `openalex_author_id` | 98% | 保持のみ。**名寄せに使わない**（別人が併合されている） |
| `scopus_author_id` | 56% | 保持のみ |
| `is_corresponding` | 100% | 責任著者か |
| `is_toyota` | 100% | 所属がトヨタ系か。豊田工業大学・豊田高専・刈谷豊田総合病院は除外済み |
| `matched_crossref` / `matched_scopus` | 100% | 各DBと突き合わせできたか。DOI がなければ常に False |

