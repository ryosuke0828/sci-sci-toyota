# SciSciGPT の周辺文献調査

実施日: 2026-09-14
対象論文: Shao, Wang, Qian, Pan, Liu & Wang, "SciSciGPT: advancing human–AI collaboration in
the science of science", *Nature Computational Science* 6:301–315 (2026), `10.1038/s43588-025-00906-6`
出力データ: `data/derived/literature/sciscigpt_{refs,cocited,field,systems}.csv`

論文そのものの中身は[段階1-2 精読メモ](sciscigpt_review.md)にある。本メモはその**周辺**、
すなわち何を引き、誰に引かれ、同種のシステムが他に何があるかを調べたものである。

---

## 0. 結論（先に読む用）

1. **SciSciGPT は「科学計量に特化した」という点で珍しいが、手法としては新規ではない。**
   同じ設計（LLMに道具とデータを与えて自律的に作業させる）の先行システムが、化学・生物医学・
   材料科学に既にある。SciSciGPT の位置づけは「既知の設計を新しい領域に持ち込んだもの」である。
2. **この分野は評価が弱い。** SciSciGPT 自身が評価を "exploratory by nature" と断っており、
   被験者3名・評価者3名である。調べた範囲で、統計的に十分な比較を行っている論文は見つからなかった。
3. **AIの研究利用には、実証にもとづく批判が既に出ている。** とくに「AIは個人の成果を押し上げるが、
   科学全体の多様性を狭める」という指摘が複数の独立した研究から出ており、被引用も多い。
   先生への write-up ではこの点を落とせない。
4. **SciSciGPT はまだ引かれていない。** スナップショット（2026-06-26）時点で前方引用6件。
   出版から半年なので当然であり、評価が定まった文献ではない。

---

## 1. どう集めたか

OpenAlex スナップショット（5億1,037万件）から SciSciGPT の前方・後方引用を辿り、
不足分をタイトル検索で補った。API は指標取得ではなくタイトル取得のみに使用（計約130リクエスト）。

| 手段 | 件数 |
|---|---:|
| 後方引用（SciSciGPT が引いている） | 54 |
| 前方引用（SciSciGPT を引いている） | 6 |
| 共引用（前方引用6本が一緒に引いている） | 60（うち2本以上と共引用12） |
| 分野の地図づくりのための検索 | 38（重複除去後） |
| 名指しでの個別照会 | 9 |

**限界**: 前方引用が6件しかないため、引用のつながりだけでは分野の地図が描けない。
キーワード検索で補ったが、こちらは雑音が多い（「LLM」「AI」で引くと医学教育や
説明可能AIの総説が大量に混ざる）。したがって本メモの分野地図は**網羅ではなく代表例**である。

---

## 2. SciSciGPT が何の上に立っているか

後方引用54件の内訳を読むと、この論文は三つの流れの合流点にある。

**科学計量の古典**（自分たちの適用先）

Wuchty, Jones & Uzzi 2007「The Increasing Dominance of Teams」(8,859)、Fortunato et al. 2018
「Science of science」(1,448)、Wu, Wang & Evans 2019「Large teams develop and small teams disrupt」(1,057)、
Jones 2008「The Burden of Knowledge」(1,071)。いずれも我々が段階2で扱った文献と重なる。

**LLMの技術的な弱点**（自分たちが対処すべき問題）

Ji et al. 2022「Survey of Hallucination in NLG」(4,395)、Liu et al. 2024「Lost in the Middle:
How Language Models Use Long Contexts」(1,267)、Dahl et al. 2024「Large Legal Fictions:
Profiling Legal Hallucinations in LLMs」(266)。**幻覚と長文脈の扱いにくさを、設計上の前提として明示的に引いている。**

**成熟度モデルの原典**（自分たちの枠組みの根拠）

Paulk et al. 1993「Capability maturity model, version 1.1」(1,250) と
Humphrey 1988「Characterizing the software process」(663)。ソフトウェア工学の成熟度モデルを
そのままAIエージェントに移植している。したがって4段階の枠組みは新規の理論ではなく、
既存の枠組みの借用である。

**人間とAIの協働の実証**

Vaccaro, Almaatouq & Malone 2024「When combinations of humans and AI are useful: A systematic
review and meta-analysis」(484)、Sharma et al. 2023「Human–AI collaboration enables more
empathic conversations」(481)。

---

## 3. 同種のシステムの地図

「LLMに道具とデータを与え、自律的に研究作業をさせる」という設計は、SciSciGPT より前から
複数の領域で試されている。掲載誌と被引用を添えて代表例を挙げる。

| システム / 文献 | 年 | 掲載 | 被引用 | 領域 |
|---|---:|---|---:|---|
| Coscientist（Boiko et al.「Autonomous chemical research with LLMs」） | 2023 | **Nature** | 981 | 化学実験の自動化 |
| 自走実験室の総説（Abolhasani & Kumacheva） | 2023 | Nature Synthesis | 571 | 化学・材料 |
| 生物医学のAIエージェント（Gao et al.） | 2024 | Cell | 287 | 生物医学 |
| ChemCrow（Bran et al.） | 2023 | arXiv | 134 | 化学 |
| The AI Scientist（Lu et al.） | 2024 | arXiv | 114 | 論文生成まで含む全自動 |
| 化学合成の end-to-end 基盤 | 2024 | — | 112 | 化学合成 |
| **SciSciGPT** | **2026** | **Nat Comput Sci** | **6** | **科学計量** |
| 自律エージェントの総説（Wang et al.） | 2024 | Front Comput Sci | 1,566 | 分野横断の総説 |

