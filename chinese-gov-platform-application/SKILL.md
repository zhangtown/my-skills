---
name: chinese-gov-platform-application
managed: true
description: Fill Chinese government innovation platform application documents (e.g., 产业技术工程化中心、重点实验室、工程研究中心) from source materials and templates. Use when the user asks to fill highlighted sections in a DOCX application template, write an application report from company materials, or prepare government platform申报材料.
---

# Chinese Government Innovation Platform Application Document Preparation

Use this skill when the user needs to fill out Chinese government application documents for R&D platforms, innovation centers, key laboratories, engineering centers, or similar technology/innovation platform recognition programs (政府科技/创新平台申报，如产业技术工程化中心、重点实验室、工程研究中心、企业技术中心、专精特新等申报). Also use when the user mentions "申报", "申请报告", "填写标黄章节", "填写模板", "申请报告大纲", "工程化中心", "重点实验室", or provides a DOCX template with highlighted/blank sections alongside source company materials.

This skill is distinct from `bid-proposal` (which covers procurement/tender bidding 投标/标书) and `report-writing` (which covers general reports). It specifically handles the workflow of:
- Analyzing source company materials (investment reports, company profiles, technical documents)
- Reading government application notifications/requirements (PDFs)
- Filling highlighted/blank sections in a formal application template DOCX
- Generating polished, formal Chinese government application prose
- Ensuring no cross-contamination from unrelated source materials
- Formatting output with proper Word heading styles and TOC structure

## Trigger Conditions

Use this skill when the user asks to:
- Fill in a government application/report template DOCX (especially with highlighted sections)
- Analyze company source documents and write application content
- Draft a center/lab/platform application summary or specific chapters
- Prepare materials for government innovation platform applications (工程化中心、重点实验室、工程研究中心、企业技术中心、院士工作站、博士后工作站、新型研发机构等)
- Combine multiple source documents into a single application output
- Polish or rewrite application content to remove AI artifacts while preserving data accuracy

## Workflow

### Phase 1: Discovery and Material Analysis
1. **List all files** in the workspace/directory to identify:
   - Source company materials (DOCX/PDF): investment reports, company profiles, technical summaries, financial reports, patent lists, etc.
   - Application template (DOCX): the document with sections to fill, often marked with yellow highlighting or left blank
   - Government notification/requirements (PDF): official application guidelines, qualification criteria, formatting requirements
2. **Read and analyze** all source materials using Python (python-docx, pdfminer) to extract full text. Do not rely on Read tool for binary DOCX/PDF files.
3. **Identify the application type** (e.g., 产业技术工程化中心, 重点实验室, 工程研究中心) to understand the tone and required content depth.
4. **Build a source material inventory** — catalog key data points from each source: company founding date, revenue, R&D investment, patents, core technologies, team size, qualifications, etc.

### Phase 2: Template Parsing and Section Mapping
1. **Parse the template DOCX** to identify all paragraphs and their formatting.
2. **Locate sections requiring content** — typically:
   - Yellow-highlighted paragraphs (标黄章节)
   - Blank sections after headings
   - Sections with placeholder text like "包括但不限于..."
3. **Map each blank section** to the appropriate source material(s). For example:
   - Company overview → investment report / company profile
   - Technical achievements → patent list / product descriptions
   - Market analysis → industry research / investment report
4. **Verify no cross-contamination risk**: If a template was previously used for a different applicant (e.g., contains content from another university/company), explicitly check and confirm the output does NOT contain content from the wrong source.

### Phase 3: Content Generation
1. **Draft each section** in formal Chinese government application style:
   - Use 第三人称客观陈述 (third-person objective narration)
   - Incorporate specific data: revenue figures, patent counts, team sizes, qualification certificates
   - Reference national/provincial policies (e.g., 十五五规划, 党的二十大报告, 省/市产业政策) where relevant
   - Maintain consistent terminology throughout (e.g., if the company is called "博智安全" in sources, do not introduce new names)
