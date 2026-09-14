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
| [reports/sciscigpt_review.md](reports/sciscigpt_review.md) | 段階1-2 精読メモ。SciSciGPT の構成と評価、段階2で使える資源（SciSciCorpus） |

| [reports/novelty_hotstreak_literature.md](reports/novelty_hotstreak_literature.md) | 段階2 文献調査。指標の種類・妥当性の検証結果・採否の決定。**被引用で新規性指標を検証してはいけない** |
| [reports/novelty_measure_verification.md](reports/novelty_measure_verification.md) | 新規性の指標を作り直し、SciSciNet の公開値と突き合わせた結果（581件）。実装の誤り5点の修正、1.31倍ずれた原因の特定、残る限界 |
| [reports/novelty_analysis_results.md](reports/novelty_analysis_results.md) | **最新の分析結果**。条件を揃えた順位でみるとトヨタ論文は世の中の真ん中。仮説2つは不支持。組織差だけが残る |
| [reports/novelty_first_results.md](reports/novelty_first_results.md) | **数値は無効**。新規性の最初の結果（718件）。値の定義が SciSciNet と違うことが後から判明した。作り直した値は上の報告書 |
| [notes/openalex_exploration.md](notes/openalex_exploration.md) | OpenAlex探索メモ |

## 別件: AIの使い方の write-up（`Sci-sci-tasks.md` の依頼）

novelty / hot streak の解析とは別系統の成果物。

| 文書 | 内容 |
|---|---|
| [reports/sciscigpt_literature.md](reports/sciscigpt_literature.md) | SciSciGPT の周辺文献調査。同種システムの地図、分野の評価の弱さ、AIの研究利用への実証的な批判（個人の成果は伸びるが科学全体の多様性は狭まる） |

## 計画

| 文書 | 内容 |
|---|---|
| [plans/novelty_hotstreak.md](plans/novelty_hotstreak.md) | novelty / hot streak 解析の作業計画。決定事項、実測した前提（OpenAlexスナップショットの規模・所要時間）、段階0〜3の作業内容とリスク |

## テンプレート

| 文書 | 内容 |
|---|---|
| [templates/library_api_access_inquiry.md](templates/library_api_access_inquiry.md) | Scopus・WoS APIの利用可否を阪大図書館へ問い合わせるための最小手順と貼り付け文面 |
