/**
 * 投标文件风险审查报告 —— Word 格式套件
 *
 * 这里是"格式"的唯一真源（single source of truth）：字体、字号、缩进、
 * 行距、表格底纹、页眉页脚、目录域全部集中在 TOKENS 与 makeKit() 里。
 * 改版式只改这个文件，不动 build.js，也不要在报告 JSON 里写样式。
 *
 * 配套文档：references/report-docx-format.md
 */
import { loadDocx } from "./load_docx.js";

/** A4（11906 twip 宽）＋ 上下左右各 2.54cm（1440 twip）页边距 */
export const PAGE = {
  width: 11906,
  height: 16838,
  margin: { top: 1440, bottom: 1440, left: 1440, right: 1440 },
  /** 版心宽度 = 11906 − 1440×2，表格列宽按此归一化 */
  contentWidth: 9026,
};

export const FONTS = {
  body: {
    ascii: "Times New Roman",
    hAnsi: "Times New Roman",
    cs: "Times New Roman",
    eastAsia: "SimSun",
  },
  head: {
    ascii: "Times New Roman",
    hAnsi: "Times New Roman",
    cs: "Times New Roman",
    eastAsia: "SimHei",
  },
};

/** 字号单位为半磅（half-point）：24 = 小四 12pt */
export const SIZES = {
  title: 40,
  subtitle: 26,
  h1: 30,
  h2: 26,
  body: 24,
  table: 21,
  note: 20,
};

/** 色板：深墨蓝做标题、海蓝做强调与页眉、浅蓝做表头、陶土色标记风险行 */
export const COLORS = {
  dark: "23343F",
  primary: "3C5865",
  light: "7E949E",
  border: "D3DDE1",
  fill: "EDF3F6",
  fillWarn: "FBEFE9",
  fillHigh: "F7E4DC",
  quote: "F4F7F8",
  white: "FFFFFF",
};

export const INDENT = {
  firstLine: 480,
  body: 0,
  list: 360,
  bullet: 360,
  quoteLeft: 480,
  quoteRight: 360,
};

export const SPACING = {
  body: { after: 140, line: 320 },
  bullet: { after: 100, line: 320 },
  numbered: { after: 120, line: 320 },
  h1: { before: 320, after: 160 },
  h2: { before: 240, after: 120 },
  cell: { after: 60, line: 280 },
  lead: { before: 160, after: 100 },
};

const xmlEscape = (value) =>
  String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");

/** 归一化列宽：按权重分配版心宽度，保证表格永远是 100% 且不溢出 */
const normalizeWidths = (widths, count) => {
  const weights =
    Array.isArray(widths) && widths.length === count
      ? widths.map((value) => Number(value) || 1)
      : Array.from({ length: count }, () => 1);
  const total = weights.reduce((sum, value) => sum + value, 0);
  return weights.map((value) => Math.round((value / total) * PAGE.contentWidth));
};

