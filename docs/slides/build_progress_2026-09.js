// 進捗報告資料（2026年9月）を生成する。
// 構成: 表紙 → 概要 → データ・指標 → 1. 公開値の検証 → 2. 一般論文との比較 → 3. 要因の検証
//       → その他 → 今後の予定 → 確認事項 → まとめ → 補足
// 体裁は研究発表の一般的な作法に合わせる（2026-09-27 に解説ページを参照して決めた。log.md 参照）。
//   白地・装飾なし、見出しはスライド左上に内容の要約、本文は体言止め・である調、
//   色は見出しの色と強調色の2色まで、表は縦線なしで横線のみ、スライド番号は右下。
// 数字はすべて make_numbers_progress_2026-09.py が書き出す JSON から読む。話す内容は発表者ノートに入れてある。
// 実行: NODE_PATH=<pptxgenjs のある node_modules> node build_progress_2026-09.js [出力先.pptx]
const path = require('path');
const pptxgen = require('pptxgenjs');
const N = require('./numbers_progress_2026-09.json');
const OUT = process.argv[2] || path.join(__dirname, 'toyota_novelty_progress.pptx');
const IMG = path.join(__dirname, 'fig_verification_scatter.png');
const pres = new pptxgen();
pres.layout = 'LAYOUT_WIDE';            // 13.333 x 7.5 in（PowerPoint の標準の 16:9）
const W = 13.333, H = 7.5, MX = 0.6, CW = W - 2 * MX;
const F = 'Meiryo';
const MAIN = '1F3864';                  // 見出しの色
const ACCENT = 'C55A11';                // 強調色（数値の強調にだけ使う）
const TEXT = '262626', SUB = '595959', RULE = '404040', LIGHT = 'BFBFBF';
let page = 0;

// 文字に日本語の指定を付ける。付けないと英語扱いになり、句読点や括弧が行頭に来る改行を PowerPoint が許してしまう
function jp(s) {
  const addText = s.addText.bind(s), addTable = s.addTable.bind(s);
  s.addText = (t, o) => addText(t, Object.assign({ lang: 'ja-JP' }, o));
  s.addTable = (rows, o) => addTable(rows, Object.assign({ lang: 'ja-JP' }, o));
  return s;
}
// 本文のスライド。左上に見出し、右下にスライド番号。lead を渡すと見出しの下に説明を1行置く
function slide(title, lead) {
  page += 1;
  const s = jp(pres.addSlide());
  s.background = { color: 'FFFFFF' };
  s.addText(title, { x: MX, y: 0.4, w: CW, h: 0.65, fontFace: F, fontSize: 26, bold: true, color: MAIN, valign: 'middle', margin: 0, isTextBox: true });
  if (lead) s.addText(lead, { x: MX, y: 1.1, w: CW, h: 0.4, fontFace: F, fontSize: 16, color: SUB, valign: 'middle', margin: 0, isTextBox: true });
  s.addText(String(page), { x: W - 1.2, y: H - 0.5, w: 0.6, h: 0.3, fontFace: F, fontSize: 12, color: '7F7F7F', align: 'right', valign: 'middle', margin: 0, isTextBox: true });
  return s;
}
function heading(s, text, y, x = MX, w = CW) {
  s.addText(text, { x, y, w, h: 0.4, fontFace: F, fontSize: 20, bold: true, color: TEXT, valign: 'middle', margin: 0, isTextBox: true });
}
// 箇条書き。項目は文字列か { text, sub, b }。text を配列にすると、その位置で改行する（語の途中で折り返さないため）。
// numbered で番号付き（下位の項目は黒丸のまま）
function bullets(s, items, opt) {
  const fs = opt.fs || 20;
  const arr = [];
  items.forEach((t, i) => {
    const o = typeof t === 'string' ? { text: t } : t;
    const lines = Array.isArray(o.text) ? o.text : [o.text];
    const bullet = o.sub ? { indent: 18 } : (opt.numbered ? { type: 'number', indent: 24 } : { indent: 18 });
    const size = o.sub ? fs - 2 : fs, last = i === items.length - 1;
    lines.forEach((line, k) => {
      const run = { bold: !!o.b, fontSize: size, breakLine: !last && k === lines.length - 1 };
      if (k === 0) Object.assign(run, { bullet, indentLevel: o.sub ? 1 : 0, paraSpaceAfter: opt.sp ?? 8 });
      else run.softBreakBefore = true;
      arr.push({ text: line, options: run });
    });
  });
  s.addText(arr, { x: opt.x ?? MX, y: opt.y, w: opt.w ?? CW, h: opt.h, fontFace: F, color: TEXT, valign: 'top', margin: 0, isTextBox: true });
}
// 表。縦線を引かず、上下の太い横線・見出しの下の線・行の間の細い線だけにする
function table(s, rows, opt) {
  const n = rows.length;
  const edge = r => (r === 0 || r === n) ? { type: 'solid', pt: 1.5, color: RULE }
    : r === 1 ? { type: 'solid', pt: 1, color: RULE } : { type: 'solid', pt: 0.5, color: LIGHT };
  const none = { type: 'none' };
  const align = opt.align || (j => (j === 0 ? 'left' : 'center'));
  const body = rows.map((r, i) => r.map((c, j) => {
    const cell = typeof c === 'object' ? c : { text: String(c), options: {} };
    // 表のセルには文字枠の言語指定が引き継がれないので、セルごとに付ける
    const o = Object.assign({ align: align(j), valign: 'middle', lang: 'ja-JP', border: [edge(i), none, edge(i + 1), none] }, cell.options);
    if (i === 0) Object.assign(o, { bold: true, color: TEXT });
    return { text: cell.text, options: o };
  }));
  s.addTable(body, Object.assign({ x: MX, w: CW, fontFace: F, fontSize: 18, color: TEXT, margin: [0.06, 0.12, 0.06, 0.12] }, opt, { align: undefined }));
}
const em = t => ({ text: String(t), options: { bold: true, color: ACCENT } });   // 表の中の強調
const b = (t, j = 1) => ({ text: String(t), options: { bold: true, align: j ? 'center' : 'left' } });
const shortOrg = o => ({ 'AISIN IMRA(日本・aisin.com)': 'AISIN IMRA（日本）', 'AISIN IMRA(米国・imra.com)': 'AISIN IMRA（米国）',
  'トヨタ自動車未来創成センター': '未来創成センター', '豊田中央研究所': '豊田中央研究所' }[o] || o);
