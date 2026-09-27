// 進捗報告資料（2026年9月）を生成する。16:9、白地・紺の見出し帯・ページ番号。
// 話の流れ: 要旨 → 材料と道具 → ① SciSciNet の値の検算 → ② 世の中の論文との比較 → ③ 要因の仮説検証 → 相談
// 数字はすべて make_numbers_progress_2026-09.py が書き出す JSON から読む。発表者ノートに話す内容を入れてある。
// 実行: NODE_PATH=<pptxgenjs のある node_modules> node build_progress_2026-09.js [出力先.pptx]
const path = require('path');
const pptxgen = require('pptxgenjs');
const N = require('./numbers_progress_2026-09.json');
const OUT = process.argv[2] || path.join(__dirname, 'toyota_novelty_progress.pptx');
const IMG = path.join(__dirname, 'fig_verification_scatter.png');
const pres = new pptxgen();
pres.layout = 'LAYOUT_16x9';            // 10 x 5.625 in
const W = 10;
const F = 'Meiryo';
const NAVY = '1F3864', GRAY = '7F7F7F', LINE = 'A6A6A6', BLACK = '000000';
const TINT = 'EEF1F7', DIM = '8EA3C4';
const FOOT = 'トヨタ関連企業の論文の新規性分析　進捗報告　2026年9月';
let page = 0;

// 文字に日本語の指定を付ける。付けないと英語扱いになり、句読点や括弧が行頭に来る改行を PowerPoint が許してしまう
function jp(s) {
  const addText = s.addText.bind(s), addTable = s.addTable.bind(s);
  s.addText = (t, o) => addText(t, Object.assign({ lang: 'ja-JP' }, o));
  s.addTable = (rows, o) => addTable(rows, Object.assign({ lang: 'ja-JP' }, o));
  return s;
}

// 見出し帯つきのスライド。step（1〜3）を渡すと、右上に ①②③ のどこを話しているかを示す
function slide(title, step) {
  page += 1;
  const s = jp(pres.addSlide());
  s.background = { color: 'FFFFFF' };
  s.addShape(pres.shapes.RECTANGLE, { x: 0, y: 0, w: W, h: 0.5, fill: { color: NAVY }, line: { color: NAVY } });
  s.addText(title, { x: 0.3, y: 0, w: step ? 7.5 : 8.8, h: 0.5, fontFace: F, fontSize: 18, bold: true, color: 'FFFFFF', valign: 'middle', margin: 0, isTextBox: true });
  if (step) {
    [1, 2, 3].forEach((n, i) => {
      const on = n === step, x = 8.0 + i * 0.36;
      s.addShape(pres.shapes.OVAL, { x, y: 0.11, w: 0.28, h: 0.28, fill: { color: on ? 'FFFFFF' : NAVY }, line: { color: on ? 'FFFFFF' : DIM, width: 0.75 } });
      s.addText(String(n), { x, y: 0.11, w: 0.28, h: 0.28, fontFace: F, fontSize: 10, bold: true, color: on ? NAVY : DIM, align: 'center', valign: 'middle', margin: 0, isTextBox: true });
    });
  }
  s.addText(String(page), { x: 9.2, y: 0, w: 0.55, h: 0.5, fontFace: F, fontSize: 11, color: 'FFFFFF', align: 'right', valign: 'middle', margin: 0, isTextBox: true });
  s.addText(FOOT, { x: 4.5, y: 5.35, w: 5.2, h: 0.2, fontFace: F, fontSize: 7, color: GRAY, align: 'right', margin: 0, isTextBox: true });
  return s;
}
function label(s, text, y, x = 0.5, w = 9) {
  s.addText(text, { x, y, w, h: 0.28, fontFace: F, fontSize: 12, bold: true, margin: 0, isTextBox: true });
}
function note(s, text, y, x = 0.5, w = 9, fs = 12) {
  s.addText(text, { x, y, w, h: 0.3, fontFace: F, fontSize: fs, color: BLACK, margin: 0, valign: 'middle', isTextBox: true });
}
function bullets(s, items, opt) {
  const arr = items.map((t, i) => {
    const o = typeof t === 'string' ? { text: t } : t;
    const bullet = o.sub ? { indent: 16 } : (opt.numbered ? { type: 'number' } : true);
    return { text: o.text, options: { bullet, indentLevel: o.sub ? 1 : 0, bold: !!o.b,
      fontSize: o.sub ? (opt.fs - 2) : opt.fs, breakLine: i < items.length - 1, paraSpaceAfter: opt.sp ?? 5 } };
  });
  s.addText(arr, Object.assign({ fontFace: F, color: BLACK, valign: 'top', margin: 0.05, isTextBox: true }, opt, { fs: undefined, sp: undefined, numbered: undefined }));
}
function table(s, rows, opt) {
  const hdr = rows[0].map(c => ({ text: c, options: { bold: true, fill: { color: 'F2F2F2' }, align: 'center' } }));
  const body = rows.slice(1).map(r => r.map((c, j) => (typeof c === 'object' ? c : { text: String(c), options: { align: j === 0 ? 'left' : 'center' } })));
  s.addTable([hdr, ...body], Object.assign({ fontFace: F, fontSize: 12, color: BLACK, border: { type: 'solid', pt: 0.75, color: LINE }, valign: 'middle', margin: 0.04 }, opt));
}
// 紺の丸に番号（①②③の見出しに使う）
function badge(s, n, x, y, d = 0.36) {
  s.addShape(pres.shapes.OVAL, { x, y, w: d, h: d, fill: { color: NAVY }, line: { color: NAVY } });
  s.addText(String(n), { x, y, w: d, h: d, fontFace: F, fontSize: 14, bold: true, color: 'FFFFFF', align: 'center', valign: 'middle', margin: 0, isTextBox: true });
}
const shortOrg = o => ({ 'AISIN IMRA(日本・aisin.com)': 'AISIN IMRA（日本）', 'AISIN IMRA(米国・imra.com)': 'AISIN IMRA（米国）',
  'トヨタ自動車未来創成センター': '未来創成センター', '豊田中央研究所': '豊田中央研究所' }[o] || o);
