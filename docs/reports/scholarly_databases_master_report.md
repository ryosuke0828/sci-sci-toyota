# Science of Science研究のための学術データベース調査・アクセス検証総合報告

調査基準日: 2026-07-16  
対象: トヨタ自動車の研究者・技術者の研究活動、共同研究、知識生成を対象とする Science of Science 研究

## 要約

本研究の主データ基盤には **OpenAlex** を使う。理由は、文献・著者・所属・引用・助成を識別子で結び、CC0のデータとスナップショットを用いて再現可能な分析を設計できるためである。

他の基盤は主データを置き換えるのではなく、次の役割で併用する。

| 基盤 | 位置付け | 主な用途 |
|---|---|---|
| OpenAlex | 主データ | 候補抽出、共著・引用ネットワーク、機関・助成・トピックの結合、再現実行 |
| Crossref | 識別子・書誌の補完 | DOI正規化、タイトル・出版社等の照合 |
| Semantic Scholar | 意味的探索の補助 | 類似研究・技術テーマの候補発見、限定的なメタデータ照会 |
| Scopus | 契約型の検証データ | 限定標本での収録・引用指標の感度分析 |
| Web of Science (WoS) | 契約型の検証データ | Core Collection等の選択的索引を用いる感度分析・評価文脈の照合 |

Scopus と WoS は「オープンデータベース」ではない。機関契約で利用する検索・引用索引であり、Web画面へのアクセス、API利用、データ再利用の許諾は別に確認する必要がある。Semantic Scholar も無条件のオープンデータではなく、API利用許諾とレート制限に従う。OpenAlex と Crossref は公開データ・公開メタデータとして使いやすいが、収録範囲や欠損を前提に扱う。

## 1. 調査の範囲と判断基準

本報告は、データベースの優劣を単純に順位付けするものではない。以下の五つを分けて判断する。

1. **閲覧・少量照会の可否**: Web画面またはAPIに到達できるか。
2. **プログラム取得の可否**: 公式API・スナップショットで必要なメタデータを取得できるか。
3. **再利用性**: ライセンス上、分析結果・派生データ・コードをどこまで共有できるか。
4. **測定対象**: どの文献種別・分野・地域・時期を母集団とするか。
5. **再現性**: 取得日、検索条件、API仕様、データ版を固定できるか。

したがって、無料の検索画面があること、所属機関から閲覧できること、APIで全件を取得できること、データを再配布できることは同義ではない。

## 2. 基盤別の比較

| 観点 | OpenAlex | Crossref | Semantic Scholar | Scopus | WoS Platform / Core Collection |
|---|---|---|---|---|---|
| 性格 | オープンな学術知識グラフ | DOI登録メタデータ基盤 | AI支援の研究発見・Academic Graph | 契約型の抄録・引用索引 | 契約型の選択的引用索引・プラットフォーム |
| 主な単位 | Work、Author、Institution、Source、Topic、Funder等 | DOI、作品、出版物、登録機関 | Paper、Author、Citation、Venue、埋め込み等 | 文献、著者、機関、引用 | 文献、引用文献・被引用文献、研究者・機関等 |
| 開放性・利用条件 | データはCC0。API・スナップショットを利用 | REST APIは登録不要。登録済みメタデータが対象 | 多くのAPIは公開だが、ライセンス・レート制限あり | 機関契約・APIキー・利用条件に従う | 機関契約・APIプラン・利用条件に従う |
| 強み | 広い母集団、識別子結合、再現可能な全体分析 | DOIを軸にした書誌照合 | 類似研究・推薦・意味的探索 | 選択的な書誌・引用データでの照合 | 長期引用索引、Core Collection等の評価文脈 |
| 主な限界 | 著者・所属名寄せ、上流データの欠損・改訂 | 登録内容・参照情報の欠損、引用母集団の限定 | 収録・モデル出力・レート制限、CC0ではない | 契約・取得上限・再利用制約 | 契約・取得上限・選択性による収録バイアス |
| 本研究での役割 | 主分析 | DOI正規化・補完 | 探索の補助 | 限定標本の感度分析 | 限定標本の感度分析 |

### 2.1 OpenAlex

