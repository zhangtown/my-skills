---
name: drawio-to-visio
description: Convert existing Draw.io or diagrams.net XML diagrams (.drawio/.xml) into editable Microsoft Visio VSDX files with local browser automation and structural validation. Use when a user asks to convert, export, batch-convert, or deliver a Draw.io diagram as Visio/VSDX, especially when customer diagrams must remain local.
slug: drawio-to-visio
displayName: drawio-to-visio
version: 1.0.1
summary: Convert Draw.io diagrams to editable Visio VSDX locally, with strict OPC and page-content validation.
license: Apache-2.0
---

# Draw.io to Visio

Convert with the pinned diagrams.net VSDX exporter (`26.0.16`). Keep the diagram local and validate the generated Office package before delivery.

## Setup

Run commands from this skill directory. For a fresh repository clone, run `npm ci`. If no compatible system browser is installed, run `npx playwright install chromium` once.

## Workflow

1. Confirm the input is an existing `.drawio` or Draw.io XML file.
2. Choose an explicit `.vsdx` output path. Refuse to overwrite unless the user requested replacement; use `--force` only then.
3. Run the bundled converter:

```bash
bash scripts/convert_drawio_to_vsdx.sh \
  "/absolute/path/input.drawio" \
  "/absolute/path/output.vsdx"
```

4. For important labels, add repeatable `--expect` checks:

```bash
bash scripts/convert_drawio_to_vsdx.sh \
  "/absolute/path/input.drawio" \
  "/absolute/path/output.vsdx" \
  --expect "关键节点" \
  --expect "审批"
```

5. Report the output path, validation counts, and any remaining visual-verification limitation.

For multiple inputs, enumerate the exact source/output pairs and run the wrapper once per file. Stop on the first failure, preserve completed outputs, and report successful and failed files separately. Never add `--force` unless the user authorized replacement.

## Options

- `--force`: overwrite an existing output.
- `--expect TEXT`: require text to exist in the VSDX; repeat as needed.
- `--no-download`: require an existing local diagrams.net cache and forbid fetching it.
- `--cache-dir PATH`: override the diagrams.net cache directory.
- `--timeout SECONDS`: change browser/export timeout; use an integer of at least 30 seconds; default is 180.

## Validation Rules

Always let the wrapper run `validate_vsdx.py`. It must prove that the output:

- is a ZIP/OPC package, not a PDF renamed to `.vsdx`;
- has valid OPC content types and relationship XML;
- has a valid Visio document-to-pages-to-page relationship chain and Visio namespaces;
- has at least one Visio shape in a referenced page;
- contains every requested phrase in the text of a shape on a referenced Visio page.

For high-stakes delivery, also open the result in Microsoft Visio when available. Package validation and diagrams.net compatibility do not prove pixel-perfect Microsoft Visio rendering. Do not claim a Visio client check unless it was actually performed.

## Privacy And Dependencies

The converter loads customer content only through one temporary `127.0.0.1` origin. It blocks other HTTP origins, all WebSockets, and service workers. On first use, before loading the customer file, it may clone the fixed official diagrams.net tag from GitHub into the local cache. Later runs verify both the pinned commit and a clean cache worktree. Use `--no-download` for fully offline runs after the cache exists.

Read [references/compatibility.md](references/compatibility.md) when the user asks about supported platforms, fidelity, licensing, or why version `26.0.16` is pinned.