const f1 = v => Number(v).toFixed(1);
const p2 = v => (v < 0.01 ? v.toFixed(3) : v.toFixed(2));
const man = n => `${Math.floor(n / 10000)}万${Math.round((n % 10000) / 1000)}千`;   // 432000 → 43万2千
const S = N.stages, A = N.ana, D = A.descriptive_only;
const V = lab => N.ver.find(v => v.lab === lab);
const [spLo, spHi] = [V('定石らしさ').sp, V('zスコアの下位10%').sp].sort((a, c) => a - c).map(v => v.toFixed(2));
const orgBy = name => N.org_res.find(o => o.org === name);
const novRange = names => { const v = names.map(n => orgBy(n).nov); return `${Math.round(Math.min(...v))}〜${Math.round(Math.max(...v))}`; };
const HIGH = ['豊田中央研究所', 'トヨタ自動車未来創成センター'], LOW = ['AISIN IMRA(日本・aisin.com)', 'AISIN IMRA(米国・imra.com)'];
const allNov = ['fy', 'ref', 'team', 'both'].flatMap(k => [S[k].nov, S[k].conv]);
const novLo = Math.floor(Math.min(...allNov)), novHi = Math.ceil(Math.max(...allNov));
const r2org = Math.round(A.org_vs_interdisciplinarity.r2_org_only * 100);
const notes = (s, parts) => s.addNotes(parts.join('\n\n'));

// ---------- 表紙 ----------
{
  page += 1;
  const s = jp(pres.addSlide()); s.background = { color: 'FFFFFF' };
  s.addText('トヨタ関連企業の論文の新規性分析', { x: MX, y: 2.0, w: CW, h: 0.9, fontFace: F, fontSize: 36, bold: true, color: MAIN, align: 'center', valign: 'middle', margin: 0, isTextBox: true });
  s.addText('SciSciNet を用いた新規性・破壊性の検証', { x: MX, y: 2.95, w: CW, h: 0.55, fontFace: F, fontSize: 22, color: TEXT, align: 'center', valign: 'middle', margin: 0, isTextBox: true });
  s.addText('進捗報告　2026年9月', { x: MX, y: 3.75, w: CW, h: 0.45, fontFace: F, fontSize: 18, color: TEXT, align: 'center', valign: 'middle', margin: 0, isTextBox: true });
  s.addText('大阪大学大学院 工学研究科　田中研究室\n伊倉 涼介', { x: MX, y: 4.8, w: CW, h: 0.9, fontFace: F, fontSize: 18, color: TEXT, align: 'center', valign: 'middle', margin: 0, isTextBox: true });
  notes(s, ['トヨタ関連企業の論文の新規性について、前回以降の進捗をご報告します。']);
}