**読み取れること**。

- **設計としての新規性は低い。** 司令塔＋専門役、道具の呼び出し、サンドボックスでのコード実行は、
  Coscientist（2023, Nature）や ChemCrow（2023）が既にやっている
- **領域としての新規性は高い。** 科学計量に持ち込んだのは SciSciGPT が最初とみてよい。
  この分野は SQL で大規模データベースを叩く作業が中心で、湿式実験を伴う化学とは作業の性質が違う
- **被引用の桁が違う。** Coscientist の981に対し SciSciGPT は6。出版時期の差（2023 対 2026）が
  大半だが、現時点で評価の定まった文献ではないことは事実である

---

## 4. この分野の評価の弱さ

SciSciGPT の評価は被験者3名・評価者3名で、著者自身が探索的と断っている（精読メモ3節）。
これは SciSciGPT に固有の問題ではなく、**分野全体の傾向**である。

判断の材料として引くべきなのは、個別システムの自己評価ではなく、**分野横断のメタ分析**のほうである。

Vaccaro, Almaatouq & Malone 2024（Nature Human Behaviour、被引用484）は、人間とAIの組み合わせが
有用かどうかを系統的にレビューし、メタ分析している。SciSciGPT 自身もこれを引いている。
個別の事例報告より、こちらのほうが主張の根拠として強い。

---

## 5. AIの研究利用に対する批判

**ここが今回の調査でいちばん重要な発見である。** AIを研究に使うことへの批判は、
印象論ではなく実証を伴って既に出ており、いずれも被引用が多い。

**Hao, Peng, Ke & Wang 2026「Artificial intelligence tools expand scientists' impact but
contract science's focus」**（被引用92、前方引用6本のうち3本が共引用）。
表題のとおり、AIを使う研究者は個人としての影響力を伸ばすが、**科学全体としては扱う対象が狭まる**
という主張である。SciSciGPT を引いた論文群の中で最も繰り返し共引用されている。

**Doshi & Hauser 2024「Generative AI enhances individual creativity but reduces the collective
diversity of novel content」**（Science Advances、被引用702）。
上と独立に、創作の領域で同じ構造の結果を報告している。個人の産出は良くなるが、
集団としての多様性は下がる。

**二つの独立した研究が同じ形の結論に達している。** 「個人の生産性は上がるが、全体は均質化する」。
AIの研究利用を論じる文書でこれに触れないのは不誠実である。

あわせて、研究評価そのものにLLMを使うことへの慎重論もある。
Thelwall ら（2025）が「Responsible Uses of Large Language Models for Research Evaluation」を
出しており、同じ著者群が「Estimating the quality of published medical research with ChatGPT」(23)、
「Research evaluation with ChatGPT: is it age, country, length, or field biased?」(22)で
偏りを実測している。**LLMによる評価には年代・国・長さ・分野の偏りがある**という報告である。

---

## 6. 我々の作業への含意

**1. SciSciGPT を使う予定はない。** これは道具であって、我々が必要としている指標や
データを提供するものではない。SciSciNet（同じグループのデータ）は使うが、それとは別物である。

**2. ただし設計から借りるものが一つある。** DatabaseSpecialist の `name_search`、すなわち
機関名や分野名の表記ゆれを埋め込みの類似度で寄せる仕組みである。我々は段階0-4 で所属文字列の
正規化を正規表現で行い、取りこぼしが22行残った（`src/normalize_affiliations.py`）。
同じ問題に対する別解として記録しておく。

**3. 成熟度モデルの第2段階「自己評価」は、我々の失敗の説明になる。**
実装を一次資料と突き合わせないまま段階3まで進んだ結果、値の定義が5点食い違っていた
（`scisci_foundation_review.md`）。反省の仕組みを持たない作業がどうなるかの実例である。

---

## 7. 先生への「AIの使い方の write-up」への材料

8月20日の打ち合わせで依頼のあった write-up に、本調査から使える論点を挙げる。

| 論点 | 根拠 |
|---|---|
| 領域専用に道具とデータを与えると、汎用LLMを直接使うより速く良い結果が出る | SciSciGPT の比較実験（ただし被験者3名、探索的） |
| ただし個別システムの自己評価は当てにしない | 分野全体が小規模評価。Vaccaro et al. のメタ分析を引くべき |
| **AIは個人の成果を伸ばすが、科学全体の多様性を狭める** | Hao et al. 2026（92）、Doshi & Hauser 2024（702）。**独立した2本が同じ結論** |
| 図の良し悪しの判定はまだAIには任せられない | SciSciGPT の VisualEval が4.17（他は4.98、5.00） |
| 研究評価にLLMを使うと年代・国・分野の偏りが入る | Thelwall ら 2025 の一連の実測 |
| 自己評価の仕組みを持たない作業は誤りに気づけない | 我々自身の失敗（実装の食い違い5点） |

**write-up の骨子としては、「使えるが、使い方を誤ると科学が均質化する」という両面を
実証を添えて示す形になる。** 推奨一辺倒にも否定一辺倒にもしない。

---

## 8. 残件と限界

- **前方引用が6件しかない。** SciSciGPT の評価は定まっていない。半年後に引き直せば像が変わる
- 分野地図はキーワード検索で補ったため**網羅ではない**。とくに arXiv 上の未査読のシステムは
  拾いきれていない（ChemCrow、AI Scientist は arXiv 版しか出ていない）
- Hao et al. 2026 と Doshi & Hauser 2024 は本調査では**題目と被引用しか見ていない**。
  write-up で引くなら本文を読む必要がある
