本リポジトリでは今井泰介先生からの依頼を受けてサイエンスオブサイエンスの文脈で研究活動を行う．

タスクの進め方や内要はSci-sci-tasks.mdというファイルに記述してある．

私は伊倉涼介 (Ryosuke) である．

はじめに要求があった文献サイエンスオブサイエンスについては読了済みである．

各AIエージェントは与えられたタスクの遂行に際して，命令されたコーディングや，タスクの進め方などについて意見を行う．

やり取りは日本語で行うこと．

文章を生成する際は過度な修飾表現を用いないこと．

私は今井先生のラボの学生ではなく，大阪大学大学院工学研究科の田中雄一研究室の学生であり，RAとして今井先生の研究に協力している．

API取得や解析のコードはjupyter notebookを用いること．標準ライブラリとpandas以外のライブラリを用いる場合は，複雑な処理，メソッドに関してはコメントアウトで日本語で説明文を追記すること．

研究用データベースのWeb画面・APIの確認、取得可否の検証、必要な文書化は、各AIエージェントが可能な範囲で完結させる。伊倉涼介にWeb画面の手操作を依頼しない。ただし、大阪大学個人ID・パスワード、外部サービスのパスワード、認証Cookie、APIキー等の秘密情報をチャットやリポジトリに入力・保存・共有させてはならない。認証が必要な場合は、公式API、契約済みのプログラムアクセス、または秘密情報を露出しない安全な認証方法を優先する。利用規約に反するスクレイピングや大量ダウンロードは行わない。

外部機関の承認、契約、本人確認など、伊倉涼介にしか実行できない作業が残る場合、AIエージェントは単に情報源や選択肢を示して終えてはならない。最小の必要作業を一つずつ明示し、目的、実行先、コピーして使える文面、完了条件、完了後に伊倉涼介が返すべき非秘密情報を提示する。伊倉涼介が片手間でも実行できるよう、不要な判断やWeb画面上の探索を要求しない。秘密情報の共有を求めない。

Scopus・WoSなど、大阪大学の契約や個人申請が絡む外部APIの利用手順書・申請書の文面を作成した場合、伊倉涼介に実際の提出・送信・入力の前に内容を確認してもらう。確認前に代理送信・代理入力をしない。

## 進捗の記録先（3つを使い分ける）

| ファイル | 役割 | 読み手 |
|---|---|---|
| `STATUS.md` | 目的・計画・進捗・ブロッカーの要約。**今井先生にそのまま送れる状態を常に保つ** | 今井泰介先生 |
| `log.md` | 作業の詳細ログ。経緯・試行錯誤・失敗と修正・技術的な知見を書く | 伊倉涼介・AIエージェント |
| `docs/reports/` | 個別の検証・分析レポート | 今井先生・共同作業者 |

作業が一区切りついたら、`log.md` に詳細を書いたうえで **`/status` スキルを使って `STATUS.md` を更新する**。`STATUS.md` に経緯や実装の詳細を書かない（それは `log.md` の役割である）。更新ルールの詳細は `.claude/skills/status/SKILL.md` に書いてある。

## 自動データ取得（毎日 JST 9:30）

伊倉涼介はこの作業を月曜と木曜にしか行わない。その間もデータ取得を進めるため、launchd による自動実行を設定してある（`~/Library/LaunchAgents/org.msp-lab.scisci-fetch.plist`）。

**重要な制約**: macOS のプライバシー保護(TCC)により、launchd が起動したプロセスは Google Drive 配下（`~/Library/CloudStorage`）を読めない（`Operation not permitted` になる）。そのため自動取得は Drive の外の **`~/scisci-auto/`** で完結させ、結果を後から同期する構成にしてある。Drive 上に置いたスクリプトを launchd から直接叩くことはできない。

**セッション開始時にやること**: `scripts/sync_auto.sh` を実行する。自動取得の結果をリポジトリに回収し、進捗（`~/scisci-auto/FETCH_DIGEST.md`）を表示する。伊倉涼介が「同期して」と言った場合も同じ。

**取得スクリプトを変更したとき**: 必ず `scripts/sync_auto.sh push` を流す。`~/scisci-auto/src/` にコピーされているものが実際に動くので、これを忘れると自動実行が古いコードのまま走り続ける。

**取得処理を追加するとき**: `~/scisci-auto/daily_fetch.sh` の `STEPS` 配列に足す。各スクリプトは (a) ディスクキャッシュを持ち取得済み分でクォータを消費しない、(b) クォータ切れを検出したら中断して途中結果を保存する、(c) 入出力パスを環境変数 `SCISCI_INPUT_CSV` / `SCISCI_OUT_DIR` / `SCISCI_CACHE_PATH` で差し替えられる、の3条件を満たすこと。

## バックアップ（必須）

2026-08-06、Google Drive.app の更新(v128→v129)と再起動をきっかけに、**リポジトリのフォルダが 2026-07-27 の状態へ巻き戻り、8/3 に作成した成果物を失った**。Drive の中で `git init` しても、Drive ごと巻き戻れば `.git` も一緒に消えるため対策にならない。

