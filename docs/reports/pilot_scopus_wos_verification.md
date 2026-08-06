# パイロット検証レポート: toyota_authors.csv の所属主張を Scopus + WoS で照合する

実施日: 2026-08-03（2026-08-06 に再実行して同一結果を確認）
対象: `toyota_data/toyota_authors.csv`（9,429名、OpenAlex由来）から層化サンプリングした100名
スクリプト: `src/pilot_scopus_wos_verification.py`（照合）・`src/pilot_revise_verdicts.py`（判定の作り直し）
データ: `data/derived/pilot_scopus_wos/`

---

## 1. 結論（先に読む用）

1. **Scopus/WoS による照合は機能する。** 100名・511 API呼び出しでエラー0件。クォータ消費は本格展開でも問題にならない水準。
2. **OpenAlex が「現在トヨタ所属」と主張する著者のうち、外部DBで裏付けが取れたのは 49〜63%** にとどまる。層によって差が大きい。
3. **スイス法人エンティティ経由の著者は、他エンティティ経由より明確に精度が低い**（裏付け率 48.6% vs 62.9%、矛盾率 31% vs 17%）。README §3-1 の既知バグが定量的に裏付けられた。
4. **異常キャリア長で抽出した「既知ノイズ」層の本質は、名寄せ破綻ではなく「ありふれた名前」である。** 同姓同名フラグ率が 76.7%（他層は約15%）。
5. **WoS Starter は、Scopus が見つけられなかったトヨタ所属を1件も新規に発見しなかった**（`wos_support`・`group_support` とも0件）。WoSの価値は「新規発見」ではなく「Scopusの判定の裏付け（確信度を上げること）」にある。

---

## 2. サンプリング設計

乱数シード `20260803`。3層に分けて計100名を抽出した（層は互いに排他）。

| 層 | 定義 | 母集団 | 抽出 | 狙い |
|---|---|---|---|---|
| `known_noise` | `first_pub_year < 1960` または キャリア長 > 60年 | 1,250名 | 30名 | 名寄せ破綻が疑われる層。OpenAlexの主張が誤っている可能性が高い |
| `current_swiss` | 現所属 かつ スイス法人エンティティ経由 かつ 上記ノイズでない | 1,984名 | 35名 | README §3-1 の「スイス法人への誤帰属バグ」の検証 |
| `current_other` | 現所属 かつ スイス法人経由でない かつ 上記ノイズでない | 1,670名 | 35名 | 対照群 |

## 3. 照合方法

**Scopus Author Search** (`content/search/author`)
- `AUTHLASTNAME(姓) AND AUTHFIRST(名)`。OpenAlexの`name`は姓名の順序が不定なので、0件なら入れ替えて再試行する。
- 候補を最大5件保持し、各候補の`affiliation-current`に `toyota|imra|aisin|denso` のいずれかが含まれるかで判定する（2026-07-27の探索で「上位1候補だけでは不十分」と分かっているため）。
- `AF-ID()` ではなく `AFFIL()` の自由文字列一致を使う（AF-ID厳密一致は取りこぼしが大きい）。

**WoS Starter** (`/documents`)
- レスポンスに所属フィールドがないため、検索クエリ側の組織フィルタで間接的に判定する。
- `AU="姓, 名"` 単独、`AU=... AND (トヨタ本体のOR結合)`、`AU=... AND (トヨタグループのOR結合)` の3クエリを投げる。
- **`OG=` は表記ゆれを統合しないので OR 結合が必須**（2026-08-03の機能検証で確認）:
  - 本体: `OG="Toyota Motor Corporation" OR OG="Toyota Motor Co Ltd"`
  - グループ: 上記 + `OG="Toyota Central R&D Labs Inc" OR OG="IMRA America Inc" OR OG="IMRA Europe" OR OG="Aisin Seiki"`

## 4. 初版判定の失敗と、その修正

初版は「`AU=X AND OG=Toyota` がヒットしたら所属の証拠」とみなしていた。これは**誤り**である。この複合クエリは「Xと同姓同名の**別人**がトヨタと共著していた」場合にもヒットするためである。

証拠: WoSのみを根拠に「確認済み」と判定した12名は、**名前のみヒット数の中央値が862件**だった。一方、Scopusとも一致した20名は**中央値9.5件**。桁が2つ違う。

そこで「名前のみヒット数 > 50」を**ありふれた名前の代理指標**とし、この場合はWoS単独の証拠を採用しないよう判定を作り直した（`src/pilot_revise_verdicts.py`）。

| 改訂判定 | 定義 |
|---|---|
| `strong_support` | Scopusの候補の現所属がトヨタ系 **かつ** WoSでも本体ヒット。最も強い |
| `scopus_support` | Scopusの候補の現所属がトヨタ系（Scopusは候補著者単位で所属を返すので人物特定性が高い） |
| `wos_support` | WoS本体ヒットあり、かつ名前がありふれていない |
| `ambiguous_common_name` | WoS本体ヒットはあるが名前がありふれている。**証拠として採用しない** |
| `contradicted` | Scopus候補は存在するが、どれもトヨタ所属でない |
| `no_evidence` | 両DBに候補なし。**ノイズ確定ではない**（Scopus/WoS非収録の可能性） |

## 5. 結果

### 5-1. 層 × 改訂判定

| 層 | strong_support | scopus_support | ambiguous_common_name | contradicted | no_evidence |
|---|---|---|---|---|---|
| `current_other` | 11 | 11 | 2 | 6 | 5 |
| `current_swiss` | 6 | 11 | 2 | 11 | 5 |
| `known_noise` | 3 | 6 | 8 | 13 | 0 |