const left = t => ({ text: t, options: { align: 'left' } });
const strong = (t, j = 1) => ({ text: String(t), options: { bold: true, align: j ? 'center' : 'left' } });
const hl = t => ({ text: String(t), options: { bold: true, color: NAVY, align: 'center' } });
const f1 = v => Number(v).toFixed(1);
const p2 = v => (v < 0.01 ? v.toFixed(3) : v.toFixed(2));
const man = n => `${Math.floor(n / 10000)}万${Math.round((n % 10000) / 1000)}千`;   // 432000 → 43万2千
const S = N.stages, A = N.ana, D = A.descriptive_only;
const [spLo, spHi] = [N.ver[0].sp, N.ver[1].sp].sort((a, b) => a - b).map(v => v.toFixed(2));
const orgBy = name => N.org_res.find(o => o.org === name);
const novRange = names => { const v = names.map(n => orgBy(n).nov); return `${Math.round(Math.min(...v))}〜${Math.round(Math.max(...v))}`; };
const HIGH = ['豊田中央研究所', 'トヨタ自動車未来創成センター'], LOW = ['AISIN IMRA(日本・aisin.com)', 'AISIN IMRA(米国・imra.com)'];

// ---------- 1. 表紙 ----------
{
  page += 1;
  const s = jp(pres.addSlide()); s.background = { color: 'FFFFFF' };
  s.addText('トヨタ関連企業の論文の新規性分析', { x: 0.5, y: 1.35, w: 9, h: 0.8, fontFace: F, fontSize: 30, bold: true, align: 'center', isTextBox: true });
  s.addText('― SciSciNet を用いた検証 ―', { x: 0.5, y: 2.15, w: 9, h: 0.5, fontFace: F, fontSize: 18, align: 'center', isTextBox: true });
  s.addText('進捗報告', { x: 0.5, y: 2.75, w: 9, h: 0.4, fontFace: F, fontSize: 15, align: 'center', isTextBox: true });
  s.addText('2026年9月\n大阪大学大学院 工学研究科　田中研究室\n伊倉 涼介', { x: 0.5, y: 3.6, w: 9, h: 1.0, fontFace: F, fontSize: 13, align: 'center', isTextBox: true });
  s.addText('1', { x: 9.2, y: 0.12, w: 0.55, h: 0.3, fontFace: F, fontSize: 11, align: 'right', margin: 0, isTextBox: true });
  s.addNotes('トヨタ関連企業の論文の新規性について、前回以降の進捗をご報告します。');
}

