# 付録B: 学術データベースのアクセス確認と利用計画

> この文書は到達性検査、認証・契約上の確認事項、図書館への照会文を示す補足資料である。全体の結論とデータ設計は[総合報告](scholarly_databases_master_report.md)を正本とする。

確認日: 2026-07-16（JST）  
対象: OpenAlex を主データ源とする Science of Science 研究での Crossref、Semantic Scholar、Scopus、Web of Science（WoS）の利用

## 結論

大阪大学の個人 ID・パスワードを共有する必要はない。Scopus と WoS の **Web画面への機関アクセス** は、本人が大阪大学附属図書館の学外アクセス用リンクから確認する。一方、両者の **API利用** は別の API キーと契約・利用条件が必要である。Web画面に入れることだけでは、プログラムによる収集が許可されるとはいえない。

本リポジトリでは、OpenAlex を再現可能な主データ、Crossref を DOI 正規化、Semantic Scholar を意味的な探索、Scopus と WoS を限定標本の検証・感度分析に位置付ける。Scopus と WoS は「オープンデータベース」ではなく、機関契約型のデータベースである。

## 1. 今回の技術的な到達性検査

対象 DOI を `10.1126/science.aaf5239`（Sinatra et al., 2016）に固定し、1件だけを照会した。Web画面の実閲覧・大量取得・個人認証は行っていないが、Scopus と WoS の大阪大学学外アクセス入口へ接続し、認証前のリダイレクトを検査した。実装は [アクセス検査ノートブック](../../notebooks/access_checks/scholarly_database_access_check.ipynb)、出力は [JSON](../../data/derived/access_check/access_check_summary.json) と [CSV](../../data/derived/access_check/access_check_summary.csv) にある。

| 基盤 | 今回の結果 | 解釈 | 次の操作 |
|---|---|---|---|
| Crossref | HTTP 200、書誌情報を取得 | 公開 REST API にこの環境から到達できた | DOIの正規化・メタデータ補完に利用可能 |
| Semantic Scholar | HTTP 429 | 認証なし共有IPでレート制限された。収録されていない、または利用権がないという意味ではない | 時間を置くか、本人が発行した API キーをローカル環境変数に設定して再実行 |
| Scopus Web UI（大阪大学学外アクセス） | HTTP 302、`ou-idp.auth.osaka-u.ac.jp` へリダイレクト。既存Chromeでも認証ページを表示 | 大阪大学学外アクセスの SAML 認証入口まで到達できた。この時点では再認証が必要で、認証後の画面・データは未検査 | Web UIではなく、公式APIまたは図書館への契約照会で研究用アクセスを確定 |
| WoS Web UI（大阪大学学外アクセス） | HTTP 302、`ou-idp.auth.osaka-u.ac.jp` へリダイレクト。既存Chromeでも認証ページを表示 | 大阪大学学外アクセスの SAML 認証入口まで到達できた。この時点では再認証が必要で、認証後の画面・データは未検査 | Web UIではなく、公式APIまたは図書館への契約照会で研究用アクセスを確定 |
| Scopus | 未照会 | `SCOPUS_API_KEY` が未設定のため、意図的に API を呼ばなかった | APIキーと利用条件を確認後、同じ 1 DOI 検査を実行 |
| WoS Starter API | 未照会 | `WOS_API_KEY` が未設定のため、意図的に API を呼ばなかった | Clarivate のアプリ登録・APIキーと契約プランを確認後に実行 |