// ---------- 概要 ----------
{
  const s = slide('本報告の概要');
  s.addText([
    { text: '目的：', options: { bold: true } },
    { text: 'トヨタ関連の論文について、新規性・破壊性の水準と、それを左右する要因を調べる', options: { breakLine: true } },
    { text: 'データ：', options: { bold: true } },
    { text: `トヨタ関連4組織の公式サイトから収集した論文 ${N.tot.site}件（OpenAlex で特定 ${N.tot.matched}件）` },
  ], { x: MX, y: 1.3, w: CW, h: 0.9, fontFace: F, fontSize: 20, color: TEXT, valign: 'top', margin: 0, paraSpaceAfter: 6, isTextBox: true });
  heading(s, '実施内容と結果', 2.35);
  // セルの中は語の途中で折り返さないよう、改行位置を指定する
  table(s, [
    ['項目', '実施内容', '結果'],
    ['1. SciSciNet 公開値の検証', '同じ指標を自前でも計算し、\n公開値と比較', `並び順はよく一致\n（順位相関 ${spLo}〜${spHi}）\n以降は公開値を使用`],
    ['2. 一般論文との比較', `同じ分野・同じ年の一般論文\n約${Math.round(N.n_base / 10000)}万件の中での順位を算出`, '条件を揃えると中央付近\n（新規性・破壊性・被引用）\n組織間には差'],
    ['3. 新規性の要因の検証', '先行研究にもとづく仮説を検証\n（チーム規模・国際共同）', 'いずれも関係は見られず\n件数が少なく、確かめきれていない'],
  ], { y: 2.8, colW: [3.8, 3.9, CW - 7.7], rowH: [0.45, 1.05, 1.05, 0.8], align: () => 'left' });
  s.addText('その他：SciSciGPT の精読と関連研究の調査（AI の研究利用に関する報告の準備）',
    { x: MX, y: 6.3, w: CW, h: 0.4, fontFace: F, fontSize: 18, color: TEXT, valign: 'middle', margin: 0, isTextBox: true });
  notes(s, [
    '今回の報告の概要です。',
    `目的は、トヨタ関連の論文について、新規性や破壊性がどの程度か、それが何によって決まるかを調べることです。データは、トヨタ関連4組織の公式サイトから集めた論文${N.tot.site}件です。`,
    '今回は三つのことを行いました。一つめに、SciSciNet が公開している新規性の値が信頼できるかを、同じ指標を自前でも計算して確かめました。並び順がよく一致しましたので、以降は公開値を使っています。',
    '二つめに、その値を使って、トヨタの論文が同じ分野・同じ年の一般の論文の中でどのあたりにいるかを測りました。条件を揃えると、どの指標も中央付近でした。ただし組織の間には差がございます。',
    '三つめに、新規性を左右する要因として、先行研究にもとづく仮説を検証しました。チームの大きさと国際共同を調べましたが、関係は見られませんでした。ただ件数が少なく、確かめきれていないというのが正確です。',
    'このほか、SciSciGPT の論文と関連研究を調べております。',
  ]);
}

// ---------- データの出典 ----------
{
  const s = slide('データの出典');
  table(s, [
    ['項目', '出典'],
    ['トヨタの論文の特定、組織の区別', '自前（4組織の公式サイトから収集）'],
    ['各論文の指標（新規性・破壊性・被引用）', 'SciSciNet の公開値'],
    ['比較対象（同じ分野・同じ年の一般論文）の指標', 'SciSciNet の公開値'],
  ], { y: 1.35, colW: [6.4, CW - 6.4], rowH: 0.5, align: () => 'left' });
  bullets(s, [
    'SciSciNet：約2.5億本の論文について、新規性・破壊性などの指標を計算して公開しているデータ（Northwestern 大学）',
    '一般論文と比べるには、比較対象にも同じ出典の値が必要なため、公開値を使用',
    '計算条件の一部が非公開のため、同じ指標を自前でも計算して確認（1.）',
    '前回報告（9月8日）からの変更：主に使う値を、自前の計算から公開値に変更',
  ], { y: 3.65, h: 3.2, fs: 20 });
  notes(s, [
    'データの出典です。どれがトヨタの論文か、どの組織の論文かは、公式サイトから自前で特定しました。',
    '新規性などの指標と、比べる相手になる一般の論文の指標は、SciSciNet の公開値を使っています。SciSciNet は、約2.5億本の論文について指標を計算して公開しているデータです。世の中と比べるには、比べる相手にも同じ出どころの値が要るためです。',
    'ただ、SciSciNet は計算の細かい条件を公開していませんので、同じ指標を自前でも計算して確かめました。これが一つめの作業です。',
    'なお前回は、自前の計算を主に使うと申し上げましたが、この理由から、公開値を主に使う形に変えております。',
  ]);
}