// ---------- 2. 今回の報告（要旨） ----------
{
  const s = slide('今回の報告');
  s.addText([
    { text: '問い　', options: { bold: true, color: NAVY } },
    { text: 'どのような条件で新しい研究が生まれるか。どのようなチームや共同が良い成果につながるか' },
  ], { x: 0.5, y: 0.66, w: 9, h: 0.36, fontFace: F, fontSize: 13, color: BLACK, margin: 0, valign: 'middle', isTextBox: true });
  s.addShape(pres.shapes.RECTANGLE, { x: 0.5, y: 1.1, w: 9, h: 0.46, fill: { color: TINT }, line: { color: TINT } });
  s.addText([
    { text: '材料　', options: { bold: true, color: NAVY } },
    { text: `トヨタ関連4組織の公式サイトから、自前で集めた論文 ${N.tot.site}件` },
  ], { x: 0.65, y: 1.1, w: 8.7, h: 0.46, fontFace: F, fontSize: 13, color: BLACK, margin: 0, valign: 'middle', isTextBox: true });
  // 枠が狭く、PowerPoint は日本語を単語の途中でも折り返すので、行の切れ目を指定する
  const cards = [
    { tag: 'SciSciNet の値の検算', h: 'SciSciNet の新規性の値は\n信頼できるか', did: ['同じ指標を自前でも計算し、', '公開値と突き合わせた'],
      res: ['並び順がよく一致した', `（順位相関 ${spLo}〜${spHi}）。`, '以後は公開値を使う'] },
    { tag: '世の中の論文との比較', h: 'トヨタの論文は、\n世の中と比べてどの程度か', did: ['同じ分野・同じ年の一般論文', `${man(N.n_base)}件と比べた`],
      res: ['条件を揃えると、', '新規性・破壊性・被引用とも', '世の中の真ん中。', '組織による差はある'] },
    { tag: '要因の仮説検証', h: '何が新規性を左右するか', did: ['先行研究にもとづき、', 'チームの大きさと国際共同の', '効果を調べた'],
      res: ['どちらも関係は見えなかった。', 'ただし件数が足りず、', '確かめきれていない'] },
  ];
  const cw = 2.7, gap = 0.45, y0 = 1.7, ch = 3.2;
  cards.forEach((c, i) => {
    const x = 0.5 + i * (cw + gap);
    s.addShape(pres.shapes.RECTANGLE, { x, y: y0, w: cw, h: ch, fill: { color: 'FFFFFF' }, line: { color: LINE, width: 0.75 } });
    badge(s, i + 1, x + 0.15, y0 + 0.15, 0.34);
    s.addText(c.tag, { x: x + 0.58, y: y0 + 0.15, w: cw - 0.7, h: 0.34, fontFace: F, fontSize: 11, bold: true, color: GRAY, valign: 'middle', margin: 0, isTextBox: true });
    s.addText(c.h, { x: x + 0.15, y: y0 + 0.58, w: cw - 0.3, h: 0.6, fontFace: F, fontSize: 13, bold: true, color: NAVY, valign: 'top', margin: 0, isTextBox: true });
    const runs = [{ text: 'やったこと', options: { fontSize: 10, color: GRAY, bold: true, breakLine: true } }];
    c.did.forEach((t, k) => runs.push({ text: t, options: { fontSize: 12, breakLine: true, paraSpaceAfter: k === c.did.length - 1 ? 9 : 0 } }));
    runs.push({ text: '結果', options: { fontSize: 10, color: GRAY, bold: true, breakLine: true } });
    c.res.forEach((t, k) => runs.push({ text: t, options: { fontSize: 12, bold: true, breakLine: k < c.res.length - 1 } }));
    s.addText(runs, { x: x + 0.15, y: y0 + 1.25, w: cw - 0.3, h: ch - 1.35, fontFace: F, color: BLACK, valign: 'top', margin: 0, isTextBox: true });
    if (i < cards.length - 1) s.addText('→', { x: x + cw, y: y0, w: gap, h: ch, fontFace: F, fontSize: 20, color: GRAY, align: 'center', valign: 'middle', margin: 0, isTextBox: true });
  });
  s.addText('最後に、次の段階（hot streak）の進め方をご相談させてください', { x: 0.5, y: 5.0, w: 9, h: 0.26, fontFace: F, fontSize: 11, color: GRAY, margin: 0, isTextBox: true });
  s.addNotes([
    '今回の報告の要旨を先に申し上げます。',
    `材料は、トヨタ関連4組織の公式サイトから自前で集めた論文${N.tot.site}件です。これを使って、三つのことを行いました。`,
    `一つめに、SciSciNet が公開している新規性の値が信頼できるかを確かめました。同じ指標を自前でも計算して突き合わせたところ、並び順がよく一致しましたので、以後は SciSciNet の値を使っています。`,
    '二つめに、その値を使って、トヨタの論文の新規性や破壊性が、世の中の論文と比べてどの程度かを測りました。条件を揃えると、どれも世の中の真ん中でした。ただし組織による差がございます。',
    '三つめに、新規性を左右する要因について、先行研究にもとづく仮説を検証しました。チームの大きさと国際共同を調べましたが、関係は見えませんでした。ただ、件数が足りず、確かめきれていないというのが正確なところです。',
    '最後に、次の段階である hot streak の進め方をご相談させてください。',
  ].join('\n\n'));
}

// ---------- 3. 自前のデータと SciSciNet の役割分担 ----------
{
  const s = slide('自前のデータと SciSciNet の役割分担');
  label(s, '役割分担', 0.7);
  table(s, [
    ['項目', '担当'],
    ['トヨタの論文の特定・組織の区別', '自前（公式サイト4組織から構築）'],
    ['トヨタの論文の指標（新規性・破壊性・被引用）', 'SciSciNet の公開値'],
    ['比較相手（同じ分野・同じ年の一般論文）の指標', 'SciSciNet の公開値'],
  ], { x: 0.5, y: 1.0, w: 9, colW: [4.9, 4.1], rowH: 0.4, fontSize: 13 });
  label(s, 'SciSciNet の値を使う理由と、確かめる理由', 2.85);
  bullets(s, [
    '世の中の論文と比べるには、比較相手にも同じ出どころの値が要る',
    'SciSciNet は約2.5億本の論文について、新規性・破壊性などの値を公開している',
    'ただし計算の細かい条件は公開されていない → 同じ指標を自前でも計算して確かめた（①）',
  ], { x: 0.5, y: 3.15, w: 9, h: 1.55, fs: 14, sp: 8 });
  s.addText('前回（9月8日）は自前の計算を主に使う予定と申し上げましたが、上の理由から公開値を主に使う形に変えました',
    { x: 0.5, y: 4.85, w: 9, h: 0.3, fontFace: F, fontSize: 10.5, color: GRAY, margin: 0, valign: 'middle', isTextBox: true });
  s.addNotes([
    '役割分担はこのとおりです。どれがトヨタの論文か、どの組織の論文かは、公式サイトから自前で特定しました。',
    '一方、新規性や破壊性の値と、比べる相手になる一般の論文の値は、SciSciNet の公開値を使っています。世の中と比べるには、比べる相手にも同じ出どころの値が要るためです。SciSciNet は約2.5億本の論文について、これらの値を公開しています。',
    'ただ、SciSciNet は計算の細かい条件を公開していません。そこで、同じ指標を自前でも計算して確かめました。これが一つめの作業です。',
    'なお前回は、自前の計算を主に使うと申し上げましたが、いま申し上げた理由から、公開値を主に使う形に変えております。',
  ].join('\n\n'));
}

