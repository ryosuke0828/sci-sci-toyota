# 付録A: OpenAlex・Semantic Scholar・Web of Science Platform の比較詳細

> この文書は比較軸・データモデル・研究設計の詳細を示す補足資料である。全体の結論、Crossref・Scopusを含む比較、アクセス検証の結果は[総合報告](scholarly_databases_master_report.md)を正本とする。

調査基準日: 2026-07-16  
対象: Science of Science とトヨタ自動車の研究者・技術者の研究活動分析

## 結論

3者は同じ意味での「オープンデータベース」ではない。厳密には、完全な再利用可能データ基盤は **OpenAlex** である。**Semantic Scholar** は無償でAPI・データセットを提供する研究発見基盤だが、API利用には固有の利用許諾・表示義務がある。**Web of Science Platform（WoS）** は高選択性の契約型データベースであり、オープンデータではない。

本プロジェクトでは、次の役割分担が妥当である。

| 役割 | 推奨基盤 | 理由 |
|---|---|---|
| 全件に近い探索、共同著者ネットワーク、再現可能な集計 | OpenAlex | CC0、スナップショット、研究者・組織・助成を結ぶグラフ構造 |
| 技術トピック探索、関連文献候補、埋め込みを使う発見 | Semantic Scholar | 推薦・SPECTER2 埋め込み・機械学習由来の発見機能 |
| 研究評価の感度分析、選択的な索引との照合 | WoS Core Collection | 編集選択と長期の被引用索引。ただし契約・取得上限が前提 |

3基盤の被引用数や著者数を同じ列に混ぜて平均・順位付けしてはならない。収録母集団、参照リンクの作り方、更新時点、重複統合が異なるためである。比較する場合は、同一 DOI・同一文献種別・同一年・同一取得日を固定し、基盤別の値を並列に保持する。

## 1. 比較の前提

### 1.1 「開放性」は三つに分ける

| 観点 | 問い | OpenAlex | Semantic Scholar | WoS Platform |
|---|---|---|---|---|
| 閲覧・少量APIの無償性 | 個人が試せるか | 可。無鍵の小さい日次枠と無料キー枠 | 多くのエンドポイントは無認証でも利用可 | Starter API の試用枠はあるが、機能・件数が限定的 |
| 大規模取得 | 全件または大量を取得できるか | 可。無償の全量スナップショット | 可。ただしダウンロードリンク取得にAPI keyが必要 | 契約プラン・レコード上限に従う |
| データの再利用権 | 再配布・派生データ・監査を行えるか | CC0 | API License Agreement に従う。帰属表示等が必要 | 契約・データ利用規約に従う |

したがって「無料の検索画面がある」と「オープンデータである」は別である。研究の再現性を設計するときは、アクセス可否よりライセンス、スナップショット、取得日時を優先して確認する。

### 1.2 WoS の比較範囲

WoS Platform は Core Collection だけでなく、地域索引・専門索引・外部データベースを含むプラットフォームである。本報告では、書誌計量で中心になる **Web of Science Core Collection** と、そのプログラムアクセスである Starter API / Expanded API を主に比較する。契約に含まれる索引は機関ごとに異なるため、WoS の「件数」は契約構成を明記しなければ比較不能である。

## 2. 基盤ごとの性格とデータモデル

### 2.1 OpenAlex

