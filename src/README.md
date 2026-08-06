# 分析モジュール

| モジュール | 内容 |
|---|---|
| `openalex_random_impact_rule.py` | Sinatra et al. のRandom Impact Rule再現用の取得・集計処理 |
| `openalex_h_index_prediction.py` | Hirschのh指数予測力再現用の取得・集計処理 |

通常は `notebooks/reproductions/` から実行する。CLIで実行する場合も、リポジトリ直下から `python3 src/<module>.py` とする。既定キャッシュは `data/cache/` に置く。
