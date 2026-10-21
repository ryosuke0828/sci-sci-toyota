# 研究室内で共有するリポジトリの作成計画

2026-10-07 作成（当初は公開リポジトリの計画。2026-10-08 に、private にして研究室内だけで管理する方針に変えた）。伊倉涼介との相談で決めた方針と、作業の段階をまとめる。決定が変わったら書き換える。

**進捗（2026-10-14）**: 段階1〜3は済み。段階4（再現の確認）は通った（著者数0は直さないと決まり、数値は確定）。段階0の残り（見せる相手が阪大の人だけか、置き場所）と段階5（GitHub に置く）が未完了。書き出し先は `~/scisci-public/`（`git init` 済み、コミット前）。

## 目的

トヨタ関連論文の新規性の解析を、**研究室の人が再現できる形で**、private リポジトリにまとめて研究室内で管理する（2026-10-08 変更。当初は論文・発表の付属資料として一般公開する予定だった）。

## 決定事項

| 項目 | 決定 |
|---|---|
| 公開範囲 | private。研究室内だけで共有する（2026-10-08、伊倉涼介の決定）。理由: Scopus の所属表記は規約で公開できず、外すと所属から作る数値が変わるため |
| 載せる範囲 | (1) トヨタ関連4サイトのスクレイピング結果、(2) OpenAlex を使った書誌情報・所属の補完、(3) それを使った SciSciNet の検証、(4) SciSciNet を使った分析結果。最終結果を出すのに実際に使ったものだけ |
| 載せない範囲 | Scopus・WoS で試行錯誤していた時期のもの（パイロット検証、WoS の組織検索、アクセス確認、`toyota_authors.csv`）、練習と既存研究の再現（OpenAlex 探索、Random Impact Rule、h指数）、文献調査、新規性の最初の分析（v1）、先生への CSV 書き出し |
| 分析結果 | 載せる（今井先生の了承済み） |
| 研究者単位の表 | 載せる（`researchers.csv`）。新規性の分析では使っていないが、研究者データベースとして本筋に含める（2026-10-14、伊倉涼介）。そのため、表を作るのに使った Crossref（工程6）と Scopus（工程7）のコードと出力も載せ、Scopus を含むのでリポジトリは private のまま |
| Scopus の所属表記 | 載せる（`affil_scopus`、`scopus_author_id` の列と、それを使った判定）。Scopus から取った元の応答（37MB）は載せない。規約で公開できないので、リポジトリは private にする（2026-10-08） |
| Crossref | 載せない（2026-10-14、伊倉涼介）。研究者の表にも結果にも効いていなかったため（Crossref からしか取れない所属・ORCID・名前の分け方が0件）。作業用リポジトリでも `build_authorship_table.py`・`normalize_affiliations.py`・`enrich_papers_scopus.py` から Crossref を外した。研究室用リポジトリの工程番号を詰めた（旧7〜19 → 新6〜18）。この文書のほかの箇所の工程番号は旧番号のまま |
| 確認用の出力 | `data/diagnostics/<グループ>/` に書き、研究室用リポジトリでは `.gitignore` で除く（2026-10-14、伊倉涼介）。件数の要約6つ、`unmatched.csv`、`rowid_map.csv`、`author_records_keyed.csv`、`namekey_validation.json`、`sciscinet_check.csv`、`scopus_papers.csv`、`pair_zscores` 27。取得記録 `*_meta.json` と `sciscinet_check.json`（README の検算の出典）は `data/derived/` に残す。作業用リポジトリでは追跡したまま（Drive の巻き戻り対策） |
| 工程11（参考文献のタイトルの一覧） | 残す（2026-10-14、伊倉涼介） |
| スクレイピングした HTML | 載せない。README でサイトの URL と取得日を引用する |
| OpenAlex の全論文データ（23GB） | 載せない。この段階の出力（参考文献の組ごとの値）を載せ、データの日付を記録する |
| 報告書・スライド | 載せない。代わりに英語の README を書く |
| 実行環境 | インターネットに接続した状態で実行する前提（2026-10-07 決定）。ネットなしで流すための修正はしない |
| SciSciNet の著者数が 0 の論文 | 直さず SciSciNet の値をそのまま使う。README に件数と扱いを書く（2026-10-14、伊倉涼介の判断） |
| 第三者のメールアドレス | 所属の文字列に含まれるものは `@` より前を `[email]` に置き換える（2026-10-07、Claude の判断で試作に入れた。伊倉涼介の確認待ち）。ドメインは残す（ドメインで組織を判定している行があるため） |
| 付属ファイル | `.gitignore`、`CONTRIBUTING.md`（日本語。研究室のリポジトリに共通の決まり: 構造、コミットするものの基準、命名規則・コミットメッセージ。SciSci に限らない内容で、共同編集者が自分のテーマのリポジトリにも使う。2026-10-14 追加）、`AGENTS.md`（英語。このリポジトリ固有の決まり: Scopus を含むので公開しない、本筋の4つの部分、`ss_`/`own_` を分ける、キーと環境変数）、`CLAUDE.md`（`@AGENTS.md` と `@CONTRIBUTING.md`）、`.env.example`。`CITATION.cff` は作らない |
| 載せるものの基準（共同編集者向け） | 本筋（README の結果に至る工程の連なり）に直接関係するものだけ。役に立つコードでも本筋でなければ載せず、各自の作業場所に置く（2026-10-14、伊倉涼介）。共同編集者は SciSci 以外のテーマを扱うので、`CONTRIBUTING.md` はテーマによらない書き方にした |
| git の履歴 | 持ち込まない。新しいリポジトリとして作る。今のリポジトリは非公開のまま作業用に残す |
| 置き場所（GitHub のアカウント・組織） | 未定 |
| ライセンス | 付けない。README に研究室内だけで使うと書く（2026-10-08、private にしたため） |