export function makeKit(docx) {
  const {
    AlignmentType,
    Document,
    Footer,
    Header,
    HeadingLevel,
    ImportedXmlComponent,
    Packer,
    PageNumber,
    Paragraph,
    ShadingType,
    Table,
    TableCell,
    TableRow,
    TextRun,
    WidthType,
  } = docx;

  const text = (value, options = {}) =>
    new TextRun({ text: String(value), font: FONTS.body, size: SIZES.body, ...options });

  const head = (value, options = {}) =>
    new TextRun({
      text: String(value),
      font: FONTS.head,
      size: SIZES.body,
      bold: true,
      color: COLORS.dark,
      ...options,
    });

  const para = (children, options = {}) =>
    new Paragraph({
      spacing: SPACING.body,
      ...options,
      children: Array.isArray(children) ? children : [children],
    });

  /** 正文段落（首行缩进 2 字符） */
  const p = (value, { indent = true, ...options } = {}) =>
    para(text(value), {
      indent: indent ? { firstLine: INDENT.firstLine } : undefined,
      ...options,
    });

  /** 引导词段落：加粗黑体标签 + 正文，如「位置：…」「原文：…」 */
  const lead = (label, value) =>
    para([head(label, { size: SIZES.body }), text(value)]);

  /** 圆点列表 */
  const bullet = (value, options = {}) =>
    para([text("● ", { color: COLORS.primary }), text(value)], {
      indent: { left: INDENT.bullet },
      spacing: SPACING.bullet,
      ...options,
    });

  /** 编号清单（悬挂缩进，序号自动生成） */
  const numbered = (value, index) =>
    para([head(`${index + 1}.`), text(`　${value}`)], {
      indent: { left: INDENT.list, hanging: INDENT.list },
      spacing: SPACING.numbered,
    });

  /** 原文引用块：浅灰底纹 + 左右缩进，用于引招标条款与投标原文 */
  const quote = (value) =>
    para(text(value, { color: COLORS.dark }), {
      indent: { left: INDENT.quoteLeft, right: INDENT.quoteRight },
      shading: { type: ShadingType.CLEAR, fill: COLORS.quote },
      spacing: { after: 140, line: 320, before: 60 },
    });

  /** 脚注式小字（斜体浅灰），用于口径说明与免责声明 */
  const note = (value) =>
    para(text(value, { italics: true, color: COLORS.light, size: SIZES.note }), {
      spacing: { before: 240, after: 140, line: 300 },
    });

  const h1 = (value) =>
    para(head(value, { size: SIZES.h1 }), {
      heading: HeadingLevel.HEADING_1,
      spacing: SPACING.h1,
      keepNext: true,
    });

  const h2 = (value) =>
    para(head(value, { size: SIZES.h2 }), {
      heading: HeadingLevel.HEADING_2,
      spacing: SPACING.h2,
      keepNext: true,
    });

  const cell = (value, options = {}) => {
    const lines = String(value ?? "").split("\n");
    return new TableCell({
      children: lines.map((line, index) =>
        para(text(line, { size: SIZES.table }), {
          spacing: { after: index === lines.length - 1 ? 0 : SPACING.cell.after, line: SPACING.cell.line },
        }),
      ),
      margins: { top: 100, bottom: 100, left: 120, right: 120 },
      ...options,
    });
  };

  /**
   * 表格。
   * @param {object} spec
   * @param {string[]} spec.head         表头文字
   * @param {string[][]} spec.rows       数据行（单元格内 \n 会拆成多段）
   * @param {number[]} [spec.widths]     列宽权重（内部归一化到版心宽度）
   * @param {number[]} [spec.highlight]  需要标红的风险行下标（0 基）
   * @param {string} [spec.caption]      表题（表格上方居中）
   */
  const table = ({ head: headerRow, rows = [], widths, highlight = [], caption }) => {
    const count = (headerRow || rows[0] || []).length;
    const columnWidths = normalizeWidths(widths, count);
    const border = { style: "single", size: 4, color: COLORS.border };
    const tbl = new Table({
      width: { size: 100, type: WidthType.PERCENTAGE },
      columnWidths,
      borders: {
        top: border,
        bottom: border,
        left: border,
        right: border,
        insideHorizontal: border,
        insideVertical: border,
      },
      rows: [
        new TableRow({
          tableHeader: true,
          children: (headerRow || []).map((label, index) =>
            cell(label, {
              shading: { type: ShadingType.CLEAR, fill: COLORS.fill },
              width: { size: columnWidths[index], type: WidthType.DXA },
              children: [
                para(head(label, { size: SIZES.table }), {
                  spacing: { after: 0, line: SPACING.cell.line },
                }),
              ],
            }),
          ),
        }),
        ...rows.map(
          (row, rowIndex) =>
            new TableRow({
              cantSplit: true,
              children: row.map((value, index) =>
                cell(value, {
                  width: { size: columnWidths[index], type: WidthType.DXA },
                  shading: highlight.includes(rowIndex)
                    ? { type: ShadingType.CLEAR, fill: COLORS.fillHigh }
                    : undefined,
                }),
              ),
            }),
        ),
      ],
    });

    if (!caption) return [tbl];
    return [
      para(text(caption, { size: SIZES.note, bold: false, color: COLORS.primary }), {
        alignment: AlignmentType.CENTER,
        spacing: { before: 120, after: 80, line: 280 },
        keepNext: true,
      }),
      tbl,
      para(text(""), { spacing: { after: 60 } }),
    ];
  };

  /**
   * Word 原生目录域（TOC）＋ 缓存条目。
   * 打开文档后目录会按 updateFields 提示更新；缓存条目保证未更新时不空白。
   */
  const tocField = (entries = []) => {
    const cached = entries
      .map(({ title, level = 1, page = "" }) => {
        const indent = Math.max(0, Number(level) - 1) * 360;
        return `<w:p>
          <w:pPr>
            <w:pStyle w:val="TOC${Number(level)}"/>
            <w:tabs><w:tab w:val="right" w:leader="dot" w:pos="9000"/></w:tabs>
            <w:ind w:left="${indent}"/>
          </w:pPr>
          <w:r><w:t xml:space="preserve">${xmlEscape(title)}</w:t></w:r>
          <w:r><w:tab/></w:r>
          <w:r><w:t>${xmlEscape(page)}</w:t></w:r>
        </w:p>`;
      })
      .join("");

    const xml = `<w:sdt xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
      <w:sdtPr><w:alias w:val="目录"/><w:docPartObj><w:docPartGallery w:val="Table of Contents"/><w:docPartUnique/></w:docPartObj></w:sdtPr>
      <w:sdtContent>
        <w:p>
          <w:r>
            <w:fldChar w:fldCharType="begin" w:dirty="true"/>
            <w:instrText xml:space="preserve"> TOC \\o &quot;1-3&quot; \\h \\z \\u </w:instrText>
            <w:fldChar w:fldCharType="separate"/>
          </w:r>
        </w:p>
        ${cached}
        <w:p><w:r><w:fldChar w:fldCharType="end"/></w:r></w:p>
      </w:sdtContent>
    </w:sdt>`;

    return ImportedXmlComponent.fromXmlString(xml).root[0];
  };

  /** 从 h1/h2 自动生成目录条目（页码留空，更新域后填充） */
  const tocFromSections = (blocks) =>
    blocks
      .filter((block) => block.h1 || block.h2)
      .map((block) =>
        block.h1
          ? { title: block.h1, level: 1, page: "" }
          : { title: block.h2, level: 2, page: "" },
      );

  /** 页脚居中页码（PageNumber.CURRENT 是 docx 的域占位常量，不是构造函数） */
  const pageNumber = () =>
    para(new TextRun({ children: [PageNumber.CURRENT], font: FONTS.body, size: SIZES.note }), {
      alignment: AlignmentType.CENTER,
    });

  /** 分页符 */
  const pageBreak = () => new Paragraph({ children: [], pageBreakBefore: true });

  return {
    AlignmentType,
    Document,
    Footer,
    Header,
    HeadingLevel,
    Packer,
    Paragraph,
    Table,
    TableRow,
    cell,
    bullet,
    head,
    h1,
    h2,
    lead,
    note,
    numbered,
    p,
    pageBreak,
    pageNumber,
    para,
    quote,
    table,
    text,
    tocField,
    tocFromSections,
  };
}