// ---------- 4. 材料：自前で集めたトヨタの論文 ----------
{
  const s = slide('材料：自前で集めたトヨタの論文');
  label(s, '論文数（件）', 0.7);
  const rows = [['組織', 'サイト掲載', 'OpenAlex で特定', 'SciSciNet に値あり\n（2000年以降）', '新規性の値あり']];
  for (const o of N.org) rows.push([shortOrg(o.org), o.site, o.matched, o.ss, o.nov]);
  const t = N.tot;
  rows.push(['合計', t.site, t.matched, t.ss, t.nov].map((v, j) => strong(v, j)));
  table(s, rows, { x: 0.5, y: 1.0, w: 9, colW: [2.6, 1.5, 1.6, 1.8, 1.5], rowH: [0.55, 0.36, 0.36, 0.36, 0.36, 0.36], fontSize: 13 });
  bullets(s, [
    '組織は公式サイトの掲載で特定した（OpenAlex の所属情報は誤りが多く、トヨタ所属の裏付けが取れるのは約半数）',
    '2025年以降の論文は SciSciNet に収録されておらず、対象外',
    '未来創成センターと AISIN IMRA（米国）は、新規性の値が取れたのがサイト掲載の半分以下',
  ], { x: 0.5, y: 3.55, w: 9, h: 1.6, fs: 13, sp: 7 });
  s.addNotes([
    `材料はこちらです。公式サイトに載っていた${t.site}件のうち、OpenAlex で特定できたのが${t.matched}件です。`,
    `対象は2000年以降に絞っておりまして、SciSciNet に値があるのが${t.ss}件、新規性の値まであるのが${t.nov}件です。SciSciNet は2024年までの論文しか収録していないので、2025年以降の論文は入っておりません。`,
    'どの組織の論文かは、OpenAlex の所属情報ではなく、公式サイトに載っていたかどうかで決めています。OpenAlex の所属情報は誤りが多く、トヨタ所属の裏付けが取れるのは約半数だったためです。',
    '未来創成センターと AISIN IMRA の米国法人は、値が取れたのがサイトに載っている論文の半分以下ですので、この二つの組織の結果は、件数が少ない点をご承知おきください。',
  ].join('\n\n'));
}

// ---------- 5. 指標 ----------
{
  const s = slide('指標：新規性（Uzzi 2013）と破壊性（Wu 2019）');
  const steps = ['論文の\n参考文献', '載っている\n雑誌の組を\nすべて作る', '各組の珍しさ\n（z値）を計算', '論文ごとに\n集約'];
  const bw = 1.85, gap = 0.45, x0 = 0.55, y0 = 0.8, bh = 0.95;
  steps.forEach((t, i) => {
    const x = x0 + i * (bw + gap);
    s.addShape(pres.shapes.RECTANGLE, { x, y: y0, w: bw, h: bh, fill: { color: 'FFFFFF' }, line: { color: BLACK, width: 1 } });
    s.addText(t, { x, y: y0, w: bw, h: bh, fontFace: F, fontSize: 12, align: 'center', valign: 'middle', margin: 0.03, isTextBox: true });
    if (i < steps.length - 1) s.addText('→', { x: x + bw, y: y0, w: gap, h: bh, fontFace: F, fontSize: 20, align: 'center', valign: 'middle', margin: 0, isTextBox: true });
  });
  bullets(s, [
    '珍しさ（z値）：その雑誌の組が、同じ年の全論文の中でどれだけ一緒に引用されにくいか',
    { text: '新規性として、論文ごとに2つの値を取る', b: true },
    { text: '定石らしさ：z値の中央値（高いほど、よくある組み合わせが中心）', sub: true },
    { text: '非慣習性：z値の下位10%（高いほど、珍しい組み合わせを含むように向きを揃えた）', sub: true },
    '破壊性（Wu et al. 2019）：後に続く論文が、その論文の参考文献まで引用しなくなるほど高い（既存の流れを断ち切った度合い）',
    '10年被引用：出版から10年間に引用された回数',
  ], { x: 0.5, y: 1.95, w: 9, h: 3.25, fs: 13, sp: 6 });
  s.addNotes([
    '新規性は、Uzzi らの2013年の方法で測ります。論文の参考文献に載っている雑誌を二つずつ組にして、その組が世の中でどれくらい一緒に引用されにくいかを求めます。',
    '論文ごとに二つの値を取ります。定石らしさは、よくある組み合わせがどれだけ中心にあるか。非慣習性は、珍しい組み合わせをどれだけ含むかです。非慣習性は、読み違えないよう、高いほど珍しいという向きに揃えてあります。',
    '破壊性は Wu らの2019年の指標です。後に続く論文が、その論文の参考文献まで引かなくなるほど高くなります。既存の流れを断ち切った度合いです。あわせて、影響力の目安として10年間の被引用数も見ています。',
  ].join('\n\n'));
}

