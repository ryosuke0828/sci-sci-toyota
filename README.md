# Sci-sci

今井泰介先生から依頼された Science of Science の調査・分析用リポジトリである。対象はトヨタ自動車の研究者・技術者の研究活動、共同研究、知識生成である。

## 構成

| 場所 | 内容 |
|---|---|
| `docs/reports/` | 比較・再現実験の報告書 |
| `docs/notes/` | OpenAlex探索時の作業メモ |
| `notebooks/exploration/` | APIの手動探索ノートブック |
| `notebooks/access_checks/` | 文献データベースごとの API 到達性・認証要件を確認するノートブック |
| `notebooks/reproductions/` | 既存Science of Science研究の再現ノートブック |
| `src/` | ノートブックから呼び出す分析モジュール |
| `data/cache/` | API応答の固定キャッシュ。再現実験の入力なので削除しない |
| `data/derived/` | ノートブックが生成した処理済みデータと実行メタデータ |
| `figures/` | 報告書が参照する図 |
| `toyota_data/` | OpenAlex由来のトヨタ関連研究者テーブルとその説明書。Scopus/WoSによる精度向上作業の対象 |

ルートには、案内の `README.md`、作業規約の `AGENTS.md`、タスク定義の `Sci-sci-tasks.md`、進捗記録の `log.md` のみを置く。

## 主な成果物

- [学術データベース調査・アクセス検証総合報告](docs/reports/scholarly_databases_master_report.md)
- [データベース比較の詳細付録](docs/reports/academic_database_comparison.md)
- [アクセス確認・利用計画の詳細付録](docs/reports/scholarly_database_access_plan.md)
- [阪大図書館へのAPI利用可否問い合わせテンプレート](docs/templates/library_api_access_inquiry.md)
- [学術データベースのアクセス検査ノートブック](notebooks/access_checks/scholarly_database_access_check.ipynb)
- [Random Impact Rule の外的再現](docs/reports/random_impact_rule_reproduction.md)
- [h指数予測力の再現](docs/reports/h_index_prediction.md)
- [ノートブック一覧](notebooks/README.md)

## 実行上の注意

`notebooks/reproductions/random_impact_rule_external.ipynb` は `data/cache/openalex_random_impact_rule.json` を固定入力にする。これは外部APIを再照会せず同じ計算結果を検証するためである。ライブAPIで再収集する場合は、OpenAlex API key、現行のTopicsフィルタ、著者同定の手順を更新し、別スナップショットとして保存する。