/** 把一段块描述渲染成 docx 子元素数组 */
export function renderBlocks(blocks, kit) {
  const children = [];

  for (const block of blocks || []) {
    if (block.h1 !== undefined) children.push(kit.h1(block.h1));
    if (block.h2 !== undefined) children.push(kit.h2(block.h2));
    if (block.p !== undefined) children.push(kit.p(block.p, { indent: block.indent !== false }));
    if (block.lead) children.push(kit.lead(block.lead[0], block.lead[1]));
    if (block.quote !== undefined) {
      const items = Array.isArray(block.quote) ? block.quote : [block.quote];
      items.forEach((item) => children.push(kit.quote(item)));
    }
    if (block.bullets) block.bullets.forEach((item) => children.push(kit.bullet(item)));
    if (block.list) block.list.forEach((item, index) => children.push(kit.numbered(item, index)));
    if (block.note !== undefined) children.push(kit.note(block.note));
    if (block.table) children.push(...kit.table(block.table));
    if (block.pageBreak) children.push(kit.pageBreak());
  }

  return children;
}

/** 报告 JSON → Document */
export function buildDocument(report, kit) {
  const { Document, Footer, Header, AlignmentType, PageNumber, Table, TableRow } = kit;
  const blocks = report.sections || [];
  const children = [];

  // ── 封面 ──
  if (report.title) {
    children.push(
      kit.para(kit.head(report.title, { size: SIZES.title, color: COLORS.dark }), {
        heading: kit.HeadingLevel.TITLE,
        alignment: AlignmentType.CENTER,
        spacing: { before: report.subtitle ? 900 : 1000, after: 240 },
      }),
    );
  }
  if (report.subtitle) {
    children.push(
      kit.para(kit.text(report.subtitle, { size: SIZES.subtitle, color: COLORS.primary }), {
        alignment: AlignmentType.CENTER,
        spacing: { after: 720 },
      }),
    );
  }
  if (report.meta && report.meta.rows) {
    children.push(
      ...kit.table({
        head: report.meta.head || ["项目", "内容"],
        rows: report.meta.rows,
        widths: report.meta.widths || [24, 76],
      }),
    );
  }

  // ── 目录 ──
  if (report.toc) {
    const entries = Array.isArray(report.toc) ? report.toc : kit.tocFromSections(blocks);
    children.push(
      kit.para(kit.head("目录", { size: SIZES.h1 }), {
        spacing: { before: 720, after: 120 },
        keepNext: true,
      }),
    );
    if (report.tocNote !== false) {
      children.push(
        kit.note(
          report.tocNote ||
            "（页码为估算值，可在 Word/WPS 中右键目录选择「更新域」刷新）",
        ),
      );
    }
    children.push(kit.tocField(entries));
  }

  // ── 正文 ──
  children.push(...renderBlocks(blocks, kit));

  const headerText = report.header || report.title || "投标文件风险审查报告";

  return new Document({
    features: { updateFields: true },
    sections: [
      {
        properties: { page: { size: { width: PAGE.width, height: PAGE.height }, margin: PAGE.margin } },
        headers: {
          default: new Header({
            children: [
              kit.para(kit.text(headerText, { bold: true, color: COLORS.primary, size: SIZES.note }), {
                alignment: AlignmentType.CENTER,
              }),
            ],
          }),
        },
        footers: { default: new Footer({ children: [kit.pageNumber()] }) },
        children,
      },
    ],
  });
}

/** 报告 JSON → docx 文件 */
export async function writeReport(report, outputPath) {
  const docx = await loadDocx();
  const kit = makeKit(docx);
  const doc = buildDocument(report, kit);
  const buffer = await docx.Packer.toBuffer(doc);
  const fs = await import("node:fs");
  fs.writeFileSync(outputPath, buffer);
  return outputPath;
}