// ---------- 6. ① 検算 ----------
{
  const s = slide('① SciSciNet の新規性の値は信頼できるか', 1);
  note(s, `同じ指標を自前でも計算し、両方に値がある ${N.ver_n} 件で比較（1点が1論文、破線は同じ値）`, 0.6);
  s.addImage({ path: IMG, x: 0.5, y: 0.95, w: 5.6, h: 5.6 * 3.9 / 9.0 });
  const trim = N.ver.find(v => v.lab === 'z値の下位10%');
  s.addText(`※z値の下位10%の相関係数が低いのは、公開値に極端に大きい値が少数あるため\n（上下1%を除くと ${trim.pe_trim.toFixed(2)}）`,
    { x: 0.5, y: 3.42, w: 5.6, h: 0.4, fontFace: F, fontSize: 9.5, color: GRAY, margin: 0, valign: 'top', isTextBox: true });
  const rows = [['', '順位相関', '相関係数']];
  for (const v of N.ver) rows.push([v.lab, v.sp.toFixed(2), v.pe.toFixed(2)]);
  table(s, rows, { x: 6.35, y: 1.0, w: 3.25, colW: [1.45, 0.9, 0.9], rowH: 0.3, fontSize: 11 });
  label(s, '中央値', 2.35, 6.35, 3.25);
  const med = [['', '自前', '公開']];
  for (const v of N.ver) med.push([v.lab, String(v.med_own), String(v.med_ss)]);
  table(s, med, { x: 6.35, y: 2.65, w: 3.25, colW: [1.45, 0.9, 0.9], rowH: 0.3, fontSize: 11 });
  s.addShape(pres.shapes.RECTANGLE, { x: 0.5, y: 4.02, w: 9, h: 0.95, fill: { color: TINT }, line: { color: TINT } });
  s.addText([
    { text: '並び順はよく一致した → 以後の分析は SciSciNet の値で行う', options: { bold: true, breakLine: true, paraSpaceAfter: 4 } },
    { text: '値の大きさは揃わない（計算の細かい条件が公開されていないため）→ 自前の値とは混ぜない' },
  ], { x: 0.7, y: 4.02, w: 8.6, h: 0.95, fontFace: F, fontSize: 13, color: BLACK, valign: 'middle', margin: 0, isTextBox: true });
  const conv = N.ver.find(v => v.lab === '定石らしさ');
  s.addNotes([
    `一つめの作業です。SciSciNet は計算の細かい条件を公開していませんので、同じ指標を自前でも計算し、両方に値がある${N.ver_n}件で突き合わせました。図の横軸が自前の値、縦軸が公開値です。`,
    `並び順がどれだけ一致するかを表す順位相関は、定石らしさで${N.ver[0].sp.toFixed(2)}、下位10%で${N.ver[1].sp.toFixed(2)}でした。並び順はよく一致しています。`,
    `一方、値の大きさは揃いません。たとえば定石らしさの中央値は、自前が${conv.med_own}、公開値が${conv.med_ss}です。論文の掲載誌の割り当て方など、公開されていない条件が違うためと考えています。`,
    `なお、下位10%の相関係数が${trim.pe.toFixed(2)}と低いのは、公開値に極端に大きい値が少数あるためで、上下1%を除くと${trim.pe_trim.toFixed(2)}になります。`,
    '以上から、以後の分析は SciSciNet の値で行い、自前の値とは混ぜないことにしました。',
  ].join('\n\n'));
}