Crossref の REST API は登録不要で利用できると明記されている。[Crossref REST API](https://www.crossref.org/documentation/retrieve-metadata/rest-api/)  
Semantic Scholar は多くのエンドポイントを無認証で公開しているが、無認証利用は共有レート制限を受け、混雑時には追加のスロットリングがあり得る。[Semantic Scholar API](https://www.semanticscholar.org/product/api)

## 2. 大阪大学経由の Web UI 確認

大阪大学附属図書館のデータベース一覧には、Scopus と WoS の両方に「Off Campus Access」リンクがある。Scopus は文献検索と引用文献参照、WoS は書誌・引用・データリポジトリ・特許情報の検索を案内している。[大阪大学附属図書館: データベース一覧](https://www.library.osaka-u.ac.jp/resource/database/dblist/)

学外アクセスには、`u` から始まる大阪大学個人IDとパスワードでの認証が必要で、ライセンス上利用可能な大阪大学構成員に限られる。接続後のURLに `osaka-u.idm.oclc.org` が含まれることを確認する。Cookieの競合時は別ブラウザまたはプライベートウィンドウを使うよう図書館が案内している。[キャンパス外から電子リソースを使う](https://www.library.osaka-u.ac.jp/resource/off_campus/)

Web画面の確認はエージェントが行う。今回、両方の学外アクセス入口が大阪大学の SAML 認証基盤へリダイレクトすること、および既存Chromeのタブが両方で大阪大学の認証ページを表示することを確認した。個人ID・パスワード・認証Cookieを受け取らず、ページ本文・URLクエリ・Cookie・保存済みパスワードも読み取らない。認証済みWeb UI でしか確認できない項目は、公開ページ、公式API、契約済みのプログラムアクセス、図書館への契約照会で確定する。

大阪大学は、プログラムによる短時間の大量ダウンロードだけでなく、手動で短時間に次々とダウンロードすること、ブラウザの先読み、文献管理ツールの全文自動収集も禁止対象になり得ると明記している。[電子リソースのご利用にあたって](https://www.library.osaka-u.ac.jp/resource/epolicy/)

## 3. API 利用の可否と実務上の分岐

### Crossref

公開 API を使える。DOI、タイトル、著者、出版年、出版元、ライセンス、登録済みの参照情報を補完するために使う。出版社が登録したメタデータの欠損は残るため、引用ネットワークの唯一の母集団にはしない。

### Semantic Scholar

公開 API は探索に使えるが、今回のように共有環境では 429 を返すことがある。APIキーを発行すると、認証付きのレート上限が適用される。キーはメールで届く私的な値であり、公式にも共有しないよう案内されている。[Semantic Scholar API](https://www.semanticscholar.org/product/api)

### Scopus（2026-07-21 阪大図書館 R26-085 回答で確定）

大阪大学の契約でScopus APIは研究目的で利用できることが図書館から確認された。APIキーは `dev.elsevier.com` で伊倉涼介本人がサインインして取得する。既定の認証方式はIPアドレス認証で、**阪大の契約IPアドレス範囲内からのアクセスが前提**。学外・別ネットワークから使う場合はinsttokenの追加申請が必要。[Scopus APIs](https://dev.elsevier.com/sc_apis.html)

APIキーには週間クォータがある（Author Retrieval・Affiliation Retrieval・Affiliation Search・Author Search: 週5,000件、Abstract Retrieval: 週10,000件、Scopus Search・Abstract Citation Count・Serial Title: 週20,000件）。Citation Overview API、refEIDフィールド、Index Keywordフィールド、Affiliation/Author RetrievalのDOCUMENTSビューは追加申請制。詳細な上限緩和はエルゼビアのData as a Service Support Centerへ申請する。

Web UI からのエクスポートには認証が求められる。検索結果のエクスポート上限があっても、それは API による収集の許可や再配布の許可を意味しない。[Scopus export support](https://service.elsevier.com/app/answers/detail/a_id/11234/supporthub/scopus/)

### Web of Science（2026-07-17 阪大図書館 R26-086 回答で確定）

大阪大学の契約で使えるのは **Web of Science Starter API のみ**。Expanded APIの契約は含まれない。大阪大学の Web UI 契約には Core Collection、Citation Connection、特許・データ等を含む複数のコンテンツが示されているが、これはWeb UI契約であり、API契約とは別である。[大阪大学附属図書館: データベース一覧](https://www.library.osaka-u.ac.jp/resource/database/dblist/)

WoS Starter API は基本メタデータと Times Cited（**Core Collection限定の被引用数**）に使えるが、**著者住所・所属(affiliation)、Org Enhanced、ORCID、Cited Referencesを含まない**（これらはExpanded限定フィールド）。トヨタ所属の直接検証にはStarter APIの応答は使えず、検索クエリでの絞り込み＋DOI照合が必要になる。レート制限（2023年1月時点の図書館提供資料）: Freeプラン=1req/秒・50req/日・年5万件・1req最大50件、Institutional（阪大契約構成員向け）=5req/秒・1000req/日・1req最大50件。[WoS Starter API](https://developer.clarivate.com/apis/wos-starter)

個人でWoS IDを作成し、Clarivate Developer Portalで**本人が**API利用申請する（Application ID/Nameは任意文字列）。承認後にプラン（Free Trial Plan / Free Institutional Member Plan / Free Institutional Integration Plan）を選択する。

詳細な Full Record、住所・所属、助成、引用・被引用文献を扱う WoS Expanded API は有償ライセンスを要し、大阪大学の契約には含まれないことが確認された。[WoS Expanded API](https://developer.clarivate.com/apis/wos)

## 4. 安全な再検査方法

APIキーを入手できた場合だけ、キーをチャット、ノートブック、CSV/JSON、リポジトリ内の設定ファイルに書かず、Jupyter を起動する本人の端末で一時的な環境変数に設定する。

```sh
export SEMANTIC_SCHOLAR_API_KEY='発行済みのキー'
export SCOPUS_API_KEY='発行済みのキー'
export WOS_API_KEY='発行済みのキー'
jupyter nbconvert --to notebook --execute --inplace \
  notebooks/access_checks/scholarly_database_access_check.ipynb
```

このノートブックはキーをURL、出力CSV/JSON、ノートブック出力に保存しない。各基盤に 1 DOI を照会し、HTTP状態と比較用の最小メタデータだけを保存する。`200` は当該キー・環境での到達性、`401` / `403` はキー・契約・IP等の追加確認、`429` はレート制限の確認材料である。

## 5. 図書館への確認依頼文

次の照会で、Web UI ではなく研究用APIの可否を確認できる。

> 件名: Scopus / Web of Science の研究用API利用可否について  
>  
> Science of Science 研究で、トヨタ自動車の研究活動に関する書誌・引用ネットワークを分析します。大阪大学の契約に基づき、Scopus API および Web of Science Starter API / Expanded API を研究目的で利用できるか確認したいです。  
> 1. 現在の大阪大学契約で、各APIの利用可否・申請窓口・利用上限はどこで確認できますか。  
> 2. WoS Starter API の Institutional Member Plan を構成員として利用でき、被引用数を含むデータを取得できますか。  
> 3. WoS Expanded API の利用権は含まれますか。含まれない場合、学内で利用可能な代替手段はありますか。  
> 4. Scopus API の API キー申請時に必要なネットワーク条件・利用許諾上の注意点はありますか。  
> 5. 研究用の小規模なメタデータ収集・派生集計結果の保存・共有について、契約上の留意点はありますか。  
>  
> Web UIのスクレイピングや全文の大量取得は行わず、API規約と図書館の利用条件に従います。

## 6. 研究用データ設計

| 目的 | 主データ | 補助・検証データ | 保存する識別子 |
|---|---|---|---|
| トヨタ関連研究者・論文の広い候補抽出 | OpenAlex | Crossref | DOI、OpenAlex Work/Author ID、ORCID、ROR |
| 引用・共著ネットワークの主分析 | OpenAlex の固定キャッシュまたはスナップショット | Scopus/WoSの限定標本 | 取得日、ソース名、検索式、対象索引 |
| 書誌の欠損補完 | Crossref | 出版社ページ | DOI、ISSN、出版年、文献種別 |
| 意味的な近接研究の探索 | Semantic Scholar | OpenAlex Topics | APIバージョン、取得日、対象フィールド |
| 評価指標の頑健性確認 | OpenAlex | Scopus / WoS | 各基盤の被引用数を別列で保存 |

Scopus や WoS を使える状態になっても、各基盤の被引用数を単一の「正解値」として結合しない。同一 DOI・文献種別・取得日を固定して並列に保存し、基盤差を感度分析として報告する。