// ---------- 対象論文 ----------
{
  const s = slide('対象論文');
  const rows = [['組織', 'サイト掲載', 'OpenAlex\nで特定', 'SciSciNet に値あり\n（2000年以降）', '新規性の\n値あり']];
  for (const o of N.org) rows.push([shortOrg(o.org), o.site, o.matched, o.ss, o.nov]);
  const t = N.tot;
  rows.push(['合計', t.site, t.matched, t.ss, t.nov].map((v, j) => b(v, j)));
  table(s, rows, { y: 1.35, colW: [3.4, 1.9, 2.3, 2.7, CW - 10.3], rowH: [0.8, 0.45, 0.45, 0.45, 0.45, 0.45] });
  bullets(s, [
    { text: ['組織は公式サイトへの掲載で特定', '（OpenAlex の所属情報は誤りが多く、トヨタ所属を確認できるのは約半数）'] },
    '対象は2000年以降。2025年以降の論文は SciSciNet に未収録',
    '未来創成センターと AISIN IMRA（米国）は、新規性の値が得られたのがサイト掲載の半分以下',
  ], { y: 4.6, h: 2.3, fs: 18 });
  notes(s, [
    `対象の論文です。公式サイトに載っていた${t.site}件のうち、OpenAlex で特定できたのが${t.matched}件です。対象は2000年以降に絞っており、SciSciNet に値があるのが${t.ss}件、新規性の値まであるのが${t.nov}件です。SciSciNet は2024年までの論文しか収録していないので、2025年以降の論文は入っておりません。`,
    'どの組織の論文かは、OpenAlex の所属情報ではなく、公式サイトに載っていたかどうかで決めています。OpenAlex の所属情報は誤りが多く、トヨタ所属を確認できるのは約半数だったためです。',
    '未来創成センターと AISIN IMRA の米国法人は、値が取れたのがサイトに載っている論文の半分以下ですので、この二つの組織の結果は件数が少ない点にご留意ください。',
  ]);
}

// ---------- 指標 ----------
{
  const s = slide('指標');
  heading(s, '新規性（Uzzi et al. 2013）', 1.3);
  bullets(s, [
    '論文の参考文献が掲載された雑誌を、2誌ずつすべて組にする',
    { text: ['各組が同じ年の論文全体で一緒に引用される頻度を、', '引用先を無作為に入れ替えた場合と比べて zスコアにする（小さいほど珍しい組）'] },
    '論文ごとに2つの値を取る',
    { text: '定石らしさ：zスコアの中央値（高いほど、よくある組が中心）', sub: true },
    { text: '非慣習性：zスコアの下位10%（順位は、珍しい組を含むほど高くなる向きに揃えた）', sub: true },
  ], { y: 1.8, h: 2.65, fs: 18, sp: 5, numbered: true });
  heading(s, 'その他の指標', 4.6);
  bullets(s, [
    { text: ['破壊性（Wu et al. 2019）：その論文を引用する後続論文のうち、', 'その論文の参考文献を引用しないものが多いほど高い'] },
    '10年被引用：出版後10年間の被引用数',
    '順位：同じ分野・同じ年の一般論文の中での位置（0〜100、50が中央）',
  ], { y: 5.1, h: 1.8, fs: 18, sp: 5 });
  notes(s, [
    '新規性は、Uzzi らの2013年の方法で測ります。論文の参考文献に載っている雑誌を二つずつ組にして、その組が世の中でどれくらい一緒に引用されにくいかを、引用先を無作為に入れ替えた場合と比べて求めます。',
    '論文ごとに二つの値を取ります。定石らしさは、よくある組み合わせがどれだけ中心にあるか。非慣習性は、珍しい組み合わせをどれだけ含むかです。非慣習性は、読み違えないよう、高いほど珍しいという向きに揃えてあります。',
    '破壊性は Wu らの2019年の指標で、既存の研究の流れを断ち切った度合いです。あわせて影響力の目安として、10年間の被引用数も見ています。',
    'これらを、同じ分野・同じ年に出た一般の論文の中での順位に直して比べます。50が真ん中です。',
  ]);
}