// ---------- 7. ② 世の中の論文との比較 ----------
{
  const s = slide('② トヨタの論文は、世の中の論文と比べてどの程度か', 2);
  note(s, `同じ分野・同じ年の一般論文（${man(N.n_base)}件）の中での順位の中央値。50が真ん中`, 0.6);
  table(s, [
    ['揃えた条件', '非慣習性', '定石らしさ', '破壊性', '10年被引用'],
    ['分野・年のみ', f1(S.fy.nov), f1(S.fy.conv), hl(f1(S.fy.dis)), hl(f1(S.fy.c10))],
    ['分野・年＋参考文献の数', f1(S.ref.nov), f1(S.ref.conv), f1(S.ref.dis), f1(S.ref.c10)],
    ['分野・年＋チームの大きさ', f1(S.team.nov), f1(S.team.conv), f1(S.team.dis), f1(S.team.c10)],
    ['分野・年＋両方', f1(S.both.nov), f1(S.both.conv), f1(S.both.dis), f1(S.both.c10)],
  ], { x: 0.5, y: 0.98, w: 9, colW: [3.0, 1.5, 1.5, 1.5, 1.5], rowH: 0.34, fontSize: 12.5 });
  bullets(s, [
    `トヨタの論文は、世の中よりチームが大きく（著者数 ${N.team_toyota}人 対 ${N.team_base}人）、参考文献も多い（${N.refs_toyota}本 対 ${N.refs_base}本）`,
    `分野と年だけを揃えると、被引用は多く（${f1(S.fy.c10)}）、破壊性は低い（${f1(S.fy.dis)}）`,
    '破壊性の低さは、参考文献の数とチームの大きさのどちらか一方を揃えるだけで消える',
    '被引用の多さは、チームの大きさを揃えると消える',
    '新規性は、どの揃え方でも50台前半〜半ばで、ほぼ真ん中',
  ], { x: 0.5, y: 2.85, w: 9, h: 2.4, fs: 13, sp: 6 });
  s.addNotes([
    `二つめの作業です。SciSciNet の値を使って、トヨタの論文が世の中でどのあたりにいるかを測りました。比べる相手は、同じ分野・同じ年に出た一般の論文${man(N.n_base)}件で、その中での順位を出しています。50が真ん中です。`,
    `分野と年だけを揃えますと、10年被引用は${f1(S.fy.c10)}で、世の中より多く引用されています。一方、破壊性は${f1(S.fy.dis)}と低めでした。よく引用されるが、既存の流れを断ち切る側ではない、と読めます。`,
    `ただ、トヨタの論文は世の中の論文よりチームが大きく、著者数の中央値が${N.team_toyota}人と、比べる相手の${N.team_base}人より多くなっています。参考文献も${N.refs_toyota}本と、${N.refs_base}本より多いです。そこで、これらを揃えて比べ直しました。`,
    `すると破壊性は、参考文献の数かチームの大きさのどちらか一方を揃えるだけで50前後になります。被引用は、チームの大きさを揃えると${f1(S.team.c10)}まで下がります。つまり、破壊性が低く被引用が多く見えたのは、チームが大きく参考文献が多いことの表れで、トヨタに固有の性質ではありませんでした。大きなチームほど破壊性が低いことは、Wu らが2019年に報告しているとおりです。`,
    '新規性は、どの揃え方でも50台前半から半ばで、ほぼ真ん中です。',
    '（チームの大きさと参考文献の数のどちらが効いているのかと聞かれたら、予備のスライドで説明します）',
  ].join('\n\n'));
}

// ---------- 8. ② 組織別 ----------
{
  const s = slide('② 組織別：豊田中研・未来創成は珍しい組み合わせ寄り', 2);
  note(s, '参考文献の数とチームの大きさを揃えた順位の中央値。50が真ん中', 0.6);
  const rows = [['組織', '件数', '非慣習性', '定石らしさ', '破壊性', '10年被引用']];
  for (const o of N.org_res) rows.push([shortOrg(o.org), o.n, f1(o.nov), f1(o.conv), f1(o.dis), f1(o.c10)]);
  rows.push(['トヨタ全体', N.tot.nov, f1(S.both.nov), f1(S.both.conv), f1(S.both.dis), f1(S.both.c10)].map((v, j) => strong(v, j)));
  table(s, rows, { x: 0.5, y: 0.98, w: 9, colW: [2.6, 0.9, 1.4, 1.4, 1.3, 1.4], rowH: 0.34, fontSize: 12.5 });
  const us = orgBy('AISIN IMRA(米国・imra.com)');
  bullets(s, [
    `豊田中研と未来創成は、珍しい組み合わせ寄り（非慣習性 ${novRange(HIGH)}）`,
    `AISIN IMRA は、定石寄り（非慣習性 ${novRange(LOW)}）`,
    '全体が真ん中に見えるのは、上と下に分かれた組織の平均だから',
    `破壊性はどの組織も真ん中付近。10年被引用は AISIN IMRA（米国）だけが高い（${f1(us.c10)}）`,
  ], { x: 0.5, y: 3.2, w: 9, h: 2.0, fs: 13, sp: 6 });
  s.addNotes([
    `組織別に見ますと、差がございます。新規性は、豊田中央研究所と未来創成センターが${novRange(HIGH)}で、珍しい組み合わせを使う側です。AISIN IMRA の二法人は${novRange(LOW)}で、定石を使う側です。`,
    '先ほど、全体では真ん中と申し上げましたが、それは上と下に分かれた組織の平均になっているためです。',
    `破壊性は、どの組織も真ん中付近でした。10年被引用は、AISIN IMRA の米国法人だけが${f1(us.c10)}と高くなっています。定石寄りでよく引用される論文を出していることになりますが、その理由はまだ調べておりません。`,
  ].join('\n\n'));
}

