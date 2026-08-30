---
name: zt-biaoshu-skill
description: 中国政企招投标技术标（技术响应文件）全流程生成工具。从招标文件（PDF/Word）提取技术指标 → 编写总分结构响应 → 生成产品功能截图（HTML→1920×1080后台界面）→ docx 生成（指标批注、SEQ域图注、多级自动编号、指定格式规范）→ WPS渲染校验页数 → 批注一致性校验。适用：投标技术标、技术响应文件、偏离表、承诺函、设备技术+安全服务章节。触发词：标书、技术标、投标、技术响应、响应文件、偏离表、招标指标、批注、承诺函、产品功能截图。
---

# 技术标（投标技术响应文件）生成器

基于 docx-js 的中国政企招投标**技术标**自动化生产线。已在实际项目（网络入侵检测防御系统及安服项目投标）中验证：67~81 页、68 条指标批注、37 张产品功能截图、四级自动编号标题、SEQ 域图注、承诺函单页、批注一致性 68/68 通过。

## 适用场景

- 根据招标文件"评分标准"中的设备技术/技术方案/服务方案章节，编写技术标响应文件
- 生成"技术指标响应偏离表"（★/▲/一般逐条响应）
- 为每条重要指标（▲）提供产品功能截图（1920×1080 后台管理系统界面）
- 将招标原始指标以**批注**形式插入响应位置（供评审对照），响应采用"总体响应（总）+ 详细阐述（分）"结构
- 生成承诺函、证明材料说明等附件章节

## 前置依赖

| 依赖 | 用途 | 说明 |
|---|---|---|
| Node.js ≥ 20 | docx-js 构建 | 需能解析 ESM（自动检测） |
| Python 3.10+ | 数据处理/校验 | 需 `python`（非 Store 占位）；若 `python3` 指向 Windows Store stub，见下文 shim |
| kimi-docx skill | docx 构建与校验 | 使用其 `scripts/docx build`（含 lint/XSD/批注校验/自动修复） |
| WPS Office（Windows） | 渲染校验 | COM `KWPS.Application`，用于导出 PDF、统计页数、触发域更新 |
| Chrome/Edge | 截图 | headless 模式截取 1920×1080 产品功能截图 |

**python3 shim（仅 Windows 且 `python3` 是 Store stub 时）**：
```bash
mkdir -p ~/bin && printf '#!/usr/bin/env bash\nexec "%s" "$@"\n' "$(which python)" > ~/bin/python3 && chmod +x ~/bin/python3
export PATH="$HOME/bin:$PATH"
```

## 工作流总览

```
① 解析招标文件 → ② 编写指标响应数据 → ③ 生成功能截图 → ④ 编写/调整构建脚本
→ ⑤ docx 构建+校验 → ⑥ WPS 渲染检查 → ⑦ 批注/编号/颜色校验 → ⑧ 交付
```

### ① 解析招标文件，提取技术指标

1. 将招标 PDF 转文本（用 `pdf` skill 或 `pypdf`），保存为 `_pdf_text.txt`
2. 通读"四、技术指标 / 招标技术参数"部分，提取每条指标：
   - `num`：招标原编号（★1 / ▲2 / 3 …）
   - `attr`：★ / ▲ / 一般
   - `c1` / `c2`：一级分类 / 二级分类（用于章节分组）
   - `tender`：指标**完整原文**（含"提供产品功能截图证明并加盖投标单位公章"等证明材料要求，不得省略）
3. 注意：`tender` 字段是批注内容来源，**必须与招标原文逐字一致**（后续有自动校验）。含"、"引号的长文本在 Python 源码中用中文引号「"…"」或转义，避免破坏字符串字面量。

### ② 编写指标响应数据（总-分结构）

数据组织为 Python 模块（见 `templates/data/` 示例），每条指标含：
- `zong`：**总体响应**（功能概述段，1~2 句）—— 批注范围将框住此段
- `fen`：**详细阐述**（2~4 段列表）—— 分点展开功能实现方式、技术特点、满足情况
- `shot` / `caption`：▲指标的功能截图文件名与图注文字（无则 `None`）

