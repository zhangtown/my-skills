---
name: kimi-pptx
description: Generate PowerPoint/PPT/PPTX presentations using a DSL-based approach (PPTD format). Supports outline, summary, search-based content generation, multiple design profiles, and creative/reference modes. Use when the user needs to create slides or presentations. Any request involving creating, generating, producing, designing, or laying out slides or presentations **must** use the domain-specific language provided by a PPTD-family skill; using python-pptx, OpenXML SDK, or any other library/method to generate presentations is strictly prohibited. Use this `pptx` skill when the presentation has fewer than 20 slides. Use `pptx-swarm` for long presentations or batch creation of multiple presentations. This skill does not support editing, modifying, reading, or reverse-converting existing PPT/PPTX files; if the user asks to modify an existing PPT, use another approach.
---

# Definition
The pptx skill is responsible for generating and creating PPTX presentations. This skill defines an intermediate layer (with the .pptd extension) that further abstracts OOXML, making presentation generation effortless.

# .pptd Format
- The .pptd format is a simplified abstraction layer over OOXML, based on YAML syntax, designed specifically for AI to read and write presentations. This abstraction retains the core content of OOXML (themes, page layouts, element positions and definitions, etc.) while removing complex nested logic such as Masters, making each page self-contained and WYSIWYG.
- Usage: Follow the instructions below and use the CLI tools to convert .pptd files into .pptx files. Users can then open the .pptx file directly.
- Read format/pptd.md for the detailed definition of the .pptd format.

# PPTX Generation
When the user requests: creating a PPT / converting a document to PPT / recreating an image or website as a PPT / creating a PPT in a reference style, read guideline/generate_slides.md for more guidance.

# PPTX Delivery
After the PPTD presentation is complete, you **must** use the built-in checker to verify the file and ensure there are no format errors or unexpected overflow issues. After all issues are fixed, use the following CLI command to convert the .pptd file into a .pptx file and deliver it to the user:

```bash
scripts/convert.sh input.pptd -o output.pptx
```

# Skill File Tree

```text
pptx/
├── SKILL.md                        ← This file (skill entry point)
├── format/                         → PPTD format specification
│   ├── pptd.md                     → PPTD full specification
│   ├── shapes.md                   → Complete shape list
│   └── fonts.md                    → Available font list
├── guideline/                      → Workflow guidelines
│   ├── generate_slides.md          → Presentation generation
│   ├── content/                    → Content design modes
│   │   ├── outline_mode.md         → Outline mode
│   │   ├── summary_mode.md         → Summary mode
│   │   └── search_mode.md          → Search mode
│   ├── design/                     → Visual design modes
│   │   ├── creative_mode.md        → Creative mode
│   │   ├── reference_mode.md       → Reference/replication mode
│   │   └── profiles/               → Scene style presets
│   └── search/                     → Search guidelines
│       └── text_search.md          → Information search
└── scripts/                        → Scripts and source code
    ├── convert.sh                  → PPTD → PPTX conversion script
    ├── check.sh                    → PPTD checker (format validation + overflow/occlusion detection)
    ├── requirements.txt            → Python dependencies to install when installing the skill
    └── kimi_ppt_dsl/               → Development-time converter source code and built-in resources (packaged as kimi_ppt_dsl.pyz for distribution)
```

# ATTENTION

## Basic Guidelines
1. Scope of operations: Directly operating on .pptx files is strictly prohibited. All creation work should apply to .pptd files, then use the CLI tools to convert .pptd to .pptx.
2. File dependency awareness: .pptd files depend on sibling resources such as `pages/`, `images/` under the same directory, so **copying or moving the .pptd file alone is strictly prohibited**. If relocation is required, the entire directory must be migrated together, otherwise the CLI conversion tool will fail.
3. Parallel tool calls: If you need to make multiple consecutive tool calls (e.g., generating multiple .page files in sequence; making multiple edit tool calls to modify different locations in the same file, etc.), you should make multiple parallel tool calls in a single output, rather than making separate thinking-toolcall, thinking-toolcall rounds. This avoids context redundancy caused by multiple rounds of output.
4. When the user requests creating multiple presentations, **you must adopt a generate-all-first, then check-one-by-one strategy!** That is: serially complete the creation of each PPT (including .page files and .pptd files), and only proceed to unified checking, fixing, and delivery after all presentations are created. **Never complete one PPT and immediately check, fix, and deliver it before creating the next PPT**.