// ---------- 9. ③ 仮説の検証 ----------
{
  const s = slide('③ 何が新規性を左右するか（仮説の検証）', 3);
  note(s, '新規性（非慣習性）の順位は、分野・年のみを揃えたもの。参考文献の数と引用する分野の広さは統制した', 0.6);
  const ia = D['産学連携'], cr = D['組織横断'];
  table(s, [
    ['要因', '先行研究', '件数', '結果'],
    ['チームの大きさ', 'Uzzi 2013', `${N.n_test}件\n（単著 ${N.n_solo}件）`, left(`関係は見えず（p=${p2(A.h1_team.p)}）。\n単著が少なく、チーム対単著の比較を再現できない`)],
    ['国際共同', 'Wagner 2019', `${N.n_intl}件`, left(`関係は見えず（p=${p2(A.h2_intl.p)}）。\n件数が少なく、小さな差は見逃しうる`)],
    ['産学連携', '仮説なし', `${ia.n_true}件`, left(`やや高い（${f1(ia.median_true)} 対 ${f1(ia.median_false)}）が、はっきりしない（p=${p2(ia.p)}）`)],
    ['組織をまたぐ共同', '仮説なし', `${cr.n_true}件`, left(`差は見えず（p=${p2(cr.p)}）`)],
  ], { x: 0.5, y: 0.98, w: 9, colW: [1.8, 1.4, 1.2, 4.6], rowH: [0.34, 0.6, 0.5, 0.5, 0.4], fontSize: 12 });
  label(s, '組織による差', 3.55);
  bullets(s, [
    `引用する分野の広さと参考文献の数を揃えても残る（p=${p2(A.org_effect_after_controls_p)}）`,
    `ただし、論文ごとのばらつきのうち、組織で説明できるのは約${Math.round(A.org_vs_interdisciplinarity.r2_org_only * 100)}%`,
    '同じ組織の中での違いのほうが、ずっと大きい',
  ], { x: 0.5, y: 3.85, w: 9, h: 1.35, fs: 13, sp: 6 });
  s.addNotes([
    '三つめの作業です。新規性を左右する要因として、先行研究から二つを仮説に立てました。',
    'ここでの新規性の順位は、分野と年だけを揃えたものです。チームの大きさは、効果を見る側に置いているため揃えていません。参考文献の数と、引用する分野の広さは、指標の作り方からして値に響きますので、統制しております。',
    `チームの大きさについては、Uzzi らが、チームで書いた論文は単著より珍しい組み合わせを多く含むと報告しています。今回は関係が見えませんでした。ただ、手元には単著が${N.n_solo}件しかなく、彼らの比べ方をそもそも再現できません。確かめられなかった、というのが正確です。`,
    `国際共同も関係は見えませんでした。こちらも${N.n_intl}件と少なく、小さな差であれば見逃している可能性があります。`,
    '産学連携と組織をまたぐ共同は、文献に裏付けが見つからなかったので、仮説は立てずに値だけ見ました。産学連携のある論文がやや高めですが、はっきりした差とは言えません。',
    `最後に組織の差です。引用する分野の広さと参考文献の数を揃えても、組織の差は残りました。ただ、論文ごとのばらつきのうち、組織で説明できるのは${Math.round(A.org_vs_interdisciplinarity.r2_org_only * 100)}%ほどです。同じ組織の中での違いのほうがずっと大きいということです。`,
  ].join('\n\n'));
}

// ---------- 10. まとめ ----------
{
  const s = slide('まとめ');
  // 一文ごとに改行する
  const items = [
    ['SciSciNet の値の検算', ['SciSciNet の新規性の値は、自前の計算と並び順がよく一致した。以後の分析に使える'], 0.68],
    ['世の中の論文との比較', ['条件を揃えると、トヨタの論文は新規性・破壊性・被引用とも世の中の真ん中', '破壊性の低さと被引用の多さは、チームが大きく参考文献が多いことの表れ',
      '組織では、豊田中研・未来創成が珍しい組み合わせ寄り、AISIN IMRA が定石寄り'], 1.55],
    ['要因の仮説検証', ['チームの大きさと国際共同の効果は、件数が足りず確かめられなかった', '組織の差は残るが、説明できる部分は小さい'], 2.9],
  ];
  items.forEach(([h, lines, y], i) => {
    badge(s, i + 1, 0.5, y);
    s.addText(h, { x: 1.02, y, w: 8.5, h: 0.36, fontFace: F, fontSize: 14, bold: true, color: NAVY, valign: 'middle', margin: 0, isTextBox: true });
    s.addText(lines.map((t, k) => ({ text: t, options: { breakLine: k < lines.length - 1 } })),
      { x: 1.02, y: y + 0.4, w: 8.45, h: 0.26 * lines.length + 0.05, fontFace: F, fontSize: 13, color: BLACK, valign: 'top', margin: 0, isTextBox: true });
  });
  label(s, '分からなかったこと', 4.18);
  bullets(s, [
    '2025年以降の論文（SciSciNet に未収録）',
    '新規性と被引用の関係（この件数では形が定まらない）',
  ], { x: 0.5, y: 4.46, w: 9, h: 0.7, fs: 12, sp: 2, color: GRAY });
  s.addNotes([
    'まとめです。',
    '一つめ、SciSciNet の新規性の値は、自前の計算と並び順がよく一致しましたので、分析に使えると判断しました。',
    '二つめ、条件を揃えると、トヨタの論文は新規性も破壊性も被引用も世の中の真ん中でした。破壊性が低く被引用が多く見えたのは、チームが大きく参考文献が多いことの表れです。組織では、豊田中研と未来創成が珍しい組み合わせを使う側、AISIN IMRA が定石を使う側でした。',
    '三つめ、チームの大きさと国際共同の効果は、件数が足りず確かめられませんでした。組織の差は残りますが、説明できる部分は小さいです。',
    '分からなかったこととして、2025年以降の論文は SciSciNet に入っておらず扱えていません。また、新規性と被引用の関係は、この件数では形が定まりませんでした。',
  ].join('\n\n'));
}

