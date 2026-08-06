# ノートブック

| ノートブック | 用途 | 入力・注意 |
|---|---|---|
| [exploration/openalex_exploration.ipynb](exploration/openalex_exploration.ipynb) | 田中雄一氏を例にしたOpenAlex APIの手動探索 | ライブAPIを利用する |
| [access_checks/scholarly_database_access_check.ipynb](access_checks/scholarly_database_access_check.ipynb) | Crossref・Semantic Scholar の公開 API、Scopus・WoS API、大阪大学学外アクセス入口の到達性確認 | 1 DOI だけ照会する。Scopus / WoS は環境変数の API キーがある場合のみ実行し、Web UI はSAML認証前のリダイレクトだけを検査する |
| [reproductions/h_index_prediction.ipynb](reproductions/h_index_prediction.ipynb) | Hirschのh指数予測力の再現 | `src/` と `data/cache/openalex_h_index_prediction.json` を使用 |
| [reproductions/random_impact_rule_external.ipynb](reproductions/random_impact_rule_external.ipynb) | Random Impact Ruleの固定入力による外的再現 | ネットワークを使わず、固定キャッシュから再計算する |
| [reproductions/random_impact_rule_legacy.ipynb](reproductions/random_impact_rule_legacy.ipynb) | 先行版のRandom Impact Ruleパイプライン | 比較用に保持。新規の結論には外的再現ノートブックを優先する |

APIキーをノートブックへ直接書かない。ライブAPIを使う新規実験では環境変数から読み込み、取得日時・パラメータ・キャッシュを保存する。

大阪大学の個人 ID・パスワードはノートブックへ入力しない。Scopus・Web of Science の Web UI 用認証と API キーは別物である。
