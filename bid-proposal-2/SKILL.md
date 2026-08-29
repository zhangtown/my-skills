---
name: bid-proposal
description: "Bid and tender document preparation workflow for Chinese government/enterprise procurement projects (投标方案/标书). Use when the user needs to assemble, edit, annotate, or restructure bid proposal DOCX files, merge technical content from source documents into target templates, add indicator-matching comments/annotations (批注) to bid proposals, edit procurement scoring standards (采购评分标准), or create technical specification chapters (招标技术规格及要求). Trigger keywords: 投标、标书、招标文件、投标方案、评分标准、偏离表、技术响应、招标技术规格、招标参数、应答、批注、设备概述、工作原理、系统架构、系统组成、合入."
---

# Bid Proposal Document Preparation (投标方案/标书制作)

## Domain Context

This skill covers the full workflow of preparing bid/tender documents (投标方案/标书) for Chinese government and enterprise procurement projects, especially in cybersecurity, IT infrastructure, and industrial control sectors. The user typically works with large DOCX files (>100MB) containing technical specifications, platform descriptions, and scoring criteria.

## Common Workflows

### 1. Content Extraction and Merge
1. Scan the workspace directory to identify source and target DOCX files
2. Extract specific module content from source DOCX files using `PythonRun` with `zipfile`/`xml.etree` (more reliable than `python-docx` for large/corrupted files)
   - Common modules: 基础平台模块, 场景构建模块, 教学实训模块, 比武竞赛模块, 攻防演练模块, 技术研究模块, 镜像资源库模块
3. Identify insertion positions in the target template by searching for section headings (e.g., `1.6.2.2.1`, `1.6.2.2.2`)
4. Merge extracted content into target bid proposal templates at correct section positions, preserving original formatting
5. Use `python-docx` for in-place edits when the file is not corrupted; use `zipfile` repair for files with `NULL` relationship targets

### 2. Technical Section Writing
1. Write the four standard sections for each platform: **设备概述** (Device Overview), **工作原理** (Working Principle), **系统架构** (System Architecture), **系统组成** (System Composition)
2. Reference the style and depth of existing sections (e.g., `1.6.2.2.5 新能源综合定制化沙盘设备`) for consistency
3. For system architecture diagrams, generate HTML with CSS/JS, then use `kimi-webbridge` to screenshot
4. System composition should describe modules in a layered structure (e.g., "场景展示层、环境驱动层、设备运行层...")

### 3. Indicator Annotation and Commenting (批注)
1. Read the technical indicator source file (e.g., `57条指标响应对照.txt`, `电力新能源靶场指标.txt`, `偏离表`, Excel指标表)
2. Parse the indicator file:
   - Common pattern: alternating lines where odd lines are the original indicator (原指标) and even lines are the response content (指标响应), separated by blank lines
   - Watch for **multi-line responses** that can cause parsing mismatches; verify parsed counts match (e.g., 57 indicators vs. 57 responses)
3. In the target DOCX, locate the "response content" (响应内容/应答内容) for each indicator using multi-strategy matching:
   - **Substring containment**: check if the first 30 characters of the indicator appear in a paragraph
   - **SequenceMatcher similarity**: compute similarity ratio on the first 50 characters with a threshold of ~0.6 for fallback matching
   - **Style-based filtering**: if the template uses custom styles (e.g., `BZ-正文`), restrict matches to functional-description paragraphs only
4. Select the response text and add a Word comment/annotation (批注) with the original indicator text (including the indicator number/编号)
5. Ensure **one-to-one matching** between each indicator and its corresponding response content
6. Use `python-docx` comment features or the `docx` skill's `DocxContext` editing module for adding comments; for very large files (>100 MB), direct XML manipulation via `lxml` + `zipfile` may be more reliable
7. **Validate after adding comments**:
   - Total comment count matches the expected number of indicators
   - No orphaned comment references (comment IDs in `document.xml` match `comments.xml`)
   - All comments preserve the original indicator number (带编号)
   - Comments are attached only to functional-description paragraphs (e.g., `BZ-正文` style), not to overview/system-architecture sections

### 4. Scoring Standards Editing (采购评分标准)
1. Open the scoring standard DOCX file and locate the scoring table
2. Identify cells to modify by their row/column positions and text content
3. Modify scoring criteria text to be professional and compliant:
   - Avoid "分档标准：" phrasing; use structured scoring criteria instead
   - Avoid "|`" symbols in table cells (use natural paragraph breaks)
   - Use neutral, non-discriminatory language (完善/基本完善/一般/未提供)
4. Add new scoring items when requested (e.g., 产教融合, 接口对接) with appropriate point allocations
5. Ensure total score remains consistent (e.g., 100-point system)
6. Verify compliance with 招标投标法 and 政府采购法 (no倾向性/排他性条款)

### 5. Technical Specification Chapter Creation
1. Reference existing procurement document formats (e.g., 东南大学招标文件第四章)
2. Add a new chapter (e.g., 第四章 招标技术规格及要求) to the scoring standard or bid document
3. Extract technical parameters from Excel/Word source files (e.g., 设备清单和信息详表)
4. Format as bid-compliant technical specifications with numbered items and ▲ markers for critical requirements

## Environment and Pitfall Notes

- **Windows + Git Bash environment**: Chinese filenames frequently cause encoding issues. Use `PythonRun` for file operations rather than Bash when possible. If Bash is needed, use forward-slash paths (`C:/Users/...`) and avoid inline Chinese characters in shell commands.
- **Python interpreter**: The managed Python environment is at `C:/Users/ELEX-ZT/AppData/Roaming/kimi-desktop/daimon-share/daimon/runtime/python`. If `python` or `python3` is not found in Bash, use `C:/Python314/python.exe` or the managed runtime path.
- **Large/corrupted DOCX files**: Files >100MB may have corrupted `word/_rels/document.xml.rels` with `NULL` targets. Use `zipfile` repair scripts to fix these before opening with `python-docx`.
- **File locking**: If a DOCX file is open in Word, `python-docx` cannot overwrite it. Save to a new filename and inform the user to close the original file.
- **Sub-agent delegation**: For multi-platform content writing, use `swarm-coding` or parallel sub-agents (one per platform). However, `Agent` tool may require `subagent_type` specification for new agents vs. resuming existing ones.

## Recommended Tool Stack

| Task | Tool | Notes |
|------|------|-------|
| Directory scanning | `Glob` / `Bash` (ls) | Use `PythonRun` for Chinese filenames |
| DOCX reading (large/corrupted) | `PythonRun` + `zipfile` + `xml.etree` | More robust than `python-docx` for damaged files |
| DOCX reading (normal) | `python-docx` / `docx` skill | Use `Document()` for standard files |
| DOCX repair | `PythonRun` + `zipfile` | Fix `NULL` targets in `.rels` files |
| Text extraction | `PythonRun` | Save to JSON/txt for inspection |
| In-place DOCX editing | `python-docx` | Simple text/style edits |
| Comments/annotations | `DocxContext` (from `docx` skill) | For tracked changes and comments |
| Table editing | `python-docx` | Direct cell text modification |
| Architecture diagrams | `kimi-webbridge` | HTML → screenshot → insert into DOCX |
| Content search | `Grep` | Search for keywords in extracted text |
| Excel reading | `PythonRun` + `openpyxl` / `pandas` | For technical parameter sources |
