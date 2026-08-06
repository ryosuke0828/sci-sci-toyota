# 作業ログ

このファイルはトヨタ研究者データベース構築プロジェクト全体（今井泰介先生の元タスク文書に基づく。詳細は下記「プロジェクト全体像の更新」参照）の進捗を細かく記録するためのものである。旧来は`toyota_data/toyota_authors.csv`（OpenAlex由来、どうりょう=Sota Hayashi氏経由で受領）の精度向上のみを指していたが、2026-07-27にボスの元タスク文書を確認し、公式サイトスクレイピングによる研究者DB構築・novelty等の指標計算まで含む、より広いプロジェクトであることが判明した。新しい日付のエントリを上に追加する（新しい順）。各エントリには「やったこと」「わかったこと」「次にやること」「伊倉涼介への確認・依頼事項」を書く。

## 進行中のタスク（サマリ）

- [x] Scopus APIキーの個人申請（伊倉涼介） — 完了。動作確認済み（下記参照）
- [x] WoS Starter APIキーの個人申請（伊倉涼介） — **完了（2026-08-03、Clarivateから発行メール受領・動作確認済み）**
- [x] パイロット検証（~100名）の設計・実施 — **完了（2026-08-03実施、2026-08-06に再実行）**。レポート: `docs/reports/pilot_scopus_wos_verification.md`
- [x] トヨタ研究者テーブルの精度向上：全体計画の策定 — 完了（下記参照）
- [x] 【新】ボスの元タスク文書確認・プロジェクト全体像の更新（2026-07-27） — 完了（下記参照）
- [x] 【新】トヨタ自動車未来創成センターの論文一覧スクレイピング（Phase 1） — 完了。154件取得済み（下記参照）
- [x] 【新】豊田中央研究所の論文一覧スクレイピング（Phase 2） — 完了。355件取得済み（下記参照）
- [x] 【新】AISIN IMRA（日本語版aisin.com・米国版imra.com）の論文一覧スクレイピング（Phase 3の一部） — 完了。97件＋313件取得済み（下記参照）
- [x] 【新】AISIN IMRA欧州版（imra.eu）— **スクレイピング不要になった**。WoSの`OG="IMRA Europe"`で25件を回収済み（2026-08-03）
- [x] 【新】4ソースの統合（論文単位、`combined_papers.csv`） — 完了。合計919件（下記参照）
- [x] 【新】論文メタデータのCrossrefによる補完 — 完了。638/641件、著者レコード3,206件（2026-08-03）
- [ ] 【新】スクレイピング結果とOpenAlex IDの紐付け — **813/919件(88.5%)まで完了**。自動取得が毎日進めている（残りは目視確認5件と未マッチ106件）
- [x] 【新】論文単位→研究者単位への集約（名寄せ） — 完了。1,249名（2026-08-03）
- [ ] 【新】リポジトリを整理してGitHubにアップ — **未着手**（2026-08-06のDrive巻き戻り事故の恒久対策）

---

## 2026-08-06

### やったこと

**(1) 自動取得の結果を確認 — 3日間とも正常に動作**

2026-08-03に設定したlaunchdによる毎日9:30の自動取得が、8/4・8/5・8/6と動いていた。OpenAlex紐付けは**813/919件(88.5%)**まで進行。

| ソース | 紐付け率 |
|---|---|
| 豊田中央研究所 | 99.2%（352/355） |
| トヨタ自動車未来創成センター | 85.1%（131/154） |
| AISIN IMRA 米国 | 80.8%（253/313） |
| AISIN IMRA 日本 | 79.4%（77/97） |

DOI完全一致637件・タイトルファジーマッチ176件。目視確認が必要(`review`)なのは**5件のみ**。重複OpenAlex ID 7件。

**(2) Google Drive のフォルダ巻き戻り事故と復旧**

リポジトリが**2026-07-27の状態に巻き戻り、8/3に作成した成果物を失った**。Drive.app がv128→v129に更新・再起動した形跡があり、アップロード前のローカル変更が失われたと考えられる。書き込み自体は現在も正常。

- **無事だったもの（Drive外）**: `~/scisci-auto/`一式（フェーズ3の成果物・OpenAlexキャッシュ9.9MB・`openalex_link_toyota_papers.py`）、AIエージェントのメモリ、LaunchAgent。**自動取得をDrive外に置く設計にしていたことが結果的に成果物を守った**（本来はTCC制限の回避が目的だった）。
- **失ったもの（Drive上のみ）**: `STATUS.md`、`docs/reports/pilot_scopus_wos_verification.md`、スクリプト5本、`data/derived/`の4ディレクトリ、Crossrefキャッシュ、`AGENTS.md`と`log.md`の編集、`/status`スキル。
- **復旧**: `~/scisci-auto`から復元できるものは復元し、スクリプト5本は書き直して**全て再実行した**。

**(3) 再発防止**

- `scripts/backup_repo.sh`を作成。Drive外(`~/scisci-backup/`)へrsyncでミラーし、`snapshot`引数で日付つき世代（直近10世代）も残す。巨大キャッシュ（150MB級）は除外。
- **恒久対策としてGitHubリモートへのpushを予定**（伊倉涼介の提案）。Drive内で`git init`するだけでは、Driveごと巻き戻れば`.git`も消えるため対策にならない。リモートを持つことが要件。

**(4) 再実行の結果 — 再現性を確認**

| 処理 | 8/3の結果 | 8/6の再実行 |
|---|---|---|
| Crossref補完 | 638/641件・著者3,206件・ORCID 779件 | **完全一致** |
| 研究者集約 | 1,249名（high 383/medium 712/low 154） | **完全一致** |
| 名寄せ誤り率 | 過剰併合4.3%・過剰分割1.0% | **完全一致** |
| WoS組織回収 | 832件 | 833件（+1は3日間の新規収録） |

