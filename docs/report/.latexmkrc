# ltjsarticle は LuaLaTeX 専用。pdflatex では組版できないためエンジンを固定する。
# エディタ（LaTeX Workshop 等）が latexmk を呼ぶ場合もこの設定が効く。
$pdf_mode = 4;          # 4 = lualatex
$lualatex = 'lualatex -interaction=nonstopmode -synctex=1 %O %S';
$max_repeat = 5;        # 相互参照（表1）の解決に複数回必要
$clean_ext = 'fls fdb_latexmk synctex.gz';