章节结构（安全服务/技术方案类指标同理）：
```python
dict(
    num="▲2", attr="▲", c1="威胁检测能力", c2="通用攻击检测",
    tender="▲2.支持语义分析检测漏洞利用",
    zong="设备内置语义分析检测引擎，…总体响应…",
    fen=["（详细阐述第1段）…", "（详细阐述第2段）…"],
    shot="d01_semantic.png", caption="语义分析引擎检测漏洞利用功能界面",
)
```

合并为 `indicators.json`：
```bash
python scripts/build_indicators.py <工作目录>    # 读取 data/*.py → data/indicators.json
```

### ③ 生成产品功能截图（HTML → 1920×1080 PNG）

对每条 ▲ 指标生成一张"后台管理系统"功能截图：
1. 在 `mockgen/` 下按页面规格编写页面函数（复用 `base.py` 设计系统：深色侧栏+顶部栏+卡片+表格+SVG图表，参考 `templates/mockgen/pages_example.py`）
2. 渲染 HTML：
```bash
python scripts/gen_mockups.py <工作目录>          # 输出 mockgen/mockups/*.html
```
3. 溢出检查（内容必须恰好 1920×1080，不得裁剪）：
```bash
python scripts/qa_overflow.py <工作目录>          # 报告 docH/bodyW 溢出页
```
4. 批量截图：
```bash
python scripts/screenshot_all.py <工作目录>       # Chrome headless → shots/*.png (1920×1080)
```
质量要求：文字清晰不重叠、字体 ≥12px、统一企业级风格、恰好占满视口（`html,body{width:1920px;height:1080px;overflow:hidden}`）。

### ④ 编写/调整 docx 构建脚本

复制 `templates/docx_helpers.js` 与 `templates/build.js` 到工作目录，按项目调整：
- `build.js` 顶部：`BASE`（工作目录）、`SHOTS`、`DATA`（indicators.json）
- 章节结构函数（`chapter1Children` / `chapter2Children`）：按 c1/c2 分组渲染指标响应
- 承诺函（`promiseBlock`）、证明材料说明表、渗透测试成果等章节内容
- 封面/页眉/落款信息（投标人名称、日期）

**构建命令**（kimi-docx 的 build 封装：node --check → lint → 生成 → 自动修复+校验）：
```bash
export PATH="$HOME/bin:$PATH"
/path/to/kimi-docx/scripts/docx build build.js 输出.docx
```

### ⑤ 构建校验

`docx build` 内置校验（XSD/批注/图片/编号）。构建通过后确认：
- `✓ Done:` 无 `Error:` 行（`Error:` 是阻断项）
- 批注数量 = 指标数量

### ⑥ WPS 渲染检查（页数/版面/域更新）

```bash
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/wps_render.ps1 \
  -InFile <绝对路径/输出.docx> -OutPdf <绝对路径/检查.pdf>
```
输出 `PAGES=N`（N>50 为常见要求）与 `PDF_OK`。用 pypdf 抽查 PDF 文本：
- 标题编号（1 / 1.1 / 1.3.1 / 1.3.1.1）、图注（图1~图N）、目录页码已更新
- 无"…"残留（若偏离表要求完整指标）、无标记残留（若要求去除【总体响应】（分））

### ⑦ 自动校验

```bash
python scripts/verify_comments.py <工作目录> <输出.docx>     # 批注 vs 指标 逐字一致性（含XML反转义）
python scripts/check_black.py <工作目录> <输出.docx>          # 全文纯黑检查（可选）
```
另校验：批注范围包裹总体响应段（`commentRangeStart..commentRangeEnd` 内含【总体响应】/对应总段文本）、图片数 = 截图数、图注连续。

### ⑧ 交付

- 输出文件名：`<采购单位>_技术标_<内容>_<日期>.docx`
- 保留工作目录（数据/截图/脚本），便于评审反馈后快速重生成

## 关键实现要点（踩坑记录）

### docx-js 多级自动编号（重要！）
`numbering` 的 `text` 中 `%N` 引用**第 N 级计数器**（1-based）。同级的正确写法：
```js
{ level: 0, format: LevelFormat.DECIMAL, text: "%1",    start: 1 },   // 1
{ level: 1, format: LevelFormat.DECIMAL, text: "%1.%2", start: 1 },   // 1.1
{ level: 2, format: LevelFormat.DECIMAL, text: "%1.%2.%3", start: 1 },// 1.3.1
{ level: 3, format: LevelFormat.DECIMAL, text: "%1.%2.%3.%4", start: 1 },
```
若全部写成 `%1`，Word/WPS 中同级标题不递增（都会引用第1级计数器）。中文编号同理：level1 用 `%2、`、level2 用 `（%3）`。