### わかったこと

- **キャッシュを持つ設計が事故の被害を大幅に減らした**。OpenAlexキャッシュ9.9MBが無事だったため、813件の紐付けを再取得せずに復元できた（無料枠1日1,000リクエストしかないため、再取得なら数日かかっていた）。
- **成果物をクラウド同期フォルダだけに置くのは危険**。Google Driveはファイル単位の同期に見えて、クライアント更新時にフォルダ単位で状態が巻き戻りうる。バージョン管理か、同期外のミラーが必要。
- 再実行で数字が完全一致したことから、**分析パイプラインの再現性は確保できている**。

### 次にやること

1. リポジトリを整理してGitHubにアップする（恒久的なバックアップ）
2. OpenAlex紐付けの残り（未マッチ106件・要目視5件）を詰める
3. Scopusで著者の所属情報を補完し、所属網羅率34.5%の問題を解消する

### 伊倉涼介への確認・依頼事項

- drive.google.com のゴミ箱・版履歴に8/3のファイルが残っていないか確認してほしい（サーバー側に届いていなければ何も残っていないはずだが、確認する価値はある）。
- GitHubリポジトリは public / private のどちらにするか。トヨタの研究者データを含むため private を推奨する。

---

## ここまでの状態と次回の再開方法（最優先で読むこと・2026-07-27時点で最新化）

このプロジェクトには現在**独立した2つの作業トラック**が並走している。次回セッションでは、まずこの節を読み、**トラックB（次の一手が明確）から着手する**のが基本方針。トラックAは伊倉涼介の外部承認待ちで、こちらからは動かせない。

### トラックA: toyota_authors.csv 精度検証（Scopus/WoSパイロット）— ブロック中

**状態**: WoS Starter APIキーが**Clarivateの承認待ち**（Scopus側は完了・動作確認済み）。伊倉涼介が「WoSのapplicationが来たら教える」と明言しているため、こちらからは基本待つのみ。

再開手順:
1. 伊倉涼介に「WoSの承認が来たか」を確認する。
   - 確認方法: `developer.clarivate.com/applications` にログイン→一覧の`Ikura Research`をクリック→詳細画面。API側のサブスクリプション状態は `developer.clarivate.com/apis/wos-starter` の「Applications」表で確認できる。
2. 承認が来ていたら: プランは既に**「Free Institutional Member Plan」**でサブスクリプション申請済み（選び直し不要）。発行されたAPIキーを`~/.zshrc`に`export WOS_API_KEY='取得した値'`として追記してもらい、**さらに**`grep 'WOS_API_KEY' ~/.zshrc >> ~/.zshenv`を実行してもらう（zshの非対話シェルは`.zshenv`しか読まないため。Scopusのときと同じ理由）。
3. `echo "WOS_API_KEY: 設定済み(長さ ${#WOS_API_KEY} 文字)"`等で値を表示せずに存在確認する。
4. 1 DOIだけを使ったWoS Starter APIのスモークテストを行う（Scopusで行った方法に倣う）。
5. 動作確認できたら「フェーズ2: パイロット検証（~100名）」の設計・実装に進む（詳細は下記「全体計画」、および2026-07-27の「Scopus単独パイロット探索」で得た知見＝AUTHLASTNAME/AUTHFIRST構文・AFFIL vs AF-ID・上位1候補だけでは不十分、等を反映すること）。

### トラックB: 公式サイトスクレイピングによる研究者DB構築 — **ブロックなし、次にやるべきはこちら**

**背景**: 2026-07-27に今井泰介先生の元タスク文書を確認し、本プロジェクトの本来のゴールは`toyota_authors.csv`の精度向上だけでなく、トヨタ関連公式サイトのスクレイピング→OpenAlex ID紐付け→novelty/disruptiveness等の指標計算であることが判明した（詳細は下記「プロジェクト全体像の更新」参照）。

**ここまで完了したこと**:
- Phase 1〜3（4ソースのうち3ソース）のスクレイピングが完了し、`data/derived/toyota_official_scrape/combined_papers.csv`に919件（DOIあり643件）を統合済み。内訳: 豊田中央研究所355・AISIN IMRA米国(imra.com)313・トヨタ自動車未来創成センター154・AISIN IMRA日本(aisin.com)97。
- 使ったノートブックは`notebooks/exploration/`配下の`toyota_frontier_research_center_scrape.ipynb`・`toyota_central_rd_labs_scrape.ipynb`・`aisin_imra_jp_scrape.ipynb`・`imra_com_scrape.ipynb`・`toyota_official_scrape_consolidate.ipynb`（すべて実行済み・出力保存済み、再実行すれば同じ結果が再現できるはず）。
- 詳細は下記「Phase 2〜3・統合 実施内容」を参照。

**次回セッションで最初にやるべき具体的な一手（優先順）**:
1. **Phase 4: OpenAlex IDへの紐付け** — `combined_papers.csv`の919件（DOIあり643件・DOIなし276件）についてOpenAlex Works APIと照合する。DOIありは`https://api.openalex.org/works/doi:{DOI}`で完全一致検索できる見込み（実装未着手）。DOIなしはタイトルのファジーマッチング＋目視確認が必要（ボスの指示通り）。この過程で著者名の表記ゆれ（ピリオド有無・日本語/ローマ字）の正規化も設計する。
2. **imra.eu（AISIN IMRA欧州版）のスクレイピング** — ニュース記事形式・SSL証明書エラーありで他3件より手間がかかるため後回しにしていた。Phase 4がある程度進んでから、または並行して着手する。
3. 伊倉涼介にSota Hayashi氏の担当範囲（役割分担）を確認する（未確認のまま）。

