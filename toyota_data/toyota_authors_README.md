# toyota_authors.csv データセット説明

トヨタ自動車(海外現地法人を含む)に**過去一度でも所属したことのある研究者**の一覧。
OpenAlex Authors API から取得し、1行 = 1研究者(OpenAlex著者ID単位)に整形したもの。

- 生成スクリプト: `fetch_toyota_authors.py`
- データソース: `https://api.openalex.org/authors?filter=affiliations.institution.id:<エンティティID>`
- 取得日: 2026-07-17(OpenAlexは日次更新のため、再実行すると件数は微増しうる)
- 行数: **9,429名**(うち現所属フラグ True: **3,763名**)、列数: 43
- 文字コード: UTF-8(BOM付き、Excelでそのまま開ける)

## 1. 対象エンティティ

OpenAlex上で Toyota Motor Corporation (Japan) の系列(lineage)に属する8機関を対象とした。
**豊田自動織機・豊田中央研究所・Toyota Research Institute は含まない**(これらはトヨタグループ配下だがトヨタ自動車系列ではないため)。

| OpenAlex ID | 名称 | 実体 | 研究者数 | うち現所属 |
|---|---|---|---:|---:|
| I4210137853 | Toyota Motor Corporation (Japan) | 日本本体(トヨタ自動車株式会社) | 4,395 | 2,026 |
| I1293612202 | Toyota Motor Corporation (Switzerland) | 名目上はスイス法人。**ただし注意(§3)** | 5,788 | 2,050 |
| I4210093665 | Toyota Motor North America (United States) | 北米統括会社 | 588 | 268 |
| I4210129182 | Toyota Motor Corporation (Germany) | ドイツ現地法人 | 264 | 133 |
| I4210120547 | Toyota Motor Corporation (Belgium) | ベルギー法人(所属表記上は Toyota Motor Europe, Zaventem が主) | 167 | 108 |
| I4210130561 | The Toyota Foundation | トヨタ財団(助成財団。現地法人ではないが系列配下のため含む) | 15 | 4 |
| I4210165215 | Toyota Motor Corporation (Canada) | カナダ現地法人 | 6 | 2 |
| I4405261461 | Toyota Motor North America Research & Development (United States) | 北米R&D(該当著者なし) | 0 | 0 |

- 複数エンティティに該当する研究者が **1,504名** いるため、各行の合計はユニーク数(9,429)を上回る。
- 「うち現所属」は「最新所属に上記いずれかのトヨタ系機関を含む」の意味であり、そのエンティティに現所属という意味ではない。

## 2. 列の説明

### 識別子
| 列 | 内容 |
|---|---|
| `openalex_id` | OpenAlex著者ID(例: A5100368058)。`https://openalex.org/<ID>` でプロファイル閲覧可 |
| `name` | 代表表記の著者名 |
| `orcid` | ORCID(保有者のみ。全体で3,144名=33%、現所属者では413名=11%) |

### フィルタ用フラグ
| 列 | 内容 |
|---|---|
| `is_currently_affiliated` | 最新所属(`last_known_institutions`)にトヨタ系エンティティを含むか。OpenAlex側でこのフィールドが空の著者は False(非所属)として扱った |
| `matched_entities` | 該当したエンティティ名の一覧(「; 」区切り) |
| `entity_*`(8列) | エンティティ別の該当フラグ(True/False)。`matched_entities` と同じ情報のワンホット表現で、Excelのオートフィルタ用 |

### 業績指標(いずれも**キャリア全体**の値。トヨタ在籍中に限定した値ではない)
| 列 | 内容 |
|---|---|
| `works_count` | 総著作数。査読論文のほかプレプリント・学会発表等を含むため、いわゆる「論文数」より多めに出る |
| `cited_by_count` | 総被引用数 |
| `h_index` / `i10_index` | h指数 / 被引用10回以上の著作数 |
| `two_yr_mean_citedness` | 直近2年の平均被引用(ジャーナルのインパクトファクター相当の著者版) |
| `first_pub_year` / `last_pub_year` | 業績の最初と最後の年(`counts_by_year` の最小・最大年)。キャリア長の推定に使える |

### 研究トピック(OpenAlexの4階層分類: domain > field > subfield > topic)
| 列 | 内容 |
|---|---|
| `topic_1` 〜 `topic_5` | その研究者の著作数が多い順の上位5トピック |
| `topic_k_subfield` / `topic_k_field` / `topic_k_domain` | 各トピックの上位階層。分野での集計には `topic_1_field` を使うのが基本 |

### 所属・ノイズ点検用
| 列 | 内容 |
|---|---|
| `other_affiliations` | トヨタ系以外の所属機関(在籍年範囲付き、「; 」区切り) |
| `n_affiliations` | 所属機関の総数 |
| `n_last_known_institutions` | 最新所属の機関数 |

## 3. データの質に関する注意(俯瞰の要点)

1. **スイス法人エンティティ(5,788名)は機関判定の誤りを大量に含む。**
   論文上の生所属表記を抽出調査したところ、「Toyota Motor Co., Ltd(豊田市)」「Toyota Central R&D Labs」など日本本体や豊田中研の表記がこのエンティティに紐づいている例が多数確認された。日本本体のみに限定する場合も、スイス法人分を単純に除外すると取りこぼしが生じる点に注意。
2. **著者名寄せ(同名混同)のノイズ。** `first_pub_year` が1950年以前の研究者が324名おり、大半は複数人が1つのIDに統合された混同プロファイルと考えられる。`n_affiliations` が100超(79名)、`n_last_known_institutions` が10超(19名)も同様の疑いが強い。これらの列で降順ソートするとノイズの実例を確認できる。
3. **分野分布にもノイズが現れている。** 主トピック(topic_1)の field 別では Engineering 3,812名、Materials Science 979名など自動車企業として自然な分布の一方、Medicine が1,236名と多い。これは主にスイス法人エンティティへの誤紐づけ(医学系研究者の混入)による。
4. 指標はすべてキャリア全体の値のため、「トヨタ在籍中の業績」を見る場合は論文単位の追加集計が必要。

## 4. 想定される使い方

- トヨタ側へ渡す版: `is_currently_affiliated = TRUE` でフィルタ(3,763名)
- 日本本体に限定: `entity_motor_corporation_japan = TRUE` でフィルタ(ただし§3-1の取りこぼしに注意)
- ノイズの目視確認: `first_pub_year` 昇順、または `n_affiliations` 降順にソート
