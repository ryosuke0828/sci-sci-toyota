# 報告資料

## 組版方法

**必ず LuaLaTeX を使うこと。** `ltjsarticle` は LuaLaTeX 専用で、pdflatex や platex では
`luatexja-core Error: This package requires Lua(HB)(La)TeX` で失敗する。

```
cd docs/report
latexmk report_2026-08-17.tex
```

`.latexmkrc` で `$pdf_mode = 4`（lualatex）に固定してあるので、latexmk を素で呼べばよい。
`.tex` の先頭にも `% !TEX program = lualatex` を置いてあるため、
LaTeX Workshop・TeXShop・TeXstudio から開いた場合もエンジンが選ばれる。

手動で回す場合:

```
lualatex -interaction=nonstopmode report_2026-08-17.tex
```

相互参照（表1）を解決するには2回以上通す必要がある。

## うまくいかないとき

- **`表??` のまま残る** … pdflatex が混ざって `.aux` が壊れている。
  `latexmk -C` で全消ししてから組版し直す。
- **`■` が本文に混ざる／`\paragraph` の見出しが本文の後ろに出る** …
  `titlesec` と `ltjsarticle` の競合。プリアンブルの `\titleformat{\paragraph}[runin]` が
  効いているか確認する。この定義を消すと再発する。
- **エラーが出ていないか確認する** … `-interaction=nonstopmode` は組版を止めないため、
  ページ数だけ見ても破損に気づけない。`.log` の `Error` と `Warning` を必ず見ること。