**このトラックの成果は将来的にトラックAとも合流する**: 「トヨタ公式サイトから得た正解データ」と「Scopus/WoSでの照合結果」を突き合わせることで、Scopus/WoS照合の精度を定量評価できるようになる（伊倉涼介と議論した「複数DBの一致でノイズ判定する」というアイデアの土台になる）。

## 全体計画（2026-07-23 策定、伊倉涼介承認: パイロット規模で開始）

Scopus・WoSともAPIキーは伊倉涼介の個人申請が必要なため（機関契約はあるがキー発行は個人アカウント経由）、まずAPIキーを取得し、100名規模のパイロット検証でScopus/WoSを使った照合手法が実際に機能するかを確かめてから、本格展開の規模・期間を再検討する。9,429名全体や現所属3,763名全体への拡大は、パイロット結果を見て判断する（いきなり全体には広げない）。

| フェーズ | 内容 | 状態 |
|---|---|---|
| 0. 環境整備 | 図書館回答の反映、既知データ品質問題の把握 | 完了 |
| 1. APIキー個人申請 | Scopus・WoS Starterとも伊倉涼介が個人で申請。キーは環境変数のみで共有、チャット・リポジトリに書かない | **Scopus完了・動作確認済み。WoSはClarivate承認待ち** |
| 2. パイロット検証（~100名） | 既知ノイズ約400名からサブサンプル30〜40名＋現所属3,763名からランダム60〜70名を対象に、Scopus/WoSの複数エンドポイントを試しながら所属照合・被引用数感度分析を行う | APIキー取得後に着手 |
| 3. パイロットのレビュー・本格展開判断 | パイロット結果（何が機能し、何が機能しなかったか、実際のクォータ消費量）を伊倉涼介と共有し、本格展開の範囲・期間を再設計する | 未着手 |

パイロットで確認したいこと（「なるべくいろいろなことを試す」の対象）:
- Scopus: Author Search／Author Retrieval／Affiliation Search／Abstract Retrieval／Scopus Search（affil()・af-id()クエリ）を試し、OpenAlexの`matched_entities`・`other_affiliations`との一致度を評価する。
- WoS Starter: 応答に所属フィールドがないため、検索クエリ側の組織名フィルタ（OG=等のフィールドタグ）が機能するかを確認する。機能すれば「DOI一致＋組織検索ヒット」で間接的な所属証拠にできる。Times Cited (Core Collection) をOpenAlexの`cited_by_count`と並べて感度分析用に保存する（上書き・合算はしない）。
- 実際のクォータ消費・レスポンス時間・エラー（429/403等）を記録し、本格展開時の見積もりに使う。

## プロジェクト全体像の更新（2026-07-27・今井先生の元タスク文書を確認）

伊倉涼介が今井泰介先生から示された元タスク文書（Notion等のページと思われる）の内容を共有。これにより、本プロジェクトが単なる`toyota_authors.csv`の精度向上ではなく、もっと広い「Science of Science」研究であることが判明した。

**本来のゴール**: トヨタ自動車の研究者・技術者の共同研究・知識生成をSciSciの手法で分析する。具体的な問い＝イノベーションがどこでどんな条件で生まれるか／どの研究者が特に成功・影響力を持つか／どんなチーム構造が良い研究成果につながるか。

**共同作業者**: 伊倉涼介ともう一人、Sota Hayashi氏が同じタスクにアサインされている。`toyota_data/toyota_authors.csv`は「どうりょう」から受け取ったものだが、おそらくSota Hayashi氏経由。