// ---------- 1. SciSciNet 公開値の検証 ----------
{
  const conv = V('定石らしさ'), atyp = V('zスコアの下位10%');
  const s = slide('1. SciSciNet 公開値の検証', `同じ指標を自前でも計算し、両方に値がある ${N.ver_n}件で比較（1点が1論文、破線は両者が同じ値）`);
  s.addImage({ path: IMG, x: MX, y: 1.75, w: 7.0, h: 7.0 * 3.9 / 9.0 });
  bullets(s, [
    { text: ['並び順はよく一致', `（順位相関：定石らしさ ${conv.sp.toFixed(2)}、`, `非慣習性 ${atyp.sp.toFixed(2)}）`] },
    { text: ['値の大きさは一致しない', '（定石らしさの中央値：', `自前 ${Math.round(conv.med_own)}、公開 ${Math.round(conv.med_ss)}）`] },
    { text: ['原因は、掲載誌の決め方など', '計算条件の一部が非公開であること'] },
    { text: ['以降の分析は公開値を使用し、', '自前の値とは混ぜない'] },
  ], { x: 7.9, y: 1.8, w: W - MX - 7.9, h: 5.0, fs: 18, sp: 12 });
  notes(s, [
    `一つめの作業です。同じ指標を自前でも計算し、両方に値がある${N.ver_n}件で突き合わせました。横軸が自前の値、縦軸が公開値です。`,
    `並び順の一致を表す順位相関は、定石らしさで${conv.sp.toFixed(2)}、非慣習性で${atyp.sp.toFixed(2)}でした。並び順はよく一致しています。`,
    `一方、値の大きさは揃いません。定石らしさの中央値は、自前が${Math.round(conv.med_own)}、公開値が${Math.round(conv.med_ss)}です。論文の掲載誌の決め方など、公開されていない条件が違うためと考えています。`,
    '以上から、以降の分析は SciSciNet の値で行い、自前の値とは混ぜないことにしました。',
    `（質問が出たら）値そのものの相関係数は、定石らしさで${conv.pe.toFixed(2)}、非慣習性で${atyp.pe.toFixed(2)}です。非慣習性が低いのは、公開値に極端に大きい値が少数あるためで、上下1%を除くと${atyp.pe_trim.toFixed(2)}になります。`,
  ]);
}

// ---------- 2. 一般論文との比較（全体） ----------
{
  const s = slide('2. 一般論文との比較（全体）', `同じ分野・同じ年の一般論文（${man(N.n_base)}件）の中での順位の中央値（0〜100、50が中央）`);
  table(s, [
    ['揃えた条件', '非慣習性', '定石らしさ', '破壊性', '10年被引用'],
    ['分野・年のみ', f1(S.fy.nov), f1(S.fy.conv), em(f1(S.fy.dis)), em(f1(S.fy.c10))],
    ['分野・年＋参考文献数', f1(S.ref.nov), f1(S.ref.conv), f1(S.ref.dis), f1(S.ref.c10)],
    ['分野・年＋チーム規模', f1(S.team.nov), f1(S.team.conv), f1(S.team.dis), f1(S.team.c10)],
    ['分野・年＋両方', f1(S.both.nov), f1(S.both.conv), f1(S.both.dis), f1(S.both.c10)],
  ], { y: 1.75, colW: [3.6, 2.13, 2.13, 2.13, CW - 9.99], rowH: 0.46 });
  bullets(s, [
    `分野と年のみ揃えると、10年被引用は高く（${f1(S.fy.c10)}）、破壊性は低い（${f1(S.fy.dis)}）`,
    `トヨタの論文は一般論文より、著者数（${N.team_toyota}人 対 ${N.team_base}人）も参考文献数（${N.refs_toyota}本 対 ${N.refs_base}本）も多い`,
    '参考文献数かチーム規模の一方を揃えると破壊性は約50。チーム規模を揃えると被引用も約50',
    `新規性（非慣習性・定石らしさ）は、どの条件でも${novLo}〜${novHi}で中央付近`,
  ], { y: 4.35, h: 2.6, fs: 18, sp: 8 });
  notes(s, [
    `二つめの作業です。SciSciNet の値を使って、トヨタの論文が、同じ分野・同じ年に出た一般の論文${man(N.n_base)}件の中でどのあたりにいるかを、順位で表しました。50が真ん中です。`,
    `分野と年だけを揃えますと、10年被引用は${f1(S.fy.c10)}で、世の中より多く引用されています。一方、破壊性は${f1(S.fy.dis)}と低めでした。よく引用されるが、既存の流れを断ち切る側ではない、と読めます。`,
    `ただ、トヨタの論文は著者数の中央値が${N.team_toyota}人と、比べる相手の${N.team_base}人より多く、参考文献も${N.refs_toyota}本と、${N.refs_base}本より多くなっています。そこでこれらも揃えて比べ直しました。`,
    `すると破壊性は、参考文献数かチーム規模のどちらか一方を揃えるだけで50前後に戻ります。被引用は、チーム規模を揃えると${f1(S.team.c10)}まで下がります。つまり、よく引用されるが流れを断ち切らないように見えたのは、トヨタに固有の性質ではなく、チームが大きく参考文献が多いことの表れでした。大きなチームほど破壊性が低いことは、Wu らが2019年に報告しています。`,
    '新規性は、どの揃え方でも中央付近です。',
    '（チーム規模と参考文献数のどちらが効いているのかと聞かれたら、補足のスライドで説明します）',
  ]);
}