`wos_support`・`group_support` は**全層で0件**。

### 5-2. OpenAlexの主張の裏付け率

| 層 | 裏付けあり / 全体 | 率 |
|---|---|---|
| `current_other` | 22 / 35 | **62.9%** |
| `current_swiss` | 17 / 35 | **48.6%** |
| `known_noise` | 9 / 30 | **30.0%** |

### 5-3. 同姓同名フラグ率（WoS名前のみヒット > 50件）

| 層 | 率 |
|---|---|
| `current_other` | 14.3% |
| `current_swiss` | 17.1% |
| `known_noise` | **76.7%** |

## 6. 個別事例

**明確に一致した例（`strong_support`、名前のみヒットが1件＝人物特定性が高い）**

| 名前 | 層 | Scopusの現所属 |
|---|---|---|
| Fumiaki Kawaii | current_other | Toyota Motor Corporation |
| Yasuhiro Nonobe | current_other | Toyota Motor Corporation |
| Nobuyuki Ishihara | current_other | Toyota Motor Corporation |
| Naohisa Nishino | current_swiss | **Toyota Central R&D Labs., Inc.** ← スイス法人経由だが実体は豊田中研。README §3-1 のバグの実例 |

**スイス法人経由で矛盾した例（`contradicted` 11名全件。WoSのグループヒットも全員0件）**

| 名前 | Scopusの現所属 |
|---|---|
| Yoshio Tazima | The University of Tokyo |
| Keiko Toi | ESPEC Corp. |
| Miura Shinichi | Kanazawa University |
| Yoshiaki Miyazaki | The Jikei University School of Medicine |
| Yoshio TAKAEDA | Mitsubishi Research Institute, Inc. |
| Claudia Brasse | Arrhenius Laboratory |
| Shozo Wada | Ashikaga University |
| Scott Gordon | QIMR Berghofer Medical Research Institute |
| İftihar KÖKSAL | Karadeniz Technical University |
| Mark Jakstis | GITAI USA Inc. |
| Noboru KOMATU | （Scopusに候補なし） |

トヨタとの関係がまったく見えない機関が並ぶ。**スイス法人エンティティの誤帰属は「豊田中研の混入」だけではなく、より広範な誤帰属を含む**。

**ありふれた名前による偽陽性の例（`ambiguous_common_name`）**

| 名前 | 層 | キャリア長 | Scopusの現所属 | WoS名前のみ | WoS本体 |
|---|---|---|---|---|---|
| S. Nakamura | known_noise | 74年 | University of California, Santa Barbara | **19,785** | 13 |
| H. Okamoto | current_swiss | 14年 | Jichi Medical University | 7,212 | 5 |
| T. Hattori | known_noise | 70年 | Chiba University School of Medicine | 6,228 | 15 |

`S. Nakamura` は典型例。イニシャル表記のためOpenAlex上で無数の別人が1つのIDに併合されており、WoSでも19,785件ヒットする。このうち13件がトヨタと共著しているが、それが当人である保証はまったくない。

## 7. クォータ実績

| API | 呼び出し数 | エラー | 応答時間中央値 |
|---|---|---|---|
| Scopus Author Search | 211 | 0 | 392 ms |
| WoS Starter `/documents` | 300 | 0 | 230 ms |

100名で511呼び出し（1名あたり約5.1）。WoSの制限は5 req/秒・5,000 req/日、Scopusは Author Search 5,000/週。
**9,429名全体に展開しても約48,000呼び出し**で、WoSなら10日、Scopusは週次クォータの観点から分割が必要だが、いずれも実行可能な範囲。

## 8. 本格展開に向けた提言

1. **Scopus を主、WoS を従とする。** WoSは新規発見に寄与しなかった（0件）ので、全件にWoSを回すのは費用対効果が悪い。Scopusで判定が付いた著者の**確信度を上げる用途**に絞り、`strong_support` を作るためだけに使うのが合理的。
2. **「名前のみヒット数」を必ず併記する。** これは同姓同名リスクの安価で強力な代理指標である。1著者1クエリで取れる。
3. **スイス法人エンティティ経由の著者（2,050名）を優先的に精査する。** 矛盾率が他層の約2倍。
4. **`no_evidence`（両DBに候補なし）をノイズと断定しない。** 現所属層でも各5名出ており、Scopus/WoS非収録の可能性がある。
5. **`known_noise` 層の抽出条件を見直す。** 異常キャリア長は「ありふれた名前によるID併合」を拾っているのであって、必ずしも「トヨタと無関係」を意味しない。実際 `Shinji Inagaki`（キャリア61年、Scopus現所属は産総研）はWoSでトヨタグループに133件ヒットしており、豊田中研の実在の研究者がID併合で汚れている例と考えられる。**「ノイズだから捨てる」ではなく「ID併合が起きているから分割が必要」と捉えるべき。**
6. **今後の検証には、公式サイトのスクレイピング結果（`combined_papers.csv` 919件）を正解ラベルとして使う。** 本パイロットは「外部DBとの一致」を見ているだけで真の正解ラベルがない。トヨタ自身が公表している著者リストと突き合わせれば、本手法の適合率・再現率を実測できる。

## 付録: 再現性について

2026-08-06 に同一シードで全件を再実行した結果、判定件数・裏付け率・同姓同名フラグ率・API呼び出し数がすべて 2026-08-03 と一致した（応答時間の中央値のみ差異）。本パイロットの結果は再現可能である。