OpenAlex は、論文だけでなく書籍、データセット、学位論文などを `Works` として扱い、著者、所属、出版物、トピック、助成等を識別子で接続する。主分析で必要になる共著ネットワーク、引用ネットワーク、研究者・組織単位の集計を一つのデータモデルで実施できる。データはCC0であり、APIだけでなくスナップショットを固定入力にできる。[OpenAlexのデータ概要](https://help.openalex.org/hc/en-us/articles/24397285563671-About-the-data)、[API認証・利用枠](https://developers.openalex.org/guides/authentication)

ただし、著者ID・所属・企業名の自動名寄せは確定事実ではない。トヨタ研究者の分析では、ORCID、DOI、所属表記、企業サイト・CV等による監査を組み込む必要がある。少人数群、同姓同名者、異動者、高被引用者を優先して確認する。

### 2.2 Crossref

Crossref はDOIを中心とする書誌メタデータの公開基盤である。REST APIは登録不要で利用でき、作品、ジャーナル、出版者、助成者等を照会できる。[Crossref REST API](https://www.crossref.org/documentation/retrieve-metadata/rest-api/)

本研究では、OpenAlex等から得た文献の DOI を正規化し、タイトル・出版年・ISSN・出版者を照合する補助基盤として使う。Crossrefの引用関係・被引用数は、登録された参照情報とCited-by参加状況に依存するため、研究全体の引用ネットワークを単独で代表させない。[Crossref Cited-by](https://www.crossref.org/documentation/cited-by/)

### 2.3 Semantic Scholar

Semantic Scholar Academic Graph は、論文・著者・引用関係に加え、類似研究、推薦、埋め込み等を提供する。技術テーマが近い研究や関連文献の候補を広げる用途に向く。[Semantic Scholar API](https://www.semanticscholar.org/product/api)

多くのエンドポイントは無認証で使えるが、共有レート制限を受け、混雑時には追加のスロットリングがある。認証付きAPIキーを使う場合も、利用許諾とレート制限に従う。Semanticな類似性や influential citation 等のモデル出力は、研究者評価の確定ラベルではなく探索候補として扱う。[API License Agreement](https://www.semanticscholar.org/product/api/license)

### 2.4 Scopus

Scopus は、文献・抄録・引用情報、著者・機関プロファイルを扱う契約型の学術データベースである。大阪大学附属図書館は学外アクセス用リンクを提供し、文献検索と引用文献参照を案内している。[大阪大学附属図書館: データベース一覧](https://www.library.osaka-u.ac.jp/resource/database/dblist/)

Scopus APIはElsevier Developer PortalでAPIキーを申請する。学術・公的機関等の非商用利用には無償の選択肢が案内されているが、実際の項目・上限・ネットワーク条件・再利用範囲はキーと契約条件による。[Scopus APIs](https://dev.elsevier.com/sc_apis.html) Web UI上のエクスポート可能件数は、APIによる収集または再配布の許可を意味しない。[Scopus export support](https://service.elsevier.com/app/answers/detail/a_id/11234/supporthub/scopus/)

### 2.5 Web of Science

WoSは、Web of Science Core Collectionを中心に引用関係を索引化する契約型のデータベースである。大阪大学の契約案内には Core Collection、Citation Connection、特許・データ関連の索引等が示されている。分析時には、Core Collection単独か横断検索か、どの索引を対象にしたかを記録する。[大阪大学附属図書館: データベース一覧](https://www.library.osaka-u.ac.jp/resource/database/dblist/)

WoS Starter APIは基本メタデータ・引用数の照会に向く。Clarivateは試用プランを1日50リクエスト・被引用数なし、WoS契約機関の構成員向けプランを被引用数あり・1日5,000リクエストとして案内している。詳細なFull Record、住所・所属、助成、引用・被引用文献を扱う Expanded API は有償ライセンスが必要である。[WoS Starter API](https://developer.clarivate.com/apis/wos-starter)、[WoS Expanded API](https://developer.clarivate.com/apis/wos)

### 2.6 Web UIで利用する機能の整理

下表は公式案内に基づく機能であり、今回の認証済みセッションで実査した結果ではない。認証後に利用可能な範囲は、大阪大学の契約内容とログイン後の表示で確定する。

| 基盤 | Web UIで確認・利用したい機能 | 研究での使い方 |
|---|---|---|
| Scopus | 文献検索、引用文献・被引用情報、著者・機関プロファイル、選択した結果のエクスポート | OpenAlexで作った DOI 一致標本の収録確認、著者名寄せの補助、被引用数の感度分析 |
| WoS | Core Collectionまたは横断検索、引用文献・被引用文献、被引用数、索引・文献種別の絞込み | Core Collectionを明示した限定標本の収録確認、被引用数・引用関係の感度分析 |

Scopusのエクスポートは認証後に実行する手順であり、UI上のエクスポート上限はAPI・再配布の許可とは別である。[Scopus export support](https://service.elsevier.com/app/answers/detail/a_id/11234/supporthub/scopus/) WoSでは、Core Collectionと横断検索で対象が異なるため、どちらで検索したかを分析記録に残す。[大阪大学附属図書館: データベース一覧](https://www.library.osaka-u.ac.jp/resource/database/dblist/)

## 3. 実行済みのアクセス検証

検証日時: 2026-07-16T00:59:22Z  
対象 DOI: `10.1126/science.aaf5239`（Sinatra et al., *Science*, 2016）  
実装: [アクセス検査ノートブック](../../notebooks/access_checks/scholarly_database_access_check.ipynb)  
生データを含まない出力: [JSON](../../data/derived/access_check/access_check_summary.json)、[CSV](../../data/derived/access_check/access_check_summary.csv)

| 対象 | 実測結果 | 判断 |
|---|---|---|
| Crossref REST API | HTTP 200。タイトル、2016年、被引用数499を取得 | この実行環境から公開メタデータAPIへ到達できた |
| Semantic Scholar API | HTTP 429 | 共有・無認証利用のレート制限。収録なし・利用不可を意味しない |
| Scopus Web UI 学外アクセス入口 | HTTP 302で `ou-idp.auth.osaka-u.ac.jp` へ遷移。既存Chromeでも認証ページを表示 | 大阪大学のSAML認証入口まで到達できた。この時点では再認証が必要で、認証後のコンテンツは未検査 |
| WoS Web UI 学外アクセス入口 | HTTP 302で `ou-idp.auth.osaka-u.ac.jp` へ遷移。既存Chromeでも認証ページを表示 | 大阪大学のSAML認証入口まで到達できた。この時点では再認証が必要で、認証後のコンテンツは未検査 |
| Scopus API | 未照会 | `SCOPUS_API_KEY` が未設定。無許可の推測・取得は行わない |
| WoS Starter API | 未照会 | `WOS_API_KEY` が未設定。無許可の推測・取得は行わない |

この検査では個人ID、パスワード、認証Cookie、APIキーを使わず、保存もしていない。学外アクセスの302は認証入口への到達を示すだけで、Scopus/WoS内のレコード閲覧・API権限・エクスポート権限を証明するものではない。

実機Chromeについても、Scopus と WoS の学外アクセス入口をそれぞれ1回だけ開き、タブのタイトルのみを確認した。両方で「大阪大学 全学 IT 認証基盤サービス」が表示されたため、この時点では有効な大阪大学SSOセッションがなく、再認証が必要だったと判断した。ページ本文、URLのクエリ文字列、Cookie、保存済みパスワードは読み取らず、WoS用に開いた検査ウィンドウは閉じた。この結果は、機関契約の有無ではなく、認証済みセッションがないことだけを示す。

大阪大学の学外アクセスは個人IDによる認証を必要とし、利用できるのはライセンス上許可された大阪大学構成員に限られる。[キャンパス外から電子リソースを使う](https://www.library.osaka-u.ac.jp/resource/off_campus/) また、自動ダウンロードだけでなく、手動の短時間大量ダウンロード、ブラウザの先読み、文献管理ツールによる全文自動収集も禁止対象になり得る。[電子リソースの利用条件](https://www.library.osaka-u.ac.jp/resource/epolicy/)

## 4. 研究用のデータ設計

以下の層を分けることで、再現性と契約遵守を両立させる。

```text
OpenAlexの固定キャッシュ / スナップショット
  ├─ DOI・書誌の照合 → Crossref
  ├─ 技術テーマ・関連研究の候補発見 → Semantic Scholar
  └─ DOI一致の限定標本による感度分析 → Scopus / WoS の公式API
                                             （利用権が確認できた場合のみ）
```

各文献について、少なくとも次を別列・別ファイルで保存する。

| 項目 | 保存方針 |
|---|---|
| 同定子 | DOI、OpenAlex Work ID、OpenAlex Author ID、ORCID、ROR、Scopus ID/WoS ID（利用できる場合） |
| 出所 | `source_database`、対象索引、検索式、APIエンドポイントまたはスナップショット版 |
| 時点 | `retrieved_at`、公開年、データセット版、キャッシュ名 |
| 書誌情報 | タイトル、文献種別、誌名、ISSN、出版年、著者順、論文時点の所属 |
| 指標 | `cited_by_openalex`、`cited_by_scopus`、`times_cited_wos` 等を別列に保存 |
| 検証状態 | 著者・所属・DOIの確認方法、未確定理由、確認日 |

被引用数をデータベース横断で平均・合算・順位化してはならない。各値は各基盤が定義する収録母集団・引用リンク・更新時点の下での値である。同一 DOI、同一年、同じ文献種別、同じ取得日を固定し、基盤別の差を感度分析として報告する。

## 5. トヨタ研究活動分析への適用

1. **候補研究者の作成**: トヨタ関連の所属表記、既知の研究者、ORCID、企業ページ等から候補を作る。
2. **著者同定の監査**: OpenAlexの著者IDを出発点に、同姓同名、異動、共同所属、高影響研究者を重点確認する。
3. **主分析**: 固定したOpenAlex入力から、出版量、共著構造、引用ネットワーク、トピック推移、所属間連携を分析する。
4. **書誌の補完**: CrossrefでDOI・書誌の不整合を検出・補完する。
5. **意味的探索**: Semantic Scholarは、研究テーマ・関連研究・候補文献を発見する補助として使う。
6. **頑健性確認**: 利用権が確定したScopus/WoSから、同一 DOI の限定標本を取り、収録有無・被引用数・文献種別の差を比較する。

企業研究者の研究活動は論文だけでは完結しない。特許、標準、社内報告、共同研究契約、研究部門の異動等は別ソースを必要とする。学術データベースにないことを「活動がない」と解釈しない。

## 6. 現在の到達点と未解決事項

| 区分 | 到達点 | 次に必要なこと |
|---|---|---|
| 主データ | OpenAlexを主分析に使う設計を確定 | 対象研究者の同定基準・固定入力を作る |
| DOI補完 | Crossref APIの疎通を確認 | DOI照合処理を対象データへ適用 |
| 意味的探索 | Semantic Scholarの公開APIを確認 | 429回避のためのキー取得または低頻度再試行を設計 |
| Scopus | 学外アクセス入口がSAMLへ遷移することを確認 | APIキー、利用項目、上限、再利用条件を公式窓口で確定 |
| WoS | 学外アクセス入口がSAMLへ遷移することを確認 | Starter APIの機関向けプラン、Expanded APIの利用権を公式窓口で確定 |
| 規約遵守 | 秘密情報非保存・大量取得禁止を確認 | APIで取得量・頻度・保存範囲を明示して実行 |

Scopus/WoSの認証後コンテンツやAPI権限は、個人ID・パスワードの共有で解決しない。公式APIキーと契約上の許可を使う必要がある。外部窓口への照会文は[アクセス確認と利用計画](scholarly_database_access_plan.md)に整理している。

### 6.1 図書館回答（2026-07-17・2026-07-21受領）

阪大図書館から回答を受領し、次が確定した。

| 項目 | 回答内容 |
|---|---|
| Scopus API | 研究目的で利用可能（R26-085） |
| WoS API | Starter APIのみ利用可能。Expanded APIは契約外（R26-086） |
| WoS Starter APIの制約 | 著者住所・所属、ORCID、Org Enhancedを含まない。Times CitedはCore Collection限定 |
| APIキー取得 | Scopus・WoSとも伊倉涼介本人がdev.elsevier.com／Clarivate Developer Portalで個別申請する必要がある |

詳細な回答内容・レート制限・フィールド一覧は[アクセス確認と利用計画](scholarly_database_access_plan.md)、恒久的な運用ルールは[AGENTS.md](../../AGENTS.md)に記載した。

### 6.2 次に行う作業

Scopus・WoSともAPIキー発行は伊倉涼介本人の個人申請が必要（大阪大学の契約はあるが、キー自体は個人のアカウントに紐づくため）。申請手順・完了条件は[log.md](../../log.md)の進行中タスクを参照。APIキー取得後は、キーをローカル環境変数に設定するだけでよく、値そのものをAIエージェントへ共有する必要はない。取得設計・検証・実行はAIエージェントが引き継ぐ。

## 7. 文書構成

本報告を正本とする。以下は詳細根拠・補足として残す。

| 文書 | 役割 |
|---|---|
| [OpenAlex・Semantic Scholar・WoSの比較詳細](academic_database_comparison.md) | データモデル、比較軸、分析設計の詳細 |
| [アクセス確認と利用計画](scholarly_database_access_plan.md) | 実測結果、API利用条件、図書館への照会文 |
| [Random Impact Ruleの外的再現](random_impact_rule_reproduction.md) | 既存Science of Science研究の再現結果 |
| [h指数予測力の再現](h_index_prediction.md) | 既存Science of Science研究の再現結果 |

## 8. 主要な公式資料

- [OpenAlex API](https://developers.openalex.org/api-reference/introduction)
- [OpenAlex data overview](https://help.openalex.org/hc/en-us/articles/24397285563671-About-the-data)
- [Crossref REST API](https://www.crossref.org/documentation/retrieve-metadata/rest-api/)
- [Semantic Scholar API](https://www.semanticscholar.org/product/api)
- [Elsevier Scopus APIs](https://dev.elsevier.com/sc_apis.html)
- [Clarivate WoS Starter API](https://developer.clarivate.com/apis/wos-starter)
- [Clarivate WoS Expanded API](https://developer.clarivate.com/apis/wos)
- [大阪大学附属図書館: データベース一覧](https://www.library.osaka-u.ac.jp/resource/database/dblist/)
- [大阪大学附属図書館: 学外アクセス](https://www.library.osaka-u.ac.jp/resource/off_campus/)
- [大阪大学附属図書館: 電子リソース利用条件](https://www.library.osaka-u.ac.jp/resource/epolicy/)