// ---------- 2. 一般論文との比較（組織別） ----------
{
  const us = orgBy('AISIN IMRA(米国・imra.com)');
  const s = slide('2. 一般論文との比較（組織別）', '参考文献数とチーム規模も揃えた順位の中央値（50が中央）');
  const rows = [['組織', '件数', '非慣習性', '定石らしさ', '破壊性', '10年被引用']];
  for (const o of N.org_res) rows.push([shortOrg(o.org), o.n, b(f1(o.nov)), f1(o.conv), f1(o.dis), f1(o.c10)]);
  rows.push(['トヨタ全体', N.tot.nov, f1(S.both.nov), f1(S.both.conv), f1(S.both.dis), f1(S.both.c10)]);
  table(s, rows, { y: 1.75, colW: [3.4, 1.3, 1.86, 1.86, 1.86, CW - 10.28], rowH: 0.46 });
  bullets(s, [
    `非慣習性：豊田中研・未来創成は ${novRange(HIGH)}、AISIN IMRA は ${novRange(LOW)}`,
    '全体が中央付近なのは、上下に分かれた組織の平均のため',
    `10年被引用は AISIN IMRA（米国）のみ高い（${f1(us.c10)}）。理由は未調査`,
  ], { y: 4.85, h: 2.0, fs: 18, sp: 8 });
  notes(s, [
    `組織別に見ますと差がございます。新規性のうち非慣習性は、豊田中央研究所と未来創成センターが${novRange(HIGH)}で、珍しい組み合わせを使う側です。AISIN IMRA の二法人は${novRange(LOW)}で、定石を使う側です。`,
    '先ほど全体では真ん中と申し上げましたが、それは上と下に分かれた組織の平均になっているためです。',
    `破壊性は、どの組織も真ん中付近でした。10年被引用は、AISIN IMRA の米国法人だけが${f1(us.c10)}と高くなっています。定石寄りでよく引用される論文を出していることになりますが、理由はまだ調べておりません。`,
  ]);
}

// ---------- 3. 新規性の要因の検証 ----------
{
  const ia = D['産学連携'], cr = D['組織横断'];
  const s = slide('3. 新規性の要因の検証', '非慣習性の順位（分野・年のみ揃えたもの）を、参考文献数と引用分野の広さを統制して検証');
  table(s, [
    ['要因', '先行研究', '件数', '結果'],
    ['チーム規模', 'Uzzi et al. 2013', `${N.n_test}件\n（単著 ${N.n_solo}件）`, `関係なし（p=${p2(A.h1_team.p)}）\n単著が少なく、チーム対単著は比較不可`],
    ['国際共同', 'Wagner et al. 2019', `${N.n_intl}件`, `関係なし（p=${p2(A.h2_intl.p)}）\n件数が少なく、小さな差は見逃しうる`],
    ['産学連携', '仮説なし', `${ia.n_true}件`, `やや高い（${f1(ia.median_true)} 対 ${f1(ia.median_false)}）\n差は明確でない（p=${p2(ia.p)}）`],
    ['組織をまたぐ共同', '仮説なし', `${cr.n_true}件`, `差なし（p=${p2(cr.p)}）`],
  ], { y: 1.75, colW: [2.4, 2.75, 2.1, CW - 7.25], rowH: [0.45, 0.8, 0.8, 0.8, 0.46], align: j => (j === 0 || j === 3 ? 'left' : 'center') });
  heading(s, '組織による差', 5.4);
  bullets(s, [
    `引用分野の広さと参考文献数を統制しても残る（p=${p2(A.org_effect_after_controls_p)}）`,
    `ただし、論文ごとのばらつきのうち組織で説明できるのは約${r2org}%`,
  ], { y: 5.9, h: 1.0, fs: 18, sp: 6 });
  notes(s, [
    '三つめの作業です。新規性を左右する要因として、先行研究から二つを仮説に立てました。',
    'ここでの新規性の順位は、分野と年だけを揃えたものです。チーム規模は効果を見る側に置いているため揃えていません。参考文献数と引用する分野の広さは、指標の作り方からして値に響きますので、統制しております。',
    `チーム規模については、Uzzi らが、チームで書いた論文は単著より珍しい組み合わせを多く含むと報告しています。今回は関係が見られませんでした。ただ、手元には単著が${N.n_solo}件しかなく、彼らの比べ方そのものを再現できません。確かめられなかったというのが正確です。`,
    `国際共同も関係は見られませんでした。こちらも${N.n_intl}件と少なく、小さな差であれば見逃している可能性があります。`,
    '産学連携と組織をまたぐ共同は、文献に裏付けが見つからなかったので、仮説は立てずに値だけ見ました。産学連携のある論文がやや高めですが、はっきりした差とは言えません。',
    `組織の差は、引用する分野の広さと参考文献数を揃えても残りました。ただ、論文ごとのばらつきのうち、組織で説明できるのは${r2org}%ほどで、同じ組織の中での違いのほうがずっと大きいということです。`,
  ]);
}