2. **Match the required tone and depth** for each section type:
   - **摘要 (Abstract)**: ~1000 words, comprehensive overview covering company background, technology, market position, financials, and application purpose
   - **建设背景及必要性**: Policy context, industry chain analysis, market trends, technical gaps, necessity justification
   - **依托单位概况**: Company registration, equity structure, R&D capabilities, team composition, qualifications
   - **主要任务与目标**: R&D directions, specific tasks, strategic planning, short/medium/long-term goals with quantifiable metrics
   - **总投资与建设内容**: Investment breakdown, facility plans, equipment procurement, talent recruitment, R&D schedule
   - **管理与运行机制**: Organizational structure, talent team, operation mechanisms, IP management
3. **Deep polish (深度润色)** when requested:
   - Remove AI template phrases: "值得注意的是", "不难发现", "综上所述", "深入剖析", "从这个角度来看"
   - Remove redundant parenthetical explanations and bracketed asides
   - Remove mechanical enumeration markers ("第一/第二/第三") where they feel artificial; use natural paragraph transitions
   - Eliminate repetitive closing sentences that appear at the end of every subsection
   - Preserve all core data points exactly as they appear in sources
   - Maintain formal but direct prose — avoid overly flowery or promotional language

### Phase 4: DOCX Assembly and Formatting
1. **Insert content into the template** by paragraph index or by matching heading text. Use python-docx.
2. **Preserve original formatting** where required (fonts, spacing, indentation). Replace placeholder text with generated content.
3. **Set heading styles** for TOC generation:
   - Major sections (一、二、三...) → Heading 2
   - Sub-sections (（一）（二）...) → Heading 3
   - Sub-sub-sections (1. 2. 3.) → Heading 4
4. **Save as a new file** (never overwrite the original template). Use a naming convention like `原文件名-已填写.docx` or `原文件名-深度润色版-定稿.docx`.
5. **Validate the output**:
   - Count paragraphs and verify all highlighted sections were filled
   - Spot-check that key data from sources appears correctly
   - Verify no content from wrong/unrelated sources leaked in
   - Check heading style consistency

### Phase 5: Delivery and Revision
1. **Deliver the completed file** with a summary of what was filled and any placeholder data that still needs user input (e.g., specific addresses, exact equipment model numbers, personnel names).
2. **Highlight remaining placeholders** clearly so the user knows what to verify or replace manually.
3. **If the user requests style changes** (e.g., "小标题也设置一下目录级别"), apply Word heading styles and regenerate the file.

## Common Pitfalls

- **WD_COLOR_INDEX error**: When detecting highlighted text in python-docx, `run.font.highlight_color` may throw `WD_COLOR_INDEX has no XML mapping for 'none'`. Use a try-except wrapper around highlight detection.
- **Merged cell tables**: If the template contains complex merged-cell tables, `python-docx` may fail with `no 'tc' element at grid_offset`. Skip table-heavy pages or use alternative parsing strategies.
- **Permission denied on save**: If the DOCX is open in Word, saving will fail. Save with a new filename or close Word first.
- **Source cross-contamination**: If the user provides a template that was previously filled for another company/institution, the old content might be hidden in the XML. Always parse the template fresh and verify the output contains no legacy content.
- **Missing imports in Python scripts**: PythonRun scripts need explicit imports (`import os`, `from docx.shared import Pt`, etc.). Do not assume imports are available.
- **Function naming in PythonRun**: Always wrap logic in a `def main(context):` function. Bare module-level code may fail with `Function not found: main`.
- **PDF text extraction**: Use `pdfminer.high_level.extract_text` (bundled in the managed runtime) rather than `PyPDF2` or `PyMuPDF`, which may not be available.

## Related Skills

- `bid-proposal`: Use for procurement/tender bidding documents (投标/标书/招标文件), indicator matching, and bid annotations — NOT for platform application documents.
- `docx`: Use for general DOCX creation, editing, repair, and validation.
- `report-writing`: Use for long-form industry reports, policy briefs, or market analysis — NOT for filling government application templates.
