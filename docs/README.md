# 文書

`reports/` には、結論・方法・限界・出典をまとめた報告書を置く。`notes/` には探索時の作業メモを置く。`plans/` には作業計画を置き、決定が変わったら書き換える。

## 正本

| 文書 | 内容 |
|---|---|
| [reports/pipeline_overview.md](reports/pipeline_overview.md) | スクレイピングから欠損値補完・ノイズ除去までの全体像（第1段階）。処理の流れと設計判断を一読で掴むためのもの |
| [reports/pipeline_details.md](reports/pipeline_details.md) | 同（第2段階）。実装・しきい値・実測値・落とし穴を残した詳細版 |
| [reports/scholarly_databases_master_report.md](reports/scholarly_databases_master_report.md) | OpenAlex、Crossref、Semantic Scholar、Scopus、WoSの比較、アクセス検証、研究用データ設計を統合した総合報告 |

## 補足資料

| 文書 | 内容 |
|---|---|
| [reports/academic_database_comparison.md](reports/academic_database_comparison.md) | 付録A: OpenAlex、Semantic Scholar、WoSの比較詳細 |
| [reports/scholarly_database_access_plan.md](reports/scholarly_database_access_plan.md) | 付録B: Crossref、Semantic Scholar、Scopus、WoSのアクセス確認と利用計画 |
| [reports/pilot_scopus_wos_verification.md](reports/pilot_scopus_wos_verification.md) | 受領した著者リスト（9,429名）の精度をScopus・WoSで照合したパイロット検証 |
| [reports/random_impact_rule_reproduction.md](reports/random_impact_rule_reproduction.md) | Random Impact Ruleの外的再現 |
| [reports/h_index_prediction.md](reports/h_index_prediction.md) | h指数予測力の再現 |
| [reports/scisci_foundation_review.md](reports/scisci_foundation_review.md) | 段階1-1 精読メモ。SciSciNet の novelty / disruption の実装仕様と、我々の実装との食い違い5点 |
| [reports/novelty_first_results.md](reports/novelty_first_results.md) | **数値は無効**。新規性の最初の結果（718件）。値の定義が SciSciNet と違うことが後から判明した |
| [notes/openalex_exploration.md](notes/openalex_exploration.md) | OpenAlex探索メモ |

## 計画

| 文書 | 内容 |
|---|---|
| [plans/novelty_hotstreak.md](plans/novelty_hotstreak.md) | novelty / hot streak 解析の作業計画。決定事項、実測した前提（OpenAlexスナップショットの規模・所要時間）、段階0〜3の作業内容とリスク |

## テンプレート

| 文書 | 内容 |
|---|---|
| [templates/library_api_access_inquiry.md](templates/library_api_access_inquiry.md) | Scopus・WoS APIの利用可否を阪大図書館へ問い合わせるための最小手順と貼り付け文面 |