// ---------- その他：SciSciGPT ----------
{
  const s = slide('その他：SciSciGPT の調査');
  bullets(s, [
    { text: ['SciSciGPT（Shao et al. 2025, Nature Computational Science）', 'SciSciNet のデータを、言葉での指示にもとづいて AI が分析するシステム'] },
    '今回の分析には使用していない（SciSciNet のデータを直接集計）',
    'AI の研究利用に関する報告の準備として、同種のシステムと、AI の研究利用への批判を調査中',
  ], { y: 1.3, h: 2.3, fs: 18, sp: 8 });
  table(s, [
    ['システム', '内容', '年', '掲載', '被引用数'],
    ['Coscientist', '化学実験の自動化', '2023', 'Nature', '981'],
    ['The AI Scientist', '論文作成の自動化', '2024', 'arXiv', '114'],
    ['SciSciGPT', '科学計量の分析', '2025', 'Nat. Comput. Sci.', '6'],
  ], { y: 3.85, colW: [3.2, 3.5, 1.2, 2.7, CW - 10.6], rowH: 0.46 });
  s.addText('被引用数は OpenAlex による（2026年6月時点）', { x: MX, y: 5.8, w: CW, h: 0.35, fontFace: F, fontSize: 14, color: SUB, valign: 'middle', margin: 0, isTextBox: true });
  notes(s, [
    'このほか、SciSciGPT を調べました。SciSciNet のデータに言葉で指示すると、AI が手順を組み立てて分析してくれるシステムです。今回の分析には使っておらず、SciSciNet のデータを直接集計しています。',
    '先生からいただいている、AI の研究利用についての報告に向けて、同じ種類のシステムと、AI の研究利用への批判を調べております。',
  ]);
}

// ---------- 今後の予定 ----------
{
  const s = slide('今後の予定');
  bullets(s, [
    '研究者ごとの論文の再収集について、作業量を見積もる（次回報告まで）',
    { text: ['hot streak（研究者の業績が一時期に集中する現象）の分析には、', 'トヨタ以外も含めたキャリア全体の論文が必要'], sub: true },
    { text: 'サイト上で20本以上の論文がある研究者は18名のみ', sub: true },
    'hot streak の分析（見積もりの確認後に着手）',
    'AI の研究利用に関する報告書の作成',
  ], { y: 1.35, h: 5.4, fs: 20, sp: 10 });
  notes(s, [
    '今後の予定です。次の段階は hot streak で、先生の問いのうち、どの研究者が特に成功するかに当たります。',
    'hot streak を見るには、研究者一人ひとりについて、トヨタ以外での論文も含めたキャリア全体の論文が要ります。いまのデータでは、サイトに20本以上の論文がある研究者は18名しかおりませんので、論文を集め直す必要があります。',
    '前回、この作業の手間を見積もってからご相談すると申し上げましたが、まだお出しできておりません。次回までにお出しします。そのうえで hot streak の分析に着手します。あわせて、AI の研究利用についての報告書をまとめます。',
  ]);
}

// ---------- 確認事項 ----------
{
  const s = slide('確認事項');
  bullets(s, [
    'hot streak を、研究者ごとの論文の再収集を前提に進めてよいか',
    '対象期間：2000年以降でよいか（1990年代以前の62件はすべて AISIN IMRA 米国法人）',
    '対象組織：現在の4組織でよいか',
    { text: 'デンソー、Toyota Research Institute などを加えるか', sub: true },
    { text: '豊田工業大学は教育研究機関のため、除外を提案', sub: true },
    'Sota Hayashi さんとの役割分担',
  ], { y: 1.35, h: 5.4, fs: 20, sp: 10, numbered: true });
  notes(s, [
    '確認させていただきたいことが四点ございます。',
    '一つめは、hot streak を、研究者ごとに論文を集め直す前提で進めてよいかです。',
    '二つめは対象期間です。1990年代以前の論文は参考文献の登録が薄く、新規性の値が不安定になるため、2000年以降に絞っております。なお、1990年代以前の論文62件は、すべて AISIN IMRA の米国法人のものです。',
    '三つめは対象組織です。Web of Science で調べたところ、デンソーや Toyota Research Institute などにも論文がまとまってございます。豊田工業大学は、企業の研究所ではなく教育研究機関ですので、除外することを提案いたします。',
    '四つめは、Sota Hayashi さんとの役割分担です。作業が重複している可能性がございますので、ご教示いただけますと助かります。',
  ]);
}

