# shibayama-novelty のレビュー

林へ

リポジトリ見た。中身はよくできてるし、1つのリポジトリに解析ごとの区画を作る方針も賛成。
併合の前に直してほしいのが5つ、小さいのが3つ、相談が2つ。

- 各項目の下の枠は、AI（Claude Code とか）にそのまま貼ればいい指示文。
- 順番は 1・3・4・5 を今、2 は併合のとき。
- こっちはコードを読んで比べただけで、実行はしてない。

## 直してほしいこと

### 1. CONTRIBUTING.md の「確認用の出力」の決まりが消えてる

「確認用の出力は data/diagnostics/ に置いてコミットしない」って決まりが抜けてる。確認用の出力は、件数の要約とか、作業中に中身を確かめるだけのもののこと。
俺が渡した版が、この決まりを足す前の古いやつやったと思う、ごめん。俺のほうはこの決まりで作ってるから戻してほしい。

```
CONTRIBUTING.md に次の2つを足し、.gitignore に data/diagnostics/ を足してください。
- 「1. 構造」の図の derived の行の次に:
    diagnostics/<解析名>/<グループ>/  確認用の出力（件数の要約、照合できなかったものの一覧など）。コミットしない
- 「各工程はコミットされたファイルだけを読み……」の箇条の次に:
    - 後の工程が読まず、README.md の結果にも使わない確認用の出力は data/diagnostics/<解析名>/<グループ>/ に書く。このフォルダはコミットしない。ただし取り直せない記録（取得日時など）は data/derived/ に置いてコミットする。
そのあと、data/derived/shibayama_novelty/ の中で、後の工程も README も使っていないファイルを一覧にして見せてください。移すかどうかは私が決めます。
```

### 2. 論文・著者・参考文献の表の写しをやめる（併合のとき）

data/raw の3つの表は俺の出力の写し。併合すると同じ表が2つになって、片方だけ古くなる。実際、著者の表はもう古い（10/14 に外した Crossref の列が残ってる）。
併合のときに写しを消して、俺の表を直接読むようにしてほしい。林の計算が使う列は俺の表と一致してるから、結果の数字は変わらんはず。置き場所は併合の形が決まったら連絡する。

```
（併合のときに使う）data/raw の papers.csv・authorships.csv・paper_references.csv の写しをやめて、伊倉の表を直接読むようにしてください。伊倉の表の場所: <伊倉から聞いた場所>
- src/shibayama_novelty/clean_reference_titles.py の PAPERS_CSV・REFS_CSV・AUTHORS_CSV（30〜33行目）を上の場所に変える。RAW_DIR は変えない。
- data/raw の3つの写しを消し、README と data/README の3表の説明は、伊倉の README を参照する1文にする。
- reproduce_shibayama_novelty.ipynb を流す。JSON の inputs だけが変わるのは想定どおりなのでコミットしてよい。数字が変わったら、何がどう変わったかを報告して止まる。
```

### 3. 論文の表に足した2列を、取ってくる工程にする

上位10%・1%の2列を OpenAlex から取ったプログラムがリポジトリに無いから、他の人が同じ値を作れない。2 で写しを消すと、この2列も一緒に消える。
取ってくる工程を1つ足して、OpenAlex の返事を data/cache/ に保存しといてほしい。保存しとけば何回流しても同じ値になる。10/1 に取ったときの返事が残ってたら、それを保存ファイルにすれば今の結果のままいける。

```
data/raw/papers.csv の末尾2列（is_in_top_10_percent、is_in_top_1_percent）を、取得する工程に置き換えてください。
- src/shibayama_novelty/fetch_citation_percentiles.py を作り、work_id の論文について OpenAlex Works API の citation_normalized_percentile を50件ずつまとめて取る。
- 返答はそのまま data/cache/ に保存してコミットし、保存があれば問い合わせない。連絡先のメールアドレスは環境変数から読む（変数の名前は .env.example に書く）。
- 出力は data/derived/shibayama_novelty/ に paper_uid と2列の表で書き、取得日も記録する。validate_novelty_citations.py はここから読む。
- papers.csv から2列を消す。新しい工程は今の工程9の前に入れて番号をずらし、README の工程の表・reproduce_shibayama_novelty.ipynb・data/README.md を直す。
- 再現のノートブックを流し、結果が変わったら数字と理由を報告して止まる。
```

### 4. README に Scopus のことを書く

著者の表に Scopus のデータ（所属と著者番号）が入ってる。Scopus は規約で、見せていいのは阪大の人だけ。今の注意書きは「研究の関係者に限る」になってるから、阪大の人だけって書いてほしい。zip を人に渡すときも同じ。

```
README.md 冒頭の「共有の範囲」に次を書いてください。
- data/raw/authorships.csv に Scopus の列（affil_scopus、scopus_author_id）が入っている。
- Scopus の規約で、見せてよいのは大阪大学の構成員だけ。
- リポジトリを公開せず、データを阪大の外に持ち出さない。
```

### 5. AGENTS.md から個人の決まりを抜く

AGENTS.md は AI が最初に読む指示書で、併合したら俺の AI も読む。「push は林が行う」とかが入ってると、俺の作業まで林の担当やと AI が勘違いしかねない。
個人の決まりは自分のパソコンだけにある設定ファイルに移してほしい。Claude Code なら ~/.claude/CLAUDE.md、Codex なら ~/.codex/AGENTS.md。AGENTS.md には柴山の解析のデータとコードの決まりだけ残す。

```
AGENTS.md を共有用に直してください。
- 私個人の作業のしかた（「前提」の自己紹介、「やり取りと文章」、「段階を飛ばさない」、「git」、外部への申請・送信の確認）を ~/.claude/CLAUDE.md に移す。移す前に一覧を見せる。
- 残りは「## shibayama_novelty」の節にまとめる。「所属判定に inst_openalex を使わない」は、この解析の中だけの決まりだと分かる書き方にする。
- CLAUDE.md に @CONTRIBUTING.md の行を足す。
```

## 小さいこと

- RG65 と SimLex-999 は、配布していいかの記載が無い。決まりでは data/raw に置くのは再配布OKのものだけ。scispaCy みたいに工程の中で取ってくるか、このまま置くか、どっちがいいと思う？
- 「未来創成センター」は正式には「未来創生センター」。README と data/README の2か所。
- README の取得日の TODO は、2 をやれば片づく。俺の README に書いてあるから。

## 相談

- **README の言語。** 俺は英語、林は日本語。1つにまとめるからどっちかに揃えたい。どっちがいい？
- **Python とライブラリの版。** 俺は Python 3.14、林は 3.13 で、numpy と pandas の版も違う。requirements.txt は共有やから揃えたい。3.13 にしたのは spaCy の都合？

わからんとこあったら聞いて。

伊倉
