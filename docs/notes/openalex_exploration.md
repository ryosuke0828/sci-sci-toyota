# OpenAlex 調査メモ (Ikura)

最終更新: 2026-06-08

トヨタ研究者の研究活動をScience of Scienceの観点で分析するプロジェクトの一環として、
OpenAlexで何が取得可能で何が難しいかを調査した記録。

ターゲット研究者: 田中雄一 (Yuichi Tanaka)。データ取得は全てAPI経由で行う（`openalex_exploration.ipynb`）。

---

## エンティティ構成

OpenAlexは5つの主要エンティティで構成される。

- Works（論文・書籍など）
- Authors（著者）
- Institutions（機関）
- Sources（ジャーナル・会議・リポジトリ）
- Topics（トピック分類）

加えて Funders（資金提供者）、Publishers（出版社）がある。

---

## 取得可能な情報

### Works（論文・書籍など）
- メタデータ: タイトル、出版年・日付、`type`（article / book-chapter / dataset 等）、言語
- 識別子: DOI、PMID、OpenAlex ID、MAG ID
- 引用: 被引用数（`cited_by_count`）、参照文献リスト（`referenced_works`）、関連論文（`related_works`）
- 著者情報: `authorships`（著者・所属・著者順 first/middle/last・対応著者フラグ）
- 掲載先: `primary_location`（ジャーナル名・出版社・ISSN）、他の配置先（`locations`）
- 分類: `topics`（domain→field→subfield→topic の4階層）、`concepts`（旧分類、廃止予定）、`keywords`、`sustainable_development_goals`
- オープンアクセス: `open_access`（is_oa、OAステータス gold/green/hybrid 等）
- 資金情報: `grants`（funder名・award ID）※記録率は低い
- 本文由来: `abstract_inverted_index`（アブストラクトを逆インデックス形式で復元可能）

### Authors（著者）
- 名前、別名（`display_name_alternatives`）、ORCID
- 論文数、被引用数、`summary_stats`（h-index、i10-index、2yr mean citedness）
- 所属履歴（`affiliations`: 機関と在籍年）、最終所属
- 年別の論文数・被引用数（`counts_by_year`）

### Institutions / Sources / Topics
- 機関: 名称、国、種別（education / company 等）、ROR ID、地理情報、親子機関関係
- Sources: ジャーナル/会議名、ISSN、出版社、APC（掲載料）、OA区分
- Topics: 4階層の分類体系と各説明

### Funders / Publishers
- 名称、国、関連論文数（ただしWork側の grant 記録自体が乏しい）

---

## 取得が難しい・欠けている情報

| 項目 | 状況 |
|---|---|
| アブストラクト全文 | 逆インデックスのみ。著作権上、生テキストでは提供されない（復元は可能だが完全でない場合あり） |
| 本文・図表 | 一切なし。OpenAlexはメタデータDBであり全文DBではない |
| 資金情報（grants） | フィールドは存在するが、値が入っている論文は少数。網羅性が低い |
| 著者の名寄せ精度 | 同名異人の混在・一人が複数IDに分裂する問題。特に日本人名・中国名で顕著 |
| 所属の正確性・粒度 | 学部/研究室レベルは取れない。機関名の表記ゆれ、過去所属の欠落 |
| 著者の属性 | 性別、年齢、学位、キャリア段階、雇用形態などは無い |
| 引用の網羅性 | 参照文献は出版社提供依存。古い論文・非英語論文で欠落が多い |
| 引用の文脈・極性 | 「どの文で・肯定的か否定的か引用したか」は無い |
| 会議録・プレプリント・特許 | カバーはするが、ジャーナル論文に比べ粒度・整合性が落ちる。特許は基本対象外 |
| 著者の貢献区分 | CRediT（執筆/解析等の役割分担）情報は無い |
| 企業・産業界の研究 | 企業所属者は学術機関より名寄せ・所属情報が不安定 |

---

## Toyotaプロジェクトへの含意

依頼の文脈（トヨタ研究者の協働・知識生成の分析）で特に効く制約。

1. **著者名寄せ** — トヨタの研究者・技術者を正確に同定するのが最大の難関。日本人名の曖昧性 + 企業所属者の名寄せ不安定さが重なる。ORCIDがある人は信頼できるが、企業研究者はORCID保有率が低い傾向。
2. **特許が対象外** — 企業研究はアウトプットが特許に偏る。論文だけ見ると活動を過小評価する。別ソース（Google Patents / PatentsView 等）との突合が必要。
3. **所属が機関レベル止まり** — 「トヨタのどの部署/研究所か」は取れない。組織内の協働構造を見るには別データが要る。
4. **資金情報の欠落** — どの研究にどう投資されたかはOpenAlexからはほぼ追えない。

---

## 実装上の注意（ノートブックから得た知見）

- **polite pool**: User-Agentヘッダに `mailto:` でメールアドレスを入れるとレートリミットが緩和される。
- **Author ID形式**: 検索結果のIDは `https://openalex.org/A5101751423` のフルURL形式で返る。APIに渡す際は短縮ID `A5101751423` に変換する必要がある。
- **`author.id` が None になりうる**: 名寄せ未確定の著者は `author.id` が `None`。`AUTHOR_ID in a["author"]["id"]` のような比較は `TypeError` になるため、None を空文字に変換するなどの防御が必要。
- **ページネーション**: `cursor=*` を使い `meta.next_cursor` を辿る。`per_page` は最大200。

---

## TODO / 次のステップ

- [ ] 田中雄一の正しいAuthor IDを確定（候補: 名古屋大 `A5101751423` など。所属・論文内容で要確認）
- [ ] フィールド充足率の集計（例: トヨタ所属論文のうち grant が入っている割合）を実データで測定
- [ ] Sota のノートと統合し、今井先生に主要な観察を報告