### docx-js 批注
- `Document({ comments: { children: [{ id, author, children: [Paragraph…] }] } })`：children 传**普通对象**，不是 `new Comment()`
- 段落内：`CommentRangeStart(id)` + runs + `CommentRangeEnd(id)` + **`TextRun({children:[new CommentReference(id)]})`**（commentReference 必须包在 w:r 内，否则 XSD 校验报错）

### 图片与图注
- 图片：`ImageRun({type:"png", data: fs.readFileSync(path), transformation:{width:596,height:335}})`（A4 可用宽约 16cm ≈ 596px@96dpi，保持 16:9）
- 图注：`run("图") + new SequentialIdentifier("图") + run(" 标题")` → SEQ 域自动编号，配 `features:{updateFields:true}` 让打开时自动更新

### WPS 渲染注意
- WPS COM：`KWPS.Application`；`doc.ComputeStatistics(2)` 统计页数；`doc.ExportAsFixedFormat(path,17)` 导出 PDF
- 打开文档后先 `doc.Fields.Update()` 更新 SEQ/TOC，再导出

### 数据/脚本常见坑
- Python 源码含中文引号「"…"」时勿用 ASCII `"` 包裹，用单引号或 `"…"`（U+201C/D）
- 批注文本含 `&`（如 ATT&CK）时 XML 自动转义，校验需 `html.unescape`
- 承诺函等需"单独一页"的内容：段落前加 `new Paragraph({children:[new PageBreak()]})`

## 目录结构

```
zt-biaoshu-skill/
├── SKILL.md                  # 本文件
├── scripts/
│   ├── build_indicators.py   # data/*.py → indicators.json
│   ├── gen_mockups.py        # mockgen 页面 → HTML
│   ├── qa_overflow.py        # HTML 1920×1080 溢出检查（CDP）
│   ├── screenshot_all.py     # Chrome headless 批量截图
│   ├── wps_render.ps1        # WPS 渲染 PDF + 页数统计
│   ├── verify_comments.py    # 批注 vs 指标一致性校验
│   └── check_black.py        # 全文纯黑检查（可选）
├── templates/
│   ├── docx_helpers.js       # docx 辅助（标题/正文/批注/图注/表格/样式）
│   ├── build.js              # 主构建脚本模板（含承诺函、证明材料表）
│   ├── data/                 # 指标数据示例（dev_part1.py、svc.py）
│   └── mockgen/              # 截图设计系统（base.py）与页面示例
└── references/
    └── FORMAT_SPEC.md        # 默认格式规范（标题/正文/图注）
```

## 模板使用说明

- `templates/docx_helpers.js`：**直接复制使用**，已封装全部格式规范与批注/图注/编号逻辑
- `templates/build.js`：复制后改章节内容。章节数据驱动部分（从 indicators.json 按 c1/c2 分组渲染）已通用化，项目特有文字（封面、承诺函、渗透成果、证明材料表）按注释位置替换
- `templates/data/*.py`：指标数据格式参考（项目专用数据放工作目录 `data/`）
- `templates/mockgen/base.py`：截图设计系统（CSS+SVG 图表+导航），直接复制；页面规格按项目在 `pages*.py` 中编写

## 格式规范（默认，见 references/FORMAT_SPEC.md）

- 一级标题：等线/黑体 16pt 粗黑 段前17pt 段后16.5pt 行距2.41倍
- 二级/三级：等线Light/黑体 14pt 粗黑 段前13pt 段后13pt 行距1.73倍
- 四级：等线Light/黑体 14pt 粗黑 段前14pt 段后14.5pt 行距1.57倍
- 正文（0-正文样式）：Times New Roman/幼圆 14pt 两端对齐 首行缩进2字符 行距1.25倍
- 图片（0-图格式）：居中 Times New Roman 12pt
- 图下标题（0-图下标题）：Times New Roman/幼圆 14pt 黑 "图1 标题"
- 全文纯黑（无蓝色字体）；标题自动编号（1 / 1.1 / 1.3.1 / 1.3.1.1）