## 再現性の基準

1. 公開した途中のデータと取得結果の保存ファイルを使えば、最終結果まで計算し直して同じ数値が出る。公開前に新しい環境で実際に流して確かめる。
2. OpenAlex API と Crossref API から取得する段階は、取得結果の保存ファイル（`data/cache/` のうち3つ、合計約22MB）を載せることで同じ結果を出せるようにする。OpenAlex は日々更新されるので、保存ファイルがないと結果が変わる。
3. 後から同じものを取れない段階は、出力を載せて取得日を記録する。ネットにつないでいても同じ版は取れない。該当するのは次の4つ。
   - スクレイピング（サイトの内容が変わる）
   - OpenAlex の全論文データ（OpenAlex 側で毎月置き換わる）
   - Scopus（契約がないと使えない）
   - SciSciNet（置き場所が変わる可能性がある）

## 載せるもの

最終結果から逆にたどって決めた。置き場所は作業用リポジトリと同じにして、パスを書き換えずに動くようにする。

| 工程 | コード | データ |
|---|---|---|
| スクレイピング | スクレイピングのノートブック4本（`notebooks/scraping/` に移す）、`src/rebuild_combined_papers.py` | `data/derived/toyota_official_scrape/` の CSV と meta（`*_raw.html`、`*_raw.json`、`aisin_imra_jp_raw_pages/` は除く） |
| OpenAlex との対応づけ | `src/openalex_link_toyota_papers.py`、`src/apply_review_decisions.py`、`src/build_paper_table.py` | `data/derived/openalex_linking/`、`data/review/openalex_review_decisions.csv`、`data/derived/papers/papers.csv`、`rowid_map.csv` |
| 所属などの補完 | `src/enrich_papers_crossref.py`、`src/enrich_papers_scopus.py`、`src/build_authorship_table.py`、`src/normalize_affiliations.py`、`src/aggregate_researchers.py` | `data/derived/paper_enrichment/`（Scopus 分は所属・著者IDに必要な列だけ）、`authorships.csv`、`authorship_affiliations.csv`、`data/derived/researchers/` |
| 参考文献・新規性の自前計算 | `src/openalex_snapshot_extract.py`、`src/build_reference_titles.py`、`src/novelty_uzzi.py`、`src/novelty_uzzi_selftest.py` | `paper_references.csv`、`data/derived/novelty/pair_zscores_*.parquet`、`paper_novelty.csv` |
| SciSciNet の検証 | `src/fetch_sciscinet_metrics.py`、`src/verify_novelty_sciscinet.py` | `sciscinet_metrics.csv`、`sciscinet_check.*` |
| SciSciNet を使った結果 | `src/build_paper_covariates.py`、`src/build_analysis_table.py`、`src/build_matched_baseline.py`、`src/analyze_novelty_v2.py`（公開版では `analyze_novelty.py`） | `paper_covariates.csv`、`data/derived/analysis/` |