**ボスのタスク文書の該当部分「Build a Researcher Database」**:
1. トヨタ自動車未来創成センター(https://www.toyota.co.jp/jpn/tech/partner_robot/search/) の論文一覧をスクレイピング（タイトル・著者・トヨタ所属著者=太字表記・掲載誌・リンク・カテゴリ）
2. 豊田中央研究所(https://www.tytlabs.co.jp/papers/) も同様にスクレイピング
3. AISIN IMRA(https://www.imra.com/, https://www.imra.eu/, https://www.aisin.com/jp/group/imra-japan/paper/page1/) も同様にスクレイピング
4. スクレイピングしたタイトルからOpenAlex IDを同定（文字列一致だけでは誤同定があるため目視確認が必要、とボスの文書に明記）
5. OpenAlexから論文メタデータ・参考文献を取得し、interdisciplinarity・disruptiveness等の指標を計算する

その後、novelty・hot streak関連文献の読解、以下2本の論文の輪読も予定されている:
- https://doi.org/10.1038/s41597-023-02198-9
- https://www.nature.com/articles/s43588-025-00906-6

**重要な食い違いの発見**: 現行の`toyota_data/toyota_authors.csv`（OpenAlex由来）は`toyota_authors_README.md`に「豊田自動織機・豊田中央研究所・Toyota Research Instituteは含まない」と明記されている（OpenAlex上でToyota Motor Corporation系列に属さないため除外）。しかしボスのタスク文書では**豊田中央研究所・AISIN IMRAは明示的に別個の調査対象**として指定されている。つまり現行csvはボスの本来のスコープより狭い。スクレイピングによる研究者DBは、この既存csvとは別に、独立して構築する（後で突き合わせて精度検証にも使える）。

**役割分担**: 伊倉涼介がスクレイピング担当としてこのタスクを進める（Sota Hayashi氏の担当範囲は現時点で不明・要確認）。

**Scopus/WoSパイロット作業との関係**: これまでのScopus/WoS照合パイロットは無駄にはならず、「トヨタ公式サイトのスクレイピングで得た正解データ（ボス指定の正式な所属者リスト）」と「Scopus/WoSでの照合結果」を突き合わせることで、Scopus/WoS照合の精度を定量評価できるようになる（伊倉涼介との議論で出た「3DBの一致を見る」というアイデアの、より確実な土台になる）。

### サイト下調べ結果（2026-07-27実施）

| 対象 | 状態 | 詳細 |
|---|---|---|
| 1. トヨタ自動車未来創成センター | **スクレイピング完了(Phase 1)** | 検索ページ自体はJS描画だが、裏で叩いているJSON API `https://www.toyota.co.jp/jpn/tech/partner_robot/search/json/articles.json` を直接取得すれば1回のGETで全154件（2018〜2026年）が取れる。フィールド: `category`(1〜5の整数)・`authors`(`*Name*`でトヨタ所属著者を明示)・`title`・`source`・`published_at`・`year`・`link`。robots.txt確認済み、対象パスはDisallowに含まれない |
| 2. 豊田中央研究所 | 下調べ完了・未着手 | `https://www.tytlabs.co.jp/papers/` → `https://www.tytlabs.co.jp/ja/technology/papers.html` にリダイレクト。静的HTML、`<div class="item">`が355件（2018〜2026年）全件同一ページに含まれる（ページネーションなし、年タブはJSでのフィルタ表示切替のみ）。フィールド: 日付・カテゴリアイコン・タイトル(`news_tx`)・著者(`text1`、太字マーキングなし)・掲載誌(`text2`)・巻号ページ(`text3`)・リンク(href)。robots.txt確認済み、問題なし |
| 3. AISIN IMRA | 下調べ完了・未着手 | **3つの窓口があり、それぞれ別法人・別データ**。(a) `aisin.com/jp/group/imra-japan/paper/page1/`(日本語、AISIN公式サイト内。ページネーションあり、6ページ×18件≒108件、静的HTML `class="item d_flex"`) (b) `imra.com/imra-research-papers/`(英語、IMRA America公式。素のcurlだと406を返すがブラウザ相当のヘッダー(Accept/Accept-Language/Referer)を付けると200。構造は要追加調査、WordPressサイトで`class="item"`は0件＝別のクラス名を使っている) (c) `imra.eu`(IMRA Europe公式。ニュース記事形式の個別投稿で一覧ページ化されていない可能性が高く、3つの中で最も手間がかかる。**SSL証明書エラーあり**（`unable to get local issuer certificate`）、`curl -k`で回避できることのみ確認、原因未調査) |

### 提案する進め方（フェーズ）

| フェーズ | 内容 | 状態 |
|---|---|---|
| 1. 未来創成センター スクレイピング | JSON APIから154件取得・構造化・保存 | **完了**（下記参照） |
| 2. 豊田中央研究所 スクレイピング | 静的HTML 355件をパースして保存 | 未着手（下調べ済み、実装は容易な見込み） |
| 3. AISIN IMRA スクレイピング | 3窓口(aisin.com/imra.com/imra.eu)をそれぞれ調査・実装 | 未着手（imra.comの構造再調査・imra.euのSSL対応が必要） |
| 4. OpenAlex IDへの紐付け | タイトルのファジーマッチング＋目視確認（ボスの指示通り） | 未着手 |
| 5. 指標計算 | interdisciplinarity・disruptiveness・novelty・hot streak等 | 未着手（先行研究の読解も必要） |

### Phase 1 実施内容（トヨタ自動車未来創成センター）

- ノートブック: `notebooks/exploration/toyota_frontier_research_center_scrape.ipynb`（実行済み・出力保存済み）
- 保存データ: `data/derived/toyota_official_scrape/frontier_research_center.csv`（構造化済み）、`frontier_research_center_raw.json`（取得日時・取得元URL付きの生データ、再現性のため）
- 結果: 154件取得、HTTP 200。太字（トヨタ所属）著者が0人の論文は0件（全論文に最低1人はトヨタ所属著者がいる）。リンクが`#`（未設定）の論文が4件。
- 年別: 2018年26件 〜 2026年5件（2026年はまだ年途中のため少ない）。カテゴリ別: ロボティクス57・数理AI46・バイオヒューマン24・エネルギ23・革新的構造4。
- 頻出トヨタ所属著者トップ: Kaji, H.(19件)、Masuda, T.(14件)、Takeshita, K.(12件)、Yamamoto, T.(11件)等。
- **既知の軽微な課題**: 著者名の表記ゆれ（例: 「Doi, M.」と「Doi, M」のように、ピリオドの有無が論文によって異なる）。今後OpenAlex IDと紐付ける際は、この表記ゆれを吸収する正規化が必要。また日本語氏名表記（例:「増田 泰造」）とローマ字表記（「Masuda, T.」）が別人物として集計されてしまっている可能性があり、名寄せが必要。

### 次にやること

- ~~Phase 2（豊田中央研究所）のスクレイピングノートブックを実装・実行する。~~ → **完了**（下記追記参照）
- ~~Phase 3（AISIN IMRA）は3窓口それぞれの構造を追加調査してから着手する~~ → **aisin.com・imra.comの2窓口は完了**。imra.euは未着手（下記参照）
- Phase 1データの著者名表記ゆれ（ピリオド有無・日本語/ローマ字）の正規化方針を検討する。→ 未着手（Phase 4のOpenAlex紐付け時にまとめて対応予定）
- Sota Hayashi氏の担当範囲（OpenAlex側の作業か、別のスクレイピング対象か等）を伊倉涼介に確認する。→ 未確認
- **新規**: imra.euのスクレイピング設計（ニュース記事形式の個別ページからのタイトル・著者・DOI抽出、SSL証明書エラーへの対処）
- **新規**: Phase 4（4ソース919件のタイトル/DOIをOpenAlex IDに紐付け）に着手する

### 伊倉涼介への確認・依頼事項

- Sota Hayashi氏がこのタスクのどの部分を担当しているか（役割分担の全体像）を教えてほしい。
- Phase 1で見つかった「著者名の表記ゆれ」「日本語/ローマ字の同一人物問題」について、どこまで自動処理し、どこから目視確認にするかの方針の希望があれば聞きたい。

### Phase 2〜3・統合 実施内容（追記、2026-07-27）

伊倉涼介の指示「そのまま行けるところまで進めてほしい」を受けて、Phase 2・Phase 3（一部）・統合まで連続して実施した。

**Phase 2: 豊田中央研究所**
- ノートブック: `notebooks/exploration/toyota_central_rd_labs_scrape.ipynb`
- `https://www.tytlabs.co.jp/papers/` → `https://www.tytlabs.co.jp/ja/technology/papers.html` にリダイレクト。静的HTML1ページに355件全件が埋め込まれており、ページネーション不要。
- 保存: `data/derived/toyota_official_scrape/toyota_central_rd_labs.csv`（構造化）、`toyota_central_rd_labs_raw.html`（生データ）、`toyota_central_rd_labs_meta.json`
- 結果: 355件（2018年18件〜2026年28件）。**336件(94.6%)がdoi.orgへの直リンク**（未来創成センターと違いDOIが直接取れるため、Phase 4のOpenAlex紐付けはタイトルの曖昧マッチングではなくDOI完全一致で行える見込み＝精度が高い）。カテゴリは複数ラベル制（コア技術・材料・数理・電気電子等）。リンクなし8件。トヨタ所属著者の太字表記なし（この一覧の著者は全員同研究所所属という前提と思われる）。

**Phase 3: AISIN IMRA（日本語版・aisin.com）**
- ノートブック: `notebooks/exploration/aisin_imra_jp_scrape.ipynb`
- `https://www.aisin.com/jp/group/imra-japan/paper/page1/`〜`page6/`（6ページ、1ページ17件前後）
- **文字化けの罠と修正**: `requests`がHTTPヘッダーにcharset指定がないためISO-8859-1と誤判定し、日本語が文字化けした（`resp.encoding = 'utf-8'`を明示して解決。HTMLの`<meta charset>`はutf-8なのに、HTTPヘッダーの`Content-Type: text/html`にcharset指定がないサイトでは同じ問題が起こりうる。他サイトのスクレイピングでも要注意）。
- 保存: `data/derived/toyota_official_scrape/aisin_imra_jp.csv`、`aisin_imra_jp_raw_pages/`（6ページ分生HTML）、`aisin_imra_jp_meta.json`
- 結果: 97件。カテゴリは超電導37・ライフサイエンス21・太陽電池18・センシング16・燃料電池5。doi.org以外/リンクなしが23件。

**Phase 3: AISIN IMRA（米国版・imra.com）**
- ノートブック: `notebooks/exploration/imra_com_scrape.ipynb`
- `https://www.imra.com/imra-research-papers/`（素の`curl`は406、ブラウザ相当ヘッダー(Accept/Accept-Language/Referer)で200）
- WordPress(Visual Composer)構成。1論文=1行(`div.wpb_row.vc_row`)、左列=タイトル、右列=掲載誌+DOIリンク。**著者名の記載が一切ない**（Phase 4でDOI経由でOpenAlex/Crossrefから別途取得する必要がある）。
- 保存: `data/derived/toyota_official_scrape/imra_com.csv`、`imra_com_raw.html`、`imra_com_meta.json`
- 結果: 313件。リンクなし1件、doi.org以外90件。

**AISIN IMRA（欧州版・imra.eu）— 未実施**
- `https://www.imra.eu/news/`配下の個別ニュース記事として掲載されており、一覧ページ化されていない（他3件のような構造化された論文リストではない）。記事ごとにタイトル・著者・DOIが自由記述で埋め込まれていると推測されるが未検証。
- **SSL証明書エラーあり**（`unable to get local issuer certificate`）。`curl -k`（証明書検証スキップ）で回避できることのみ確認、原因未調査。
- 他3件より大幅に手間がかかる（記事一覧のページネーション調査＋個別記事のスクレイピング＋自由記述からの構造化）ため、今回は見送り、別セッションで設計してから着手する。

**4ソース統合**
- ノートブック: `notebooks/exploration/toyota_official_scrape_consolidate.ipynb`
- 保存: `data/derived/toyota_official_scrape/combined_papers.csv`
- 結果: 合計**919件**（豊田中央研究所355・AISIN IMRA米国313・未来創成センター154・AISIN IMRA日本97）。DOIあり643件(70%)。
- **重複2件を発見**: (1) 未来創成センターと豊田中央研究所の両方に同じ論文(`10.1109/icra46639.2022.9811768`)が掲載されている（両組織の共著者がいる論文のため両方のサイトに載っている、正常な重複）。(2) imra.com内で同一論文が2回掲載されている（同サイト内の重複、原因未調査）。Phase 4でDOI単位の重複排除が必要。
- AISIN IMRA日本語版(aisin.com)と米国版(imra.com)の間には**タイトル・DOIとも重複が見つからなかった**（完全に別々の論文群＝両方スクレイピングした意味があった）。

### 得られた設計上の知見（今後のPhase 4・Phase 5に向けて）

1. **DOIベースの紐付けが可能な範囲が大きい**: 4ソース919件中643件(70%)がDOIを直接持つ。DOIがあればOpenAlex/CrossrefのAPIで完全一致検索でき、ボスの指示にある「タイトルのファジーマッチング＋目視確認」が必要なのは主に未来創成センター（リンクが`#`や外部サイトの4件、DOIパターンに合致しないリンクを含む）とAISIN IMRA日本語版の一部にとどまる見込み。
2. **著者情報の有無がソースによって異なる**: 未来創成センター(著者あり、トヨタ所属者は太字)・豊田中央研究所(著者あり、所属区別なし)・AISIN IMRA日本語版(著者あり、所属区別なし)・AISIN IMRA米国版(著者情報なし)。imra.comの著者はDOI経由でOpenAlex/Crossrefから補う必要がある。
3. **著者名の表記ゆれが複数レベルである**: (a) 同一人物でもピリオド有無等の表記ゆれ(`Doi, M.`と`Doi, M`)、(b) 日本語氏名とローマ字表記が別人物として集計されるリスク、(c) 複数組織にまたがる共著者の名寄せ。Phase 4のOpenAlex ID紐付け＋Phase 5前の研究者単位集約で、まとめて名寄せ処理を設計する必要がある。
4. **クロス組織の共著が実際に存在する**（未来創成センター×豊田中央研究所の重複例）。これは今井先生の関心事項（チーム構造・共同研究）そのものであり、単なるノイズではなく分析対象として活かせる。

---

## 2026-07-27

### やったこと

- 伊倉涼介がClarivate Developer Portalで申請状況を確認。スクリーンショットで以下を確認した。
  - `developer.clarivate.com/applications` の一覧に `ikura-research`（Ikura Research, owner）が登録済み。
  - `developer.clarivate.com/applications/ikura-research` の詳細画面: Application Name/Description/Client Type（Confidential）は申請時のまま。Subscriptionsセクションには「このアプリケーションにはAPIサブスクリプションがない」旨の表示があった（＝アプリケーション登録とAPI申込みは別ステップ）。
  - `developer.clarivate.com/apis/wos-starter`（Web of Science Starter APIのページ）下部の「Applications」表に `Ikura Research | Free Institutional Member Plan | API Key: Subscription approval is pending | Unsubscribe »` と表示されているのを確認。

### わかったこと

- WoS Starter APIキーの取得は「①アプリケーション登録」と「②そのアプリケーションでのAPIサブスクリプション申込み（プラン選択含む）」の2段階になっている。①②とも完了済みで、プランも正しく**Free Institutional Member Plan**が選択されている。現在は②のサブスクリプション承認待ち（"Subscription approval is pending"）という状態であることが画面上の文言で確定した。
- 承認されると同じ「Applications」表のAPI Key欄に実際のキーが表示される見込み（現在は"Subscription approval is pending"というプレースホルダー文言）。

### 次にやること

- 伊倉涼介: 引き続き承認を待つ（受動的）。`developer.clarivate.com/apis/wos-starter` を再訪して、Applications表のAPI Key欄が実際のキーに変わっていないか時々確認してもよい。
- 承認されたら、そのAPIキーを`~/.zshrc`に`export WOS_API_KEY='...'`として追記し、`grep 'WOS_API_KEY' ~/.zshrc >> ~/.zshenv`を実行後、AIエージェントに報告する（上記「ここまでの状態と次回の再開方法」参照）。

### Scopus単独パイロット探索（追記）

WoS承認待ちの間にできる作業として、Scopusのみを使った小規模探索（既知ノイズ4名＋現所属ランダム4名、計8名、乱数シード`20260727`）を実施した。
ノートブック: `notebooks/exploration/scopus_toyota_pilot_exploration.ipynb`（実行済み・出力保存済み）。
保存データ: `data/derived/scopus_pilot_exploration/`（`sample_selection.csv`, `affiliation_search_candidates.csv`, `api_call_log.csv`, `verdict_comparison.csv`, `run_summary.json`）。

**クエリ構文に関する訂正（重要・恒久的な知見）**

- Scopus **Author Search**（`content/search/author`）は`AUTHOR-NAME()`という複合フィールドを受け付けず`INVALID_INPUT`エラーになる。正しくは`AUTHLASTNAME()`と`AUTHFIRST()`を`AND`で分けて指定する（[Scopus Author Search Guide](https://nonprod-devportal.elsevier.com/sc_author_search_tips.html)で確認）。
- Scopus **Search API**（`content/search/scopus`）は`AUTHOR-NAME()`を受け付ける（Author Searchとは別物で、姓名の順序にも寛容）。
- Author Searchの`AFFIL()`は著者の**現在所属だけでなく過去の全論文の所属表記**にもマッチする。現在所属を知りたい場合は応答中の`affiliation-current`を別途確認する必要がある。
- `AF-ID()`による厳密な絞り込みは`AFFIL()`の自由文字列一致よりかなり狭く、この試行では**8名中どの`AF-ID()`厳密クエリも0件**だった一方、`AFFIL(Toyota)`の自由文字列では複数名で数件〜10件ヒットした（Yamamoto: 0 vs 10、Nobuhiro: 0 vs 4、Doi: 0 vs 4）。Toyota関連のaf-idはAffiliation Searchだけで25件見つかっており、地域・部門ごとに細分化されているため、上位3件だけのAF-ID絞り込みでは取りこぼしが大きい。パイロット本番では`AFFIL()`の自由文字列一致を主に使う方が良さそうである。
- OpenAlexの`name`列は姓名の順序が不定（日本語ローマ字表記の順序ゆれ）。末尾トークンを姓とみなす素朴な分割＋0件時に姓名入れ替えて再試行、という方式で対応した。

**個別の結果（8名）**

| sample_group | 名前 | OpenAlexの主張 | Scopus Author Searchの結果 |
|---|---|---|---|
| known_noise | Tetsuo Yazawa (first_pub_year=1936) | Toyota Motor Corp (Japan)所属 | 候補1件、現在所属=University of Hyogo（Toyotaではない）。OpenAlex側のノイズ疑いを支持する結果 |
| known_noise | Masatoshi Ishikawa (ORCID有, first_pub_year=1942) | Toyota Motor Corp (Japan)所属 | 姓名どちらの順でもAFFIL(Toyota)付きでは0件。判定不能（Scopus非掲載か、名寄せの取りこぼしかは不明） |
| known_noise | Shin Yamamoto (first_pub_year=1935) | Toyota Motor Corp (Switzerland)所属 | 候補4件（同名異人が多数）。うち2件は現在所属Toyota系だが文献数2〜3件と少なく、462件のOpenAlexプロファイルとは別人の可能性が高い。「Yamamoto」は多数の同名者がいる典型的な曖昧姓の例 |
| known_noise | Minoru KAWAMOTO (first_pub_year=1936) | Toyota Motor Corp (Switzerland)所属 | 姓名どちらの順でも0件。判定不能 |
| currently_affiliated | Tomohiro MIYABE | Toyota Motor Corp (Switzerland)所属（現所属） | 候補1件、現在所属=**Toyota Central R&D Labs., Inc.**（True）。**`toyota_authors_README.md`§3-1に記載のスイス法人への誤帰属バグの実例と一致**（豊田中央研究所はこのデータセットの対象外エンティティのはず） |
| currently_affiliated | Dorothée Lahaussois | Toyota Motor Corp (Belgium)所属（現所属） | 候補1件、現在所属=Toyota Motor Europe NV/SA（True）。**OpenAlexの主張と整合する明確な一致** |
| currently_affiliated | Masaki Nobuhiro | Toyota系（複数）所属（現所属） | Author Searchの上位候補はIDEC Corporation（False）だが、`AFFIL(Toyota)`広域検索では4件ヒットしており別候補にToyota関連者がいる可能性。上位1件だけを見る設計では取りこぼす例 |
| currently_affiliated | Masahiro Doi | Toyota Motor Corp (Japan)所属（現所属） | 候補1件、現在所属=Toyota Motor Corporation（True）。**明確な一致** |

**わかったこと（パイロット設計への示唆）**

1. Scopusとの突き合わせは機能する見込みが高いが、**Author Searchの「上位1候補」だけを見るのは不十分**。同姓同名（特にYamamoto等の多い姓）では複数候補を確認し、文献数・主題分野・所属履歴で絞り込む必要がある。
2. **既知ノイズの中身は一様ではない**。今回の4名中、Yazawaは「Scopus上に別人としてクリーンなプロファイルがあり、Toyota無関係」という明確なノイズ確認ができたが、Ishikawa・KAWAMOTOは「Scopus側で該当候補が見つからない」だけで、ノイズか単なる名寄せ失敗か区別できなかった。0件＝ノイズ確定ではない点に注意。
3. **既知の誤帰属バグ（スイス法人への豊田中研混入）を現所属者側でも実例確認できた**（Miyabe氏）。本格展開では、スイス法人エンティティ経由の現所属者について、Scopus/WoSでの所属名確認を優先度高く行うべき。
4. `AF-ID()`より`AFFIL()`の自由文字列一致の方が実用的（上記の通りAF-ID厳密一致は取りこぼしが大きい）。
5. クォータ消費は極めて小さい（Author Search 11件・Author Retrieval 6件・Scopus Search 16件・Affiliation Search 1件・Abstract Retrieval 2件、計35件、エラー0件、429なし、1件あたり350〜800ms）。100名規模のパイロットでも週間クォータ（Author Search系5,000/週、Scopus Search 20,000/週）には全く届かない見込み。

### 次にやること（更新）

- 伊倉涼介: 引き続きWoS承認を待つ（受動的）。
- AIエージェント: 上記の知見（AUTHLASTNAME/AUTHFIRST訂正、AFFIL vs AF-ID、上位1候補だけでは不十分等）を踏まえて、WoS承認後の本格パイロット（~100名）設計に反映する。特に「複数Scopus候補の妥当性を機械的にどう順位付けするか」（ORCID一致・所属履歴の年代整合性・共著者ネットワークなど）を検討課題として残す。

### 伊倉涼介への確認・依頼事項

- 特になし。現時点でやることはなく、Clarivateからの承認メール等を待つのみ。

---

## 2026-07-23

### やったこと

- Gmailで阪大図書館からの回答2件を確認した。
  - R26-086（2026-07-17）: WoS API — Starter APIのみ利用可、Expanded APIは契約外。
  - R26-085（2026-07-21）: Scopus API — 研究目的で利用可。
- 両回答の添付資料4点（Elsevier APIs案内、Scopus API Guide、WoS APIフィールド一覧xlsx、WoS/InCitesセミナー資料）をダウンロードし、テキスト抽出して内容を確認した。
- 確認した内容を`AGENTS.md`（恒久的な運用ルール）と`docs/reports/scholarly_database_access_plan.md`・`docs/reports/scholarly_databases_master_report.md`（詳細・出典）に反映した。
- `toyota_data/toyota_authors.csv`（9,429名、OpenAlex由来）と`toyota_authors_README.md`を確認し、既知のデータ品質問題を把握した。

### わかったこと（重要な制約）

- **WoS Starter APIには著者所属(affiliation)・ORCID・Org Enhancedフィールドが含まれない**（Expanded限定）。そのためStarter APIの応答だけではトヨタ所属の直接検証ができない。検索クエリでの絞り込み＋DOI照合という設計にする必要がある。
- **Scopus APIは既定でIPアドレス認証**（阪大契約IPアドレス範囲内からのみ動作）。学外から使う場合はinsttoken申請が別途必要。
- 両APIとも、APIキー自体は伊倉涼介が個人で申請・取得する必要がある（機関契約はあるが、キー発行は個人アカウント経由）。
- 既存の`toyota_authors_README.md`に記載された既知の問題:
  1. スイス法人エンティティ(5,788名)に日本本体・豊田中研の論文が誤帰属している例が多数。
  2. 著者名寄せの混同（`first_pub_year`<1950が324名、`n_affiliations`>100が79名、`n_last_known_institutions`>10が19名）。
  3. 分野分布の歪み（Medicine 1,236名は主にスイス法人への誤帰属由来と推定）。

### APIキー取得作業の経緯（追記）

- AIエージェントがブラウザ自動操作（claude-in-chrome）で`dev.elsevier.com`のScopus APIキー申請を代行しようとしたが、ページが`document_idle`に達せずスクリーンショット・テキスト取得が繰り返しタイムアウト。ネットワークリクエスト自体は200で返っていたため、Cookie同意バナー等のスクリプトが原因と推測されるが未解明のまま断念。
- 方針転換: 伊倉涼介本人が画面操作し、AIエージェントが手順・入力文言を指示する方式に切り替えた。

**Scopus APIキー（完了・動作確認済み）**
- ラベル: `Ikura Research` / URL: `https://tanaka.msp-lab.org/index_j` で申請・取得。
- 環境変数`SCOPUS_API_KEY`を最初`~/.zshrc`にのみ追記したところ、AIエージェントのBashツールから見えなかった。原因はzshの仕様（`.zshrc`は対話シェルのみで読み込まれ、ツール実行の非対話シェルには反映されない）。`grep 'SCOPUS_API_KEY' ~/.zshrc >> ~/.zshenv` で`.zshenv`にもコピーしてもらい解決（**WoSキーでも同じ対応が必要**）。
- スモークテスト実施済み: DOI `10.1126/science.aaf5239`（Sinatra et al. 2016、既存アクセス検査ノートブックと同じ検証用DOI）に対し `X-ELS-APIKey` ヘッダー認証でAbstract Retrieval APIを呼び出し、HTTP 200・`citedby-count: 533`を確認。実行コマンドは下記。

```python
# ~/.venvs/scisci-rir/bin/python3 で実行。os.environ からキーを読み、
# HTTPヘッダー(X-ELS-APIKey)で送る。キー自体は一切printしない。
import os, requests
api_key = os.environ.get("SCOPUS_API_KEY")
url = f"https://api.elsevier.com/content/abstract/doi/10.1126/science.aaf5239"
headers = {"X-ELS-APIKey": api_key, "Accept": "application/json"}
resp = requests.get(url, headers=headers, timeout=15)
print("status:", resp.status_code)  # 200
```

**WoS Starter APIキー（申請送信済み、承認待ち＝現在のブロッカー）**
- Application ID: `ikura-research` / Application Name: `Ikura Research`
- Application Description: `Academic research use by an individual graduate student at Osaka University: retrieving publication and citation metadata via the Web of Science Starter API for personal bibliometric analysis.`
- Client Type: Confidential相当を選択（秘密情報を安全に保持できるクライアントとして）
- 「This application will use OAuth2.0 Flows (other than the Client Credentials flow, i.e. using redirects)」のチェックボックスは**外した**（Client Credentialsフローを使用。ブラウザリダイレクトを伴うユーザーログインは不要な用途のため）。Redirect URIは未入力。
- 申請送信済み。図書館回答にある通り「Applicationが提供元(Clarivate)に承認されるとプラン選択ができる」仕組みのため、承認待ちの状態。承認までの所要時間は資料に記載がなく不明。
- 承認後にプラン選択画面が出たら「Free Institutional Member Plan」を選ぶこと（Free Trial Planは被引用数が取れないため不可、WoS Expanded APIは阪大契約外なので選ばない）。

### 次にやること

- 伊倉涼介: WoS Starter APIの承認を待つ（受動的）。承認が来たら「WoSのapplication来た」等とAIエージェントに伝える。
- AIエージェント: 承認後、プラン選択・キー取得・`.zshenv`反映・スモークテストを案内し、確認できたらフェーズ2（パイロット検証）のノートブック設計に着手する。

### 伊倉涼介への確認・依頼事項（2026-07-23時点）

1. ~~Scopus APIキー申請~~ → **完了**。ラベル`Ikura Research`・URL`https://tanaka.msp-lab.org/index_j`で取得、`.zshenv`経由で動作確認済み（上記参照）。追加対応不要。
2. **WoS Starter APIキー申請** → 申請送信済み、**Clarivate承認待ち**。伊倉涼介がやることは今は無い（受動的に待つ）。承認が来たら教えてもらう。承認後にやってもらう作業は上の「次回の再開方法」に記載済み。
3. ~~作業ネットワーク環境の確認~~ → 解決済み。普段は工学研究科棟のWi-Fi（学内ネットワーク）で作業とのことなので、ScopusのIPアドレス認証（阪大契約IP範囲内が前提）は問題ない。insttoken申請は不要。
