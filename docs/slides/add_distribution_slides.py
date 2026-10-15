"""進捗報告資料（toyota_novelty_progress.pptx）に、指標の分布の図のページを差し込む。

資料7・8・11ページの表の直後に、同じ表の各マスを順位の分布にした図（図1〜3）を1枚ずつ入れ、
最後に補足（値そのものの分布）を1枚足す。既存のページは変えない。ただしページ番号は画面上の文字なので、
差し込み後に全ページを通し番号に振り直す（もとの資料では非表示にしたページの番号が残っていて、10〜13枚目が 13〜16 になっていた）。

新しいページは、直前の表のページの見出し・副題・ページ番号の文字枠を複製して作る（体裁を揃えるため）。

実行: ~/.venvs/scisci-rir/bin/python docs/slides/add_distribution_slides.py <入力 pptx> <出力 pptx>
"""
from __future__ import annotations

import copy
import sys
from pathlib import Path

from pptx import Presentation
from pptx.util import Inches

ROOT = Path(__file__).resolve().parents[2]
FIG = ROOT / "figures" / "novelty_distributions"

# 副題は1行に収める（図の中に凡例の行があるので、副題では繰り返さない）
SUB = "前ページの表の各マスを、中央値の代わりに順位の分布にしたもの（太字は前ページの表の中央値）"
# (差し込む位置 = この番号のページの直後, 見出し, 副題, 図のファイル)
NEW_SLIDES = [
    (7, "2. 一般論文との比較（トヨタ系列全体）：順位の分布", SUB, "fig_slide7_rank_by_condition.png"),
    (8, "2. 一般論文との比較（組織別）：順位の分布", SUB, "fig_slide8_rank_by_org.png"),
    (11, "補足：チーム規模別の破壊性：順位の分布", SUB, "fig_slide11_disruption_by_team.png"),
    (None, "補足：値そのものの分布",
     "順位にする前の SciSciNet の値を、トヨタの論文（塗り）と同じ分野・年の一般論文（線、分野・年の構成をトヨタに合わせて重み付け）で重ねたもの",
     "fig_supp_values.png"),
]
# 図を置く範囲（インチ）。副題の下から、ページ番号の上まで
PIC_TOP, PIC_BOTTOM, PIC_LEFT, PIC_RIGHT = 1.55, 6.95, 0.6, 12.73


def set_text(shape, text: str) -> None:
    """文字枠の1つ目の段落・1つ目の run だけ残して文字を入れ替える（フォント等の書式は引き継ぐ）。"""
    tf = shape.text_frame
    for p in list(tf.paragraphs[1:]):
        p._p.getparent().remove(p._p)
    p = tf.paragraphs[0]
    for r in list(p.runs[1:]):
        r._r.getparent().remove(r._r)
    p.runs[0].text = text


def find_box(slide, text_startswith: str | None = None, name: str | None = None):
    for sh in slide.shapes:
        if name and sh.name == name:
            return sh
        if text_startswith and sh.has_text_frame and sh.text_frame.text.startswith(text_startswith):
            return sh
    raise KeyError(name or text_startswith)


def add_figure_slide(prs, src_slide, title: str, subtitle: str, image: Path):
    """src_slide の見出し・副題・ページ番号の文字枠を複製した新しいページを末尾に作り、図を置く。"""
    new = prs.slides.add_slide(src_slide.slide_layout)
    for name in ("Text 0", "Text 1", "Text 2"):  # 見出し、副題、ページ番号
        el = copy.deepcopy(find_box(src_slide, name=name)._element)
        new.shapes._spTree.append(el)
    set_text(find_box(new, name="Text 0"), title)
    set_text(find_box(new, name="Text 1"), subtitle)
    # 図は縦横比を保ち、範囲の中で最大にして中央に置く
    pic = new.shapes.add_picture(str(image), Inches(PIC_LEFT), Inches(PIC_TOP))
    box_w, box_h = Inches(PIC_RIGHT - PIC_LEFT), Inches(PIC_BOTTOM - PIC_TOP)
    scale = min(box_w / pic.width, box_h / pic.height)
    pic.width, pic.height = int(pic.width * scale), int(pic.height * scale)
    pic.left = int(Inches(PIC_LEFT) + (box_w - pic.width) / 2)
    pic.top = int(Inches(PIC_TOP))
    return new


def move_slide(prs, slide, to_index: int) -> None:
    """ページの並びの中で slide を to_index（0始まり）の位置に動かす。"""
    lst = prs.slides._sldIdLst
    el = next(e for e in lst if e.rId == prs.part.relate_to(slide.part, prs.part.rels[e.rId].reltype))
    lst.remove(el)
    lst.insert(to_index, el)


def main(src: Path, dst: Path) -> None:
    prs = Presentation(str(src))
    n_before = len(prs.slides)
    inserted = 0
    for after, title, subtitle, fname in NEW_SLIDES:
        if after is None:
            src_slide = prs.slides[n_before + inserted - 1]  # 直前のページ（最後の補足）の体裁を使う
            add_figure_slide(prs, src_slide, title, subtitle, FIG / fname)
        else:
            pos = after + inserted  # それまでに差し込んだ分だけ後ろにずれる
            src_slide = prs.slides[pos - 1]
            new = add_figure_slide(prs, src_slide, title, subtitle, FIG / fname)
            move_slide(prs, new, pos)
        inserted += 1
    # ページ番号を通し番号に振り直す
    for i, s in enumerate(prs.slides, 1):
        set_text(find_box(s, name="Text 2"), str(i))
    prs.save(str(dst))
    print(f"{n_before} → {len(prs.slides)} ページ: {dst}")


if __name__ == "__main__":
    main(Path(sys.argv[1]), Path(sys.argv[2]))
