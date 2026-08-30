// docx 生成辅助模块 —— 格式规范 v2
// 一级标题 Heading1：西文等线/中文黑体 16pt 粗 黑 段前17pt 段后16.5pt 行距2.41倍
// 二级标题 Heading2：西文等线Light/中文黑体 14pt 粗 黑 段前13pt 段后13pt 行距1.73倍
// 三级标题 Heading3：西文等线Light/中文黑体 14pt 粗 黑 段前13pt 段后13pt
// 四级标题 Heading4：西文等线Light/中文黑体 14pt 粗 黑 段前14pt 段后14.5pt 行距1.57倍
// 正文 0-正文：西文Times New Roman/中文幼圆 14pt 两端对齐 首行缩进2字符 行距1.25倍
// 图片 0-图格式：居中 Times New Roman 12pt
// 图下标题 0-图下标题：西文Times New Roman/中文幼圆 14pt 黑 示例"图1 设备功能模块组成图"
import {
  AlignmentType, HeadingLevel, LevelFormat, PageNumber, Paragraph, TextRun,
  Table, TableRow, TableCell, WidthType, ShadingType, VerticalAlign, LineRuleType,
  CommentRangeStart, CommentRangeEnd, CommentReference, SequentialIdentifier,
  ImageRun, convertInchesToTwip,
} from "docx";

// ---------- 字体 ----------
export const FONT_BODY = { ascii: "Times New Roman", hAnsi: "Times New Roman", cs: "Times New Roman", eastAsia: "幼圆" };
export const FONT_H1 = { ascii: "DengXian", hAnsi: "DengXian", cs: "DengXian", eastAsia: "SimHei" };
export const FONT_H24 = { ascii: "DengXian Light", hAnsi: "DengXian Light", cs: "DengXian Light", eastAsia: "SimHei" };
export const FONT_CAP = { ascii: "Times New Roman", hAnsi: "Times New Roman", cs: "Times New Roman", eastAsia: "幼圆" };

export const STYLE_BODY = "0-正文";
export const STYLE_FIG = "0-图格式";
export const STYLE_CAPTION = "0-图下标题";

export function run(text, options = {}) {
  return new TextRun({ text, font: FONT_BODY, size: 28, ...options });
}

// 正文段落（0-正文：两端对齐、首行缩进2字符、行距1.25倍、14pt 幼圆/Times New Roman）
export function bodyPara(text, options = {}) {
  return new Paragraph({
    style: STYLE_BODY,
    alignment: AlignmentType.JUSTIFIED,
    spacing: { after: 0, line: 300, lineRule: LineRuleType.AUTO },
    indent: { firstLineChars: 200 },
    ...options,
    children: Array.isArray(text) ? text : [run(text)],
  });
}

// 无缩进正文（仍为 0-正文 格式）
export function plainPara(text, options = {}) {
  return new Paragraph({
    style: STYLE_BODY,
    alignment: AlignmentType.JUSTIFIED,
    spacing: { after: 0, line: 300, lineRule: LineRuleType.AUTO },
    ...options,
    children: Array.isArray(text) ? text : [run(text)],
  });
}

// 居中段落（页眉页脚等）
export function centerPara(children, options = {}) {
  return new Paragraph({
    alignment: AlignmentType.CENTER,
    spacing: { after: 120, line: 340 },
    ...options,
    children: Array.isArray(children) ? children : [children],
  });
}

// ---------- 标题（自动编号通过 numbering 附加；格式按用户规范） ----------
export function h1(text) {
  return new Paragraph({
    heading: HeadingLevel.HEADING_1,
    numbering: { reference: "hd", level: 0 },
    alignment: AlignmentType.CENTER,
    spacing: { before: 340, after: 330, line: 578, lineRule: LineRuleType.AUTO }, // 17pt/16.5pt/2.41倍
    children: [new TextRun({ text, font: FONT_H1, bold: true, size: 32, color: "000000" })],
  });
}
export function h2(text) {
  return new Paragraph({
    heading: HeadingLevel.HEADING_2,
    numbering: { reference: "hd", level: 1 },
    spacing: { before: 260, after: 260, line: 415, lineRule: LineRuleType.AUTO }, // 13pt/13pt/1.73倍
    children: [new TextRun({ text, font: FONT_H24, bold: true, size: 28, color: "000000" })],
  });
}
export function h3(text) {
  return new Paragraph({
    heading: HeadingLevel.HEADING_3,
    numbering: { reference: "hd", level: 2 },
    spacing: { before: 260, after: 260, line: 415, lineRule: LineRuleType.AUTO },
    children: [new TextRun({ text, font: FONT_H24, bold: true, size: 28, color: "000000" })],
  });
}
export function h4(text) {
  return new Paragraph({
    heading: HeadingLevel.HEADING_4,
    numbering: { reference: "hd", level: 3 },
    spacing: { before: 280, after: 290, line: 377, lineRule: LineRuleType.AUTO }, // 14pt/14.5pt/1.57倍
    children: [new TextRun({ text, font: FONT_H24, bold: true, size: 28, color: "000000" })],
  });
}