取得結果の保存ファイルは `openalex_linking_cache.json` と `crossref_cache.json` の2つを載せる（既定で流す工程3・6・8が使う）。`openalex_title_cache.json` と OpenAlex の機関データ（`institutions.parquet`）は、23GB を使う工程でしか使わないので載せない。

`paper_references.json` は CSV と同じ内容で情報が欠けている（タイトル不明分を落とし、同名タイトルが衝突する）ので載せない。`paper_novelty_joined.csv` と `analysis_summary.json` は v1 の出力なので載せない。`scopus_papers.csv`（Scopus の論文単位の出力）は後段で使わないので載せない。

書き出すときの加工: Scopus の著者の表は `build_authorship_table.py` が使う列（DOI、著者順、Scopus 著者ID、姓、名、所属）だけにする。Crossref の保存ファイルから要旨を除く（641件中176件に要旨が入っていた。要旨の著作権は出版社にあり、どの工程も使っていない）。ノートブックの出力を消す。

## 作業の段階

各段階は、完了条件を満たしてから次に進む。

### 段階0: 前提を確定する

- ~~今井先生にライセンスを確認する~~ → private にしたので不要（2026-10-08）
- Scopus の所属表記を載せてよいか → 2026-10-08 確認。**載せられない。** Elsevier の API 利用方針（`dev.elsevier.com/policy.html`）の「Academic Research」は、Scopus のデータをウェブサイトなど公の場に出すことを認めていない（論文として出版する形を除く）。再現のための共有も、特定の相手に対して、書面で申請して Elsevier の書面の承認を得た場合に限る。API Service Agreement も、Elsevier の内容とそこから作ったものの再配布を禁じている。→ 伊倉涼介の判断で、Scopus は外さずにリポジトリを private にして研究室内だけで管理することにした（2026-10-08）。規約上、見せてよいのは契約している機関（大阪大学）の人だけなので、研究室の人が全員阪大所属かを確認する。参考: Scopus を使わずに工程8〜10を作り直すと、所属が分かる著者 4,390 → 4,367（4,448中）、トヨタ系の組織が分かる著者 2,564 → 2,527、組織をまたいだ論文 76 → 72、所属文字列から見た産学連携 331 → 343。README の結果（新規性の検算、組織の差、仮説2つ）は Scopus を使っていないので変わらない
- SciSciNet v2 の再配布の条件を確認する（抜き出した値を載せるため）→ 2026-10-07 確認。初版（figshare）は CC0。v2 の配布ページ（`northwestern-cssi.github.io/sciscinet`）には利用条件の記載がなく、論文（Lin et al. 2023）の引用を求めているだけ。README で引用している
- SciSciNet の著者数が 0 の論文の扱いを決める（log.md 2026-10-07）→ 2026-10-14 決定。SciSciNet の値をそのまま使い、直さない（伊倉涼介の判断）。README と data/README に、0 の件数と分析での扱い（対数をとるときに1とする、破壊性の比較では0〜1人の論文と比べる）を書いた
- 置き場所（GitHub のアカウント・組織）を決める

完了条件: 上の4点がこの文書の決定事項の表に書かれている。ただし段階1〜3は、段階0と並行して進めてよい（ライセンスと公開先は中身に影響しない）。著者数 0 の扱いが決まるまでは、段階4の数値の照合を確定させない。

### 段階1: 作業用リポジトリ側でコードを整える

公開用だけを直すと作業用とずれるので、作業用リポジトリで直す。