OpenAlex は論文だけでなく、書籍、データセット、学位論文などを `Works` として扱う知識グラフである。`Authors`、`Institutions`、`Sources`、`Topics`、`Publishers`、`Funders`、`Awards` 等を識別子で接続する。REST API は取得・検索・フィルタ・集約を備え、JSONL と Parquet の全量スナップショットも提供する。[API概要](https://developers.openalex.org/api-reference/introduction) と [データ概要](https://help.openalex.org/hc/en-us/articles/24397285563671-About-the-data) を参照。

主な上流データは MAG、Crossref、ORCID、ROR、DOAJ、Unpaywall、PubMed、リポジトリ、ウェブクロールである。これは広い収録範囲と多様な識別子連結の利点になる一方、上流ごとの欠損・誤記・更新遅れも継承することを意味する。OpenAlex は全データを CC0 とし、無償の公開スナップショットは四半期更新である。2026年7月時点で圧縮JSONL全量は約330 GBと案内されているため、全量解析には保存領域とETL設計が必要である。[認証・料金](https://developers.openalex.org/guides/authentication)、[ダウンロード概要](https://developers.openalex.org/download/overview) を参照。

**得意な分析**

- DOI、ORCID、ROR、OpenAlex IDを軸にした再現可能な文献・組織・助成の結合
- 文献種別を含む広い研究アウトプットの集計
- 引用・共著・機関・トピックをまたぐネットワーク分析
- API照会ではなく固定スナップショットを用いた完全な再実行

**注意点**

- `Concepts` は旧タクソノミーであり、現行APIでは非推奨である。新規分析は `Topics`、`Domains`、`Fields`、`Subfields` を用いる。
- 著者IDと所属の自動名寄せは仮説であり、個人評価や少人数組織の集計前にはORCID、CV、企業ページ等で検証する。
- APIはデータ自体の有償化ではなくサービスの従量型である。無鍵枠は小さく、無料キーは日次1ドル相当の枠であるため、大量照会はキー・キャッシュ・スナップショットを前提にする。
- `referenced_works` は主に基盤内で解決された参照である。文献の参考文献数と一致するとは限らない。

### 2.2 Semantic Scholar Academic Graph (S2AG)

Semantic Scholar は Ai2 が提供する無償のAI支援型研究発見基盤である。Academic Graph API は論文、著者、引用、参考文献、venue、推薦、SPECTER2 埋め込み等を提供し、Datasets API からスナップショット型のJSONデータを取得できる。[API概要](https://www.semanticscholar.org/product/api)、[チュートリアル](https://www.semanticscholar.org/product/api/tutorial) を参照。

Semantic Scholar の強みは、書誌レコードを単なる索引としてではなく、意味的な類似・推薦・要約・埋め込みと結びつける点にある。探索段階では、キーワード一致だけでは見つかりにくい関連研究を候補化する用途に向く。一方で、同社は引用数を自らのコーパスで特定した引用論文に基づいて算出しており、主対象は論文とプレプリントである。書籍の収録は限定的で、特許は含まれないと明示している。[引用数FAQ](https://www.semanticscholar.org/faq/estimated-citations) を参照。

**得意な分析**

- 自然言語・埋め込みによる技術テーマの候補発見
- 論文からの類似論文・推薦論文の探索
- AI、計算機科学、プレプリントを含む早期発見の補助
- APIの `fields` 指定とバッチ取得を用いた軽量なメタデータ照会

**注意点**

- 「無償・オープンな研究支援サービス」と、CC0相当の無条件なデータ再利用は異なる。API License Agreement はAI2側の権利帰属、帰属表示、利用停止・仕様変更の可能性を定めている。[API License Agreement](https://www.semanticscholar.org/product/api/license) を確認する。
- 無認証リクエストは共有レート制限の影響を受ける。API key は一部機能とダウンロードリンク取得で必要であり、初期レートは全エンドポイントで1 RPSと案内されている。
- 推薦、TLDR、埋め込み、influential citation 等のモデル出力は、研究評価のラベルではない。候補発見・感度分析に使い、査定の単独根拠にしない。
- 分野・言語・文献種別によりデータ完全性が変わる。特に書籍、特許、古い文献、企業報告書を含む分析には補助ソースが必要である。

### 2.3 Web of Science Platform

WoS Core Collection は、編集選択を経たジャーナル、会議録、学術書を対象とする引用索引である。Clarivate は、社内編集者による選択、継続的キュレーション、文献・引用メタデータの索引化を特徴としている。[収集・索引化プロセス](https://clarivate.com/academia-government/scientific-and-academic-research/research-discovery-and-referencing/web-of-science/web-of-science-core-collection/content-collection-and-indexing-process/) を参照。提供者の2026年時点の案内では、Core Collection は97百万件超のレコードと24億件の被引用参照を結び、プラットフォーム全体は2.71億件超のレコードを含む。[Core Collection](https://clarivate.com/academia-government/scientific-and-academic-research/research-discovery-and-referencing/web-of-science/web-of-science-core-collection/) を参照。

Starter API はDOI・著者・誌名等による基本照会と、契約状況に応じたTimes Citedを提供する。試用枠は1日50件でTimes Citedを返さない。Expanded API は詳細メタデータ、著者住所・所属、助成情報、引用文献、被引用文献等を扱うが、有償ライセンスが必要で、年間Full Record上限も契約に従う。[Starter API](https://developer.clarivate.com/apis/wos-starter)、[Expanded API](https://developer.clarivate.com/apis/wos) を参照。

**得意な分析**

- 選択的索引を母集団にした研究評価・長期時系列・被引用追跡
- 精査された誌名・文献種別・WoS Category等を使う分析
- 組織の公式な評価報告で、契約済みデータを根拠として使う場面
- OpenAlex等の広い索引で得た結果の感度分析

**注意点**

- WoSはオープンデータではない。API keyだけでは足りず、契約内容が取得対象・日次/年次上限・再利用を規定する。
- 高選択性はノイズ抑制に役立つ一方、地域誌、非英語文献、リポジトリ、プレプリント、データセット等の再現率を下げ得る。収録外を「存在しない」と解釈してはならない。
- WoS Platform全体とCore Collection、機関契約中の索引を混同しない。論文では検索対象データベースと取得日を必ず記録する。

## 3. 多角的比較

| 観点 | OpenAlex | Semantic Scholar | WoS Platform / Core Collection | 研究設計上の含意 |
|---|---|---|---|---|
| 開放性 | データCC0。全量スナップショットあり | 無償利用・ダウンロードあり。ただしAPIライセンスに従う | 契約型。試用APIは限定的 | 成果物の再配布・監査にはOpenAlexが最も扱いやすい |
| 収録哲学 | 多様な上流を統合し、広く収録 | 発見・機械学習利用を重視した統合コーパス | 編集選択された索引 | 広い母集団と選択的母集団は別の推定対象 |
| 主な単位 | Work、Author、Institution、Source、Topic、Funder等 | Paper、Author、Venue、Citation、Embedding等 | 文献レコード、引用文献、被引用文献、研究者・組織プロファイル等 | 共著・組織・助成を一体分析するならOpenAlex、意味探索ならS2 |
| 文献種別 | 記事、書籍、データセット、学位論文等 | 論文・プレプリント中心。書籍は限定的、特許なし | ジャーナル、会議録、書籍を編集方針に基づき収録 | 社内技術報告、特許、標準文書は3者だけで完結しない |
| 引用リンク | 基盤内で解決された引用グラフ | 自コーパスとPDF抽出・出版社連携を基に生成 | WoS索引内の引用・参照を詳細に追跡 | 引用数の絶対値ではなく、基盤内定義を使う |
| 引用コンテキスト | 書誌グラフ中心 | 意味的機能が強い | 一部コンテンツでin-text citation contextを拡張中 | 「なぜ引用されたか」は3者だけでは完全には測れない |
| 著者名寄せ | OpenAlex Author ID、ORCID連結 | Semantic Scholar Author ID | Researcher Profiles等 | 全員を手作業で検証するのではなく、高影響・同姓同名・異動者を優先監査する |
| 所属情報 | authorship単位のinstitution、ROR、国等 | 著者・論文メタデータに依存 | 著者住所・所属を詳細に索引化 | 企業所属分析では論文時点の所属と現在の雇用を分離する |
| 分野分類 | Topicsを中心とする階層 | fields of study、埋め込み・推薦 | WoS Categories、Citation Topics等 | 異分野比較では、同一の分類体系・年・文献種別で正規化する |
| OA・本文 | OA状態、最良OA版、リンク、利用可能な本文取得 | OA PDF、抄録・本文コーパス等 | 契約コンテンツとリンク | 本文分析可否はメタデータの開放性と別に確認する |
| 助成・資金 | Funder、Award、論文上の助成情報 | 項目の充足にばらつき | 助成情報を詳細メタデータとして提供 | 助成別分析は欠損率を最初に報告する |
| API | REST、集約、フィルタ、全量DL | Graph / Recommendations / Datasets API、バッチ | Starter / Expanded等、契約別 | 取得コードはキーをソースに書かず、環境変数とキャッシュを使う |
| 大規模処理 | 四半期スナップショット、Parquet | リリース型JSON、差分API | 契約とデータフィードに依存 | 分析日を固定したスナップショットを保存する |
| 更新と改訂 | レコード・名寄せ・引用リンクが更新される | 日次追加・モデル/コーパス更新があり得る | 日次更新・収録/除外の運用 | 同じコードでも後日の再実行は同じ結果にならない。バージョンを記録する |
| コスト | データは無料、APIサービスはfreemium | 無償だがキー・レート・ライセンス制約 | 主要機能は機関契約 | 研究開始時に「継続費用」と「再現可能性」を分けて見積もる |

## 4. 収録範囲と品質をどう読むか

### 4.1 件数の多寡は優劣ではない

OpenAlexはリポジトリ、プレプリント、地域・非英語圏の出力を取り込みやすく、WoS Core Collectionは選択基準を通ったソースを中心にする。そのため、OpenAlexの出版数がWoSより多いことは、研究活動全体をより広く見ている可能性を示すが、個人・機関の業績が「優れている」ことの証明ではない。

2025年の共有DOIコーパス研究では、OpenAlexの新しい共通文献における参照リンクの被覆はWoS・Scopusと競争的だった一方、ジャーナルごとの過小計上とデータ不整合も観察された。著者ORCIDの広い連結も自動名寄せの過剰結合を含み得ると報告されている。[Reference coverage analysis of OpenAlex compared to Web of Science and Scopus](https://doi.org/10.1007/s11192-025-05293-3) を参照。この結果は「OpenAlexを使えない」ではなく、研究単位・分野・年ごとの検証が必要という意味である。

2026年の個人・機関評価比較でも、出版数はデータベース間で強く一致する一方、引用に基づく順位はより不安定で、OpenAlexとWoS/Scopusの取り替えで四分位が変わる研究者が観察された。[Data source effects in research performance assessment](https://doi.org/10.1007/s11192-026-05638-6) を参照。よって、トヨタ研究者の比較に順位を使う場合は、基盤変更に対する感度分析を必須にする。

### 4.2 引用数は「データベース内の引用数」である

各基盤の被引用数は、同じDOIに対しても異なる。主因は次である。

1. どの引用元文献を収録しているか。
2. 参考文献文字列をどの程度正しく対象文献に解決できるか。
3. プレプリント・出版版・訂正・翻訳版をどう統合するか。
4. オンライン先行、出版日、更新日をどう扱うか。
5. 引用元が後から収録・削除・再名寄せされたか。

そのため、`citations_openalex`、`citations_semantic_scholar`、`citations_wos` を別列にし、`citation_source` と `retrieved_at` を必ず残す。基盤間の値は平均化せず、必要なら「3基盤のうち少なくとも2基盤で上位10%」のような頑健性条件を定義する。

### 4.3 著者・組織の同定は最重要の測定誤差源である

名前検索だけで「トヨタの研究者」を作ると、同姓同名、兼務、転職、子会社名、英語・日本語の表記ゆれ、共同研究先の所属が混ざる。著者IDも完全ではない。したがって、研究者単位の分析は次の順に実施する。

1. 企業の公式ページ、ORCID、研究者本人のCV等から、氏名、別表記、ORCID、在籍期間、部門を持つ基準名簿を作る。
2. 各データベースの著者候補を、DOI、共著者、所属、研究テーマ、年の整合性で照合する。
3. 不確実な候補には `match_status`（confirmed / probable / unresolved / rejected）を付ける。
4. confirmedのみの主分析と、probableを含めた感度分析を並べる。
5. 企業在籍の事実と、論文上の所属を別の変数として保持する。

この手順を省くと、ネットワーク中心性、キャリア年数、引用数の全てが系統的に歪む。

## 5. トヨタ研究活動分析への推奨設計

### 5.1 推奨するデータ層

| 層 | 内容 | 主な情報源 | 必須の記録 |
|---|---|---|---|
| 基準名簿 | 研究者・技術者、在籍期間、別名、ORCID、公開可能な所属 | 公式ページ、本人公開情報 | `person_id`, 根拠URL, 確信度 |
| 文献マスター | DOIを中心とする重複統合前の書誌レコード | OpenAlexを主、S2/WoSを照合 | 元ID、DOI、タイトル、年、種別、取得日 |
| 著者・所属 | 論文時点の著者順、所属、ROR、国 | OpenAlex/WoS、必要に応じ原文 | `work_id`, `author_id`, `institution_id`, 原文所属 |
| 引用・参照 | 基盤別の引用数、引用リンク、時点 | OpenAlexを主、WoSで検証 | `source`, `snapshot_date`, 指標定義 |
| 内容・技術トピック | タイトル、抄録、分類、埋め込み | S2/OpenAlex、必要に応じ本文 | モデル・分類のバージョン |
| 外部成果 | 特許、製品、標準、受賞、共同研究制度 | 専用DB・企業資料 | 文献との対応根拠 |

### 5.2 基盤別の使い方

**OpenAlexを主データにする処理**

- RORや組織lineageを使った企業・大学との共同研究ネットワーク
- 著者・作品・助成・トピックの結合表
- 年別アウトプット、共著チーム規模、国際共同研究比率
- 分析時点を固定したスナップショットによる再現実験

**Semantic Scholarを補助にする処理**

- 自動車、材料、制御、AIなど表記の揺れる技術テーマの関連論文候補の探索
- 代表論文からの推薦・類似文献の探索
- 抄録・埋め込みを用いたクラスタ候補の作成

候補化された結果は、DOI、元タイトル、抄録、原出版社ページで検証する。推薦順位やAI要約を成果・影響の評価値として扱わない。

**WoSを検証に使う処理**

- 機関契約がある場合のCore Collectionに限定した被引用数の照合
- WoS Categoryを使った分野正規化の感度分析
- 組織・研究者の少数サンプルの手動監査

WoSの契約がない段階では、Starter APIの試用範囲でDOI照合の可否を確認し、引用数を欠く試用結果を本分析に混ぜない。

### 5.3 最小の比較実験プロトコル

3者の実測差を判断するには、次の小標本監査を先に行う。

1. 基準名簿で確認済みのトヨタ関連論文を100件程度、年・分野・文献種別で層化抽出する。
2. DOIを正規化し、各基盤を DOI で照会する。タイトル検索を混ぜない。
3. 各基盤ごとに、発見可否、年、文献種別、著者数、確認済み著者の有無、所属、参考文献数、被引用数、OA状態、助成情報を保存する。
4. `missingness` と `agreement` を、全体だけでなく分野・年・文献種別別に集計する。
5. 不一致の大きい20件を原文と照合し、名寄せ、版の重複、収録範囲、メタデータ欠損に分類する。
6. 結果を踏まえ、主分析の基盤、除外規則、WoSによる感度分析の範囲を事前登録する。

この手順なしに、データベース名だけを変えて同じ分析を実施しても、差がデータ品質なのか研究現象なのか判別できない。

## 6. 研究倫理・評価上の注意

- 引用数、h指数、中心性は研究者の価値や能力を直接測るものではない。職種、共同著者慣行、分野、キャリア段階、企業内で公開されない成果に大きく依存する。
- 企業研究者は論文より特許、製品、標準化、社内技術移転で成果を出す場合がある。公開書誌データだけで人事評価を行わない。
- 所属・国籍・氏名表記を機械的な除外規則に使わない。名寄せ不確実性は検証フラグと感度分析で扱う。
- APIの利用規約、個人情報、企業の公開情報の範囲を守る。キーをノートブックやGit履歴に記載しない。

## 7. 実務上の判断表

| 問い | 主基盤 | 補助・検証 | 判断理由 |
|---|---|---|---|
| トヨタ関連の公開研究を広く拾いたい | OpenAlex | S2で関連候補、公式情報で著者確認 | 広いアウトプット種別と再利用性 |
| 新しい技術テーマを探索したい | Semantic Scholar | OpenAlexのTopic・DOIで固定 | 意味的探索は強いが、母集団定義は別途必要 |
| 論文の被引用影響を報告したい | OpenAlexまたはWoSを事前指定 | もう一方で感度分析 | 引用数は交換可能でない |
| 企業・大学間の共同研究構造を描きたい | OpenAlex | ROR、原文所属、WoS | 組織IDと共著関係を扱いやすい |
| 公式な機関評価に近い比較をしたい | WoS（契約範囲を明記） | OpenAlexで網羅性の感度分析 | 選択的索引の定義を明示できる |
| 全ての結果を他者が再計算できるようにしたい | OpenAlex snapshot | S2/WoSは照合列として保存 | ライセンスと固定スナップショットの点で有利 |

## 8. 参照資料

### 公式資料

- [OpenAlex Developers: API Overview](https://developers.openalex.org/api-reference/introduction)
- [OpenAlex Developers: Authentication & Pricing](https://developers.openalex.org/guides/authentication)
- [OpenAlex Developers: Data Downloads](https://developers.openalex.org/download/overview)
- [OpenAlex Help: About the data](https://help.openalex.org/hc/en-us/articles/24397285563671-About-the-data)
- [Semantic Scholar: Academic Graph API Overview](https://www.semanticscholar.org/product/api)
- [Semantic Scholar: API Tutorial and Datasets](https://www.semanticscholar.org/product/api/tutorial)
- [Semantic Scholar: API License Agreement](https://www.semanticscholar.org/product/api/license)
- [Semantic Scholar: Citation-count FAQ](https://www.semanticscholar.org/faq/estimated-citations)
- [Clarivate: Web of Science Starter API](https://developer.clarivate.com/apis/wos-starter)
- [Clarivate: Web of Science Expanded API](https://developer.clarivate.com/apis/wos)
- [Clarivate: Web of Science Core Collection](https://clarivate.com/academia-government/scientific-and-academic-research/research-discovery-and-referencing/web-of-science/web-of-science-core-collection/)
- [Clarivate: Content collection and indexing process](https://clarivate.com/academia-government/scientific-and-academic-research/research-discovery-and-referencing/web-of-science/web-of-science-core-collection/content-collection-and-indexing-process/)

### 比較研究

- [Maddi et al. (2025), Reference coverage analysis of OpenAlex compared to Web of Science and Scopus](https://doi.org/10.1007/s11192-025-05293-3)
- [Alonso-Alvarez & van Eck (2024), Coverage and metadata availability of African publications in OpenAlex](https://arxiv.org/abs/2409.01120)
- [Data source effects in research performance assessment of individuals and institutions (2026)](https://doi.org/10.1007/s11192-026-05638-6)

各資料の件数、料金、API上限、収録対象は更新され得る。分析実行時にはURL、取得日時、契約範囲、APIレスポンスまたはスナップショット識別子を成果物に保存する。