// ---------- 指标标签段（加粗，浅灰底纹，正文格式） ----------
export function indicatorLabel(text) {
  return new Paragraph({
    style: STYLE_BODY,
    spacing: { before: 160, after: 80, line: 300, lineRule: LineRuleType.AUTO },
    shading: { type: ShadingType.CLEAR, fill: "F2F2F2" },
    children: [run("◆ ", { bold: true, color: "000000" }), run(text, { bold: true, color: "000000" })],
  });
}

// ---------- 总响应段（批注包裹；正文格式，无标识前缀） ----------
export function zongPara(id, text) {
  return new Paragraph({
    style: STYLE_BODY,
    alignment: AlignmentType.JUSTIFIED,
    spacing: { after: 0, line: 300, lineRule: LineRuleType.AUTO },
    indent: { firstLineChars: 200 },
    children: [
      new CommentRangeStart(id),
      run(text),
      new CommentRangeEnd(id),
      new TextRun({ children: [new CommentReference(id)], font: FONT_BODY, size: 28 }),
    ],
  });
}

// ---------- 分响应段（正文格式，无标识前缀） ----------
export function fenPara(text) {
  return new Paragraph({
    style: STYLE_BODY,
    alignment: AlignmentType.JUSTIFIED,
    spacing: { after: 0, line: 300, lineRule: LineRuleType.AUTO },
    indent: { firstLineChars: 200 },
    children: [run(text)],
  });
}

// ---------- 图片（0-图格式：居中） + SEQ 图注（0-图下标题） ----------
export function figPara(imagePath, caption, widthPx = 596) {
  const heightPx = Math.round(widthPx * 9 / 16);
  return [
    new Paragraph({
      style: STYLE_FIG,
      alignment: AlignmentType.CENTER,
      spacing: { before: 120, after: 60, line: 300 },
      children: [new ImageRun({
        type: "png",
        data: imagePath,
        transformation: { width: widthPx, height: heightPx },
      })],
    }),
    new Paragraph({
      style: STYLE_CAPTION,
      alignment: AlignmentType.CENTER,
      spacing: { after: 200, line: 300 },
      children: [
        new TextRun({ text: "图", font: FONT_CAP, size: 28, color: "000000" }),
        new SequentialIdentifier("图"),
        new TextRun({ text: " " + caption, font: FONT_CAP, size: 28, color: "000000" }),
      ],
    }),
  ];
}

// ---------- 表格 ----------
export function makeTable(headers, rows, opts = {}) {
  const widths = opts.widths || headers.map(() => 1000);
  const headerRow = new TableRow({
    tableHeader: true,
    children: headers.map((h, i) =>
      new TableCell({
        shading: { type: ShadingType.CLEAR, fill: "E8E8E8" },
        verticalAlign: VerticalAlign.CENTER,
        margins: { top: 80, bottom: 80, left: 100, right: 100 },
        width: { size: widths[i], type: WidthType.DXA },
        children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [run(h, { bold: true, size: 21 })] })],
      })),
  });
  const bodyRows = rows.map((cells) =>
    new TableRow({
      children: cells.map((c, i) =>
        new TableCell({
          verticalAlign: VerticalAlign.CENTER,
          margins: { top: 60, bottom: 60, left: 100, right: 100 },
          width: { size: widths[i], type: WidthType.DXA },
          children: Array.isArray(c)
            ? c
            : [new Paragraph({ spacing: { line: 300 }, children: [run(String(c), { size: 21 })] })],
        })),
    }));
  return new Table({
    width: { size: 100, type: WidthType.PERCENTAGE },
    columnWidths: widths,
    rows: [headerRow, ...bodyRows],
  });
}

// 表格后的空行
export function tableGap() {
  return new Paragraph({ spacing: { after: 120 }, children: [] });
}

// ---------- 批注内容 ----------
export function commentContent(tenderText) {
  const lines = String(tenderText).split("\n").filter((l) => l.trim());
  return lines.map((l) =>
    new Paragraph({
      spacing: { after: 60, line: 300 },
      indent: { left: 240 },
      children: [run(l, { size: 21 })],
    }));
}