// ---------- 11. 今後とご相談 ----------
{
  const s = slide('今後とご相談');
  label(s, '次の段階：hot streak（先生の問いのうち「どの研究者が特に成功するか」）', 0.7);
  bullets(s, [
    '研究者一人ひとりの、トヨタ以外も含めた全キャリアの論文が要る',
    'サイトに20本以上の論文がある研究者は18名だけ → 論文を集め直す必要がある',
    '手間の見積もりを、次回までにお出しします',
  ], { x: 0.5, y: 1.0, w: 9, h: 1.3, fs: 13, sp: 6 });
  s.addShape(pres.shapes.RECTANGLE, { x: 0.5, y: 2.35, w: 9, h: 2.15, fill: { color: TINT }, line: { color: TINT } });
  label(s, 'ご判断をお願いしたいこと', 2.47, 0.7, 8.6);
  bullets(s, [
    'hot streak を、この方向で進めてよいか',
    '対象期間：2000年以降としてよいか',
    '対象組織：今の4組織でよいか',
    { text: 'デンソー、Toyota Research Institute などを加えるか。豊田工業大学は除外を提案', sub: true },
    'Sota Hayashi さんとの分担',
  ], { x: 0.7, y: 2.8, w: 8.6, h: 1.62, fs: 13, sp: 6, numbered: true });
  s.addNotes([
    '次の段階は hot streak です。先生の問いのうち、どの研究者が特に成功するかに当たります。',
    'hot streak を見るには、研究者一人ひとりについて、トヨタ以外での論文も含めた全キャリアの論文が要ります。いまのデータでは、サイトに20本以上の論文がある研究者は18名しかおりませんので、論文を集め直す必要があります。',
    '前回、手間を見積もってからご相談すると申し上げましたが、まだお出しできておりません。次回までにお出しします。',
    'そのうえで、ご判断をお願いしたいことが四つございます。（読み上げる）',
  ].join('\n\n'));
}

// ---------- 12. 別件：SciSciGPT ----------
{
  const s = slide('別件：SciSciGPT と、AI の使い方の書き物');
  bullets(s, [
    { text: 'SciSciGPT（Shao et al. 2025）', b: true },
    { text: 'SciSciNet のデータを、自然言語の指示で AI が分析する道具', sub: true },
    { text: '精読済み。トヨタの論文を扱えないため、今回の分析には使っていない', sub: true },
    { text: '同種の研究を調査中（AI の使い方の書き物に向けて）', b: true },
  ], { x: 0.5, y: 0.7, w: 9, h: 1.5, fs: 14 });
  table(s, [
    ['同種の研究', '年', '掲載', '被引用数'],
    ['Coscientist（化学実験の自動化）', '2023', 'Nature', '981'],
    ['The AI Scientist（論文作成の自動化）', '2024', 'arXiv', '114'],
    ['SciSciGPT（科学計量）', '2025', 'Nat. Comput. Sci.', '6'],
  ], { x: 0.5, y: 2.35, w: 9, colW: [4.6, 0.9, 2.2, 1.3], rowH: 0.36, fontSize: 12 });
  s.addNotes([
    '別件です。SciSciGPT は、SciSciNet のデータに言葉で指示すると、AI が分析してくれる道具です。精読しましたが、トヨタの論文を扱えないため、今回の分析には使っておりません。',
    '先生からいただいている、AI の使い方についての書き物に向けて、同じ種類の研究を調べております。',
  ].join('\n\n'));
}

// ---------- 13. 予備：チームの大きさ別の破壊性 ----------
{
  const s = slide('予備　チームの大きさ別の破壊性');
  note(s, '破壊性の順位の中央値（50が真ん中）。どれも同じ分野・同じ年の一般論文との比較', 0.6);
  const rows = [['チームの大きさ', '件数', '分野・年のみ', '＋参考文献の数', '＋チームの大きさ', '＋両方']];
  for (const t of N.team_strata) rows.push([t.t, t.n, f1(t.fy), f1(t.ref), f1(t.team), f1(t.both)]);
  table(s, rows, { x: 0.5, y: 0.98, w: 9, colW: [1.9, 0.9, 1.55, 1.55, 1.55, 1.55], rowH: 0.34, fontSize: 12.5 });
  bullets(s, [
    '分野と年だけを揃えると、チームが大きいほど破壊性が低い（Wu et al. 2019 と同じ傾向）',
    'チームの大きさを揃えると、ほぼ平らになる',
    '参考文献の数だけを揃えても、チームの大きさによる傾きは残る',
  ], { x: 0.5, y: 2.95, w: 9, h: 1.8, fs: 13, sp: 8 });
  s.addNotes([
    '（質問が出たときに使う）チームの大きさ別に破壊性を見たものです。',
    '分野と年だけを揃えると、チームが大きいほど破壊性が低くなります。Wu らの報告と同じ傾向です。チームの大きさを揃えると、ほぼ平らになります。',
    '参考文献の数だけを揃えた場合は、全体の中央値は50前後になりますが、チームの大きさによる傾きは残ります。チームの大きさと参考文献の数は重なっていて、全体の水準についてはどちらか一方に帰すことはできません。',
  ].join('\n\n'));
}

pres.writeFile({ fileName: OUT }).then(f => console.log('written', f));