- コードに直接書かれたメールアドレス（OpenAlex・Crossref への連絡先）を環境変数から読むようにする
- 絶対パス（`/Users/...`）をなくす
- 23GB の OpenAlex データが要る工程（参考文献の一覧、論文の属性、新規性の自前計算、比較相手の一般論文の選び出し）は、既定では流さず、載せてある出力を使う。`build_matched_baseline.py` は既存の `SCISCI_REUSE_SAMPLE=1` で選び出し済みの一般論文から順位をつける
- スクレイピングのノートブック4本を、公開版では `notebooks/scraping/` に置く（書き出しのときに移す。作業用では `notebooks/exploration/` のまま）
- `reparse_aisin_imra_jp.py` の修正内容を AISIN IMRA 日本の取得ノートブックに取り込み、スクリプトは外す（保存した HTML を読み直すスクリプトで、HTML を載せないと動かない）
- 統合用ノートブック（`toyota_official_scrape_consolidate.ipynb`）は `rebuild_combined_papers.py` と処理が同じなので外す
- `analyze_novelty_v2.py` を、公開版では `analyze_novelty.py` に改名する（書き出しのときに改名する。作業用には v1 の `analyze_novelty.py` があるため）
- スクリプトとノートブックの説明文から、作業の経緯（段階の番号、先生への言及、日付つきの修正履歴、v1 の失敗）と自分の環境のパスを除く
- 使っているライブラリのバージョンを固定した `requirements.txt` を作る（現在の環境は `~/.venvs/scisci-rir`、Python 3.14.3）
- 公開版にだけ置くファイル（README、AGENTS.md など）は作業用リポジトリの `public_release/` に置く
- 全工程を順に流す入口 `reproduce.ipynb` を作る。既定では再現できる工程だけを流し、出力が載せてある値と一致するかを確かめる。設定を切り替えると、再現できない工程（取得、Scopus、23GB を使う工程）も流す

完了条件: 作業用リポジトリで入口を流し、`data/derived/` の出力が今の値と一致する。

### 段階2: 書き出しスクリプトを作る

- `scripts/export_public.py` に「載せるファイルの一覧」を持たせ、一覧にあるものだけを Drive の外の `~/scisci-public/` にコピーする
- コピーのときに、Scopus の取得結果を必要な列だけに減らす
- 書き出し後に、メールアドレス・`/Users/` を含むパス・API キーらしい文字列・載せないと決めたファイル名が残っていないかを検査する

完了条件: 書き出しスクリプトを流すと `~/scisci-public/` ができ、検査で何も見つからない。

### 段階3: README とデータの説明を書く（英語）

- 研究の目的、データの出どころ（4サイトの URL と取得日、OpenAlex のデータの日付、SciSciNet の版、Scopus の利用条件）、工程の順番、再現の手順、再現できない段階とその理由
- 4サイトの URL
  - 未来創生センター: `https://www.toyota.co.jp/jpn/tech/partner_robot/search/json/articles.json`
  - 豊田中央研究所: `https://www.tytlabs.co.jp/ja/technology/papers.html`
  - AISIN IMRA 日本: `https://www.aisin.com/jp/group/imra-japan/paper/`
  - AISIN IMRA 米国: `https://www.imra.com/imra-research-papers/`
- 表の列の説明（`data/README.md` を英訳し、載せない表の記述を除く）
- 組織名は正式名称の「未来創生センター」（Frontier Research Center）を使う

あわせて付属ファイルを作る。

- `.gitignore`: macOS・Python・Jupyter の自動生成ファイル、仮想環境、`.env`、`data/cache/scopus_*`（Scopus の元の応答。工程を流し直したときに誤って載せないため）、`*.duckdb` と 23GB の OpenAlex データ
- `AGENTS.md`（英語）: 目的と工程の順番（README へのリンク）、API キーは環境変数から読みコードに書かない、`data/derived/` を手で編集しない、Scopus の元データと 23GB の OpenAlex データを載せない、標準ライブラリと pandas 以外の複雑な処理に説明のコメントをつける。作業用の `AGENTS.md` にある個人の事情（Drive、自動取得、バックアップ、SSH 鍵、阪大の契約、報告の書き方）は入れない
- `CLAUDE.md`: `@AGENTS.md` の1行
- `.env.example`: 環境変数の名前だけを並べ、値は空にする（OpenAlex・Crossref への連絡先メールアドレス、Scopus の API キー）。README にも同じことを書く

完了条件: README の手順だけを見て、段階4の確認を流せる。

### 段階4: 新しい環境で再現を確かめる

- `~/scisci-public/` を一時フォルダにコピーし、新しい Python 環境に `requirements.txt` から入れて、入口を流す
- 出力を、公開するデータと照合する

完了条件: すべての出力が一致する。乱数を使う部分は種を固定して一致させる。

### 段階5: GitHub に置く

- `~/scisci-public/` で `git init` し、1回目のコミットを作る
- GitHub に **private** の新しいリポジトリを作り、push する（push は伊倉涼介が行う）。研究室の人を招待する

完了条件: GitHub のリポジトリを `git clone` して、段階4と同じ確認が通る。