// ---------- まとめ ----------
{
  const s = slide('まとめ');
  bullets(s, [
    'SciSciNet 公開値の検証：自前の計算と並び順がよく一致し、以降の分析に使用',
    '一般論文との比較：条件を揃えると、新規性・破壊性・被引用とも中央付近',
    { text: '被引用の高さと破壊性の低さは、チーム規模と参考文献数の大きさによる', sub: true },
    { text: '組織間では、豊田中研・未来創成が珍しい組み合わせ寄り、AISIN IMRA が定石寄り', sub: true },
    { text: ['新規性の要因の検証：チーム規模・国際共同とも関係は見られず（件数が少ない）', `組織の差は残るが、説明できるのは約${r2org}%`] },
  ], { y: 1.35, h: 3.6, fs: 20, sp: 10, numbered: true });
  s.addText('今後：研究者ごとの論文の再収集について作業量を見積もり、hot streak の分析に進む',
    { x: MX, y: 5.2, w: CW, h: 0.45, fontFace: F, fontSize: 18, color: TEXT, valign: 'middle', margin: 0, isTextBox: true });
  notes(s, [
    'まとめです。',
    '一つめ、SciSciNet の新規性の値は、自前の計算と並び順がよく一致しましたので、分析に使っています。',
    '二つめ、条件を揃えると、トヨタの論文は新規性も破壊性も被引用も世の中の中央付近でした。被引用が高く破壊性が低く見えたのは、チームが大きく参考文献が多いことによるものです。組織では、豊田中研と未来創成が珍しい組み合わせを使う側、AISIN IMRA が定石を使う側でした。',
    '三つめ、チームの大きさと国際共同の効果は、件数が少なく確かめられませんでした。組織の差は残りますが、説明できる部分は小さいです。',
    '今後は、研究者ごとに論文を集め直す作業の手間を見積もり、hot streak の分析に進みます。以上です。',
  ]);
}

// ---------- 補足：チーム規模別の破壊性 ----------
{
  const s = slide('補足：チーム規模別の破壊性', '破壊性の順位の中央値（同じ分野・同じ年の一般論文との比較、50が中央）');
  const rows = [['チーム規模', '件数', '分野・年のみ', '＋参考文献数', '＋チーム規模', '＋両方']];
  for (const t of N.team_strata) rows.push([t.t, t.n, f1(t.fy), f1(t.ref), f1(t.team), f1(t.both)]);
  table(s, rows, { y: 1.75, colW: [2.4, 1.4, 2.08, 2.08, 2.08, CW - 10.04], rowH: 0.46 });
  bullets(s, [
    '分野と年のみ揃えると、チームが大きいほど破壊性が低い（Wu et al. 2019 と同じ傾向）',
    'チーム規模を揃えると、ほぼ平らになる',
    '参考文献数だけを揃えても、チーム規模による傾きは残る',
  ], { y: 4.35, h: 2.4, fs: 18, sp: 8 });
  notes(s, [
    '（質問が出たときに使う）チーム規模別に破壊性を見たものです。',
    '分野と年だけを揃えると、チームが大きいほど破壊性が低くなります。Wu らの報告と同じ傾向です。チーム規模を揃えると、ほぼ平らになります。',
    '参考文献数だけを揃えた場合は、全体の中央値は50前後になりますが、チーム規模による傾きは残ります。チーム規模と参考文献数は重なっていて、全体の水準についてはどちらか一方に帰すことはできません。',
  ]);
}

// pptxgenjs は、1つの段落に複数の文字列（太字の見出し語と本文、段落内の改行）を並べると、
// 段落の設定（<a:pPr>）を文字列ごとに書き出してしまう。段落の設定は先頭に1つだけという
// ファイル形式の決まりに反するので、書き出したあとで2つめ以降を取り除く。
const fs = require('fs');
const JSZip = require('jszip');
const dedupPPr = xml => xml.replace(/<a:p>[\s\S]*?<\/a:p>/g, p => {
  let seen = false;
  return p.replace(/<a:pPr\b[^>]*\/>|<a:pPr\b[^>]*>[\s\S]*?<\/a:pPr>/g, m => (seen ? '' : ((seen = true), m)));
});
pres.write({ outputType: 'nodebuffer' })
  .then(buf => JSZip.loadAsync(buf))
  .then(async zip => {
    for (const name of Object.keys(zip.files).filter(n => /^ppt\/(slides|notesSlides)\/[^/]+\.xml$/.test(n))) {
      zip.file(name, dedupPPr(await zip.file(name).async('string')));
    }
    fs.writeFileSync(OUT, await zip.generateAsync({ type: 'nodebuffer', compression: 'DEFLATE' }));
    console.log('written', OUT);
  });