**作業を終える前に、以下の2つを必ず実行する。**

1. `git add -A && git commit` して **`git push`**（リモート: `git@github.com:ryosuke0828/sci-sci-toyota.git`、private）。これが第一の防御であり、Drive が巻き戻っても `git clone` で完全に復旧できる。
2. `scripts/backup_repo.sh snapshot`（Drive 外の `~/scisci-backup/` にミラーと日付つき世代を残す）。`.gitignore` で除外している大容量キャッシュはこちらにしか残らない。

**SSH 鍵の注意**: このマシンには GitHub アカウントが2つある（`ryosuke0828` と `luida-ikura`）。既定の鍵では認証できないため、リポジトリ単位で `core.sshCommand` に `~/.ssh/id_ed25519_ryosukee0828` を指定してある。`git clone` し直した場合は再設定が必要:

```
git config core.sshCommand "ssh -i ~/.ssh/id_ed25519_ryosukee0828 -o IdentitiesOnly=yes"
```

## Scopus API 利用上の注意（2026-07-21 阪大図書館回答・エルゼビア公式資料に基づく）

- 大阪大学の契約でScopus APIは研究目的で利用可能（阪大図書館 R26-085 回答）。
- API Keyは `dev.elsevier.com` で個人サインインして取得する（伊倉涼介本人のみ実行可）。取得後のAPI Keyは秘密情報として扱い、チャット・ノートブック・リポジトリに書かない。
- 既定の認証方式はIPアドレス認証で、**阪大の契約IPアドレス範囲内からのアクセスが前提**。学外ネットワーク・別拠点から使う場合はinsttokenの追加申請が必要（エルゼビアAPIチームへ個別連絡）。
- API Keyには週間クォータがある。Author Retrieval・Affiliation Retrieval・Affiliation Search・Author Searchは週5,000件、Abstract Retrievalは週10,000件、Scopus Search・Abstract Citation Count・Serial Titleは週20,000件が既定値（要求により増枠可）。429は上限超過。
- Citation Overview API、refEIDフィールド、Index Keywordフィールド、Affiliation/Author RetrievalのDOCUMENTSビューは追加申請制で、1プロジェクトにつきAPI Key 1本のみに特別権限が付与される方針。
- 10万件超の一括取得は非推奨（後半で応答が遅くなりサーバー負荷が高まるとElsevier自身が明記）。出版年等で分割して取得する。
- 公式に紹介されている実装例: Python SDK [elsapy](https://github.com/ElsevierDev/elsapy)、コミュニティ製 [pybliometrics](https://github.com/pybliometrics-dev/pybliometrics)。
- 詳細な上限緩和・insttoken申請・アクセス制御APIの申請先: https://service.elsevier.com/app/contact/supporthub/dataasaservice/
- 出典PDF（Gmail添付、要約済み）: `Elsevier_APIs_2024年3月.pdf`、`Scopus API Guide_V1_20230907.pdf`。詳細は[アクセス確認と利用計画](docs/reports/scholarly_database_access_plan.md)参照。

## WoS（Web of Science）API 利用上の注意（2026-07-17 阪大図書館回答に基づく）

- 大阪大学の契約で使えるのは **Web of Science Starter API のみ**。Expanded APIの契約はない（阪大図書館 R26-086 回答）。
- **Starter APIのレスポンスには著者住所・所属(affiliation)、Org Enhanced、ORCID、Cited References、主題分類が含まれない**（これらはExpanded限定フィールド）。取得できるのはUID・タイトル・著者名・巻号ページ・DOI/ISSN/ISBN・出版日・Times Cited等の書誌情報のみ。**Starter APIのレスポンス単体ではトヨタ所属の直接検証はできない**。検索クエリ（Organization等のフィールドタグでの絞り込み）で候補文献を特定し、DOI照合でOpenAlex側と突き合わせる設計にする。
- `Times Cited` は **Core Collection限定の被引用数**であり、Web of Science全体の被引用数ではない。OpenAlexの`cited_by_count`と単純比較・合算しない（別列で保持し感度分析に使う）。
- レート制限（2023年1月時点・阪大図書館提供資料）: Freeプラン=1req/秒・50req/日・年5万件・1req最大50件。Institutional（阪大契約構成員向け）=5req/秒・1000req/日・1req最大50件。
- 個人でWeb of Science IDを作成し、Clarivate Developer Portalで**本人が**API利用申請する（Application ID/Application Nameは任意文字列でよい）。承認後にプラン（Free Trial / Free Institutional Member / Free Institutional Integration）を選択する。この申請作業は伊倉涼介本人にしかできない。
- 出典: 阪大図書館回答メール本文、添付 `Web of Science API_Field_JPN.xlsx`（フィールド一覧・レート制限表）。詳細は[アクセス確認と利用計画](docs/reports/scholarly_database_access_plan.md)参照。


報告をわかりづらくするな．簡単なことをしているなら簡単な報告書を書け．