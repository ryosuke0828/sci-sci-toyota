# 報告資料

## 組版方法

**必ず LuaLaTeX を使うこと。** `ltjsarticle` は LuaLaTeX 専用で、pdflatex や platex では
`luatexja-core Error: This package requires Lua(HB)(La)TeX` で失敗する。

```
cd docs/report
latexmk report_2026-08-17.tex
```

`.latexmkrc` で `$pdf_mode = 4`（lualatex）に固定してある。`.tex` 先頭の
`% !TEX program = lualatex` により、LaTeX Workshop・TeXShop・TeXstudio からも同じエンジンが選ばれる。

## プリアンブルの方針

**内容を削ってページ数を合わせる。組版で圧縮しない。**

過去に2ページへ押し込むため `titlesec` の見出し詰め・`\linespread{0.95}`・余白17mm・
負の `\vspace` を積み重ねた結果、可読性が落ちたうえ、`titlesec` が `ltjsarticle` の
`\paragraph` と競合して**見出しが本文の後ろに出る不具合**まで起こした。
現在のプリアンブルは `geometry` と `booktabs`、および `\paragraph` の
見出し記号（■）を消す1行のみ。ここに組版上の細工を足さないこと。

ページ数は目安であり、内容の正確さを優先する。

## うまくいかないとき

- **`表??` のまま残る** … pdflatex が混ざって `.aux` が壊れている。`latexmk -C` で全消しして組版し直す。
- **`■` が見出しに出る** … `\renewcommand{\jsParagraphMark}{}` が効いていない。
- **`■` が本文に混ざる／`\paragraph` の見出しが本文の後ろに出る** … `titlesec` が読み込まれている。外すこと。
- **エラーの見落とし** … `-interaction=nonstopmode` は組版を止めない。ページ数だけ見ても破損に気づけないので、`.log` の `Error` と `Warning` を必ず確認する。
