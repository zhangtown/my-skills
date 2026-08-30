# Compatibility and provenance

## Engine

- Export engine: diagrams.net / draw.io `26.0.16`.
- Source: `https://github.com/jgraph/drawio`, tag `v26.0.16`.
- Pinned source commit: `987146fb55a547a975961f57dddc781abf7648ba`.
- Upstream license: Apache License 2.0.

Later diagrams.net releases removed the VSDX exporter, so do not silently substitute the latest release. Official context:

- Change log: `https://github.com/jgraph/drawio/blob/dev/ChangeLog`
- VSDX export discussion: `https://github.com/jgraph/drawio/discussions/5173`

## Runtime

- Node.js 20 or later.
- Playwright package `1.62.0` and Chromium, Chrome, Edge, or a Playwright Chromium cache.
- Git for the first official-source download and cache verification on every run.
- Python 3 for VSDX package validation.

The wrapper searches the pinned Playwright package, `PLAYWRIGHT_BROWSERS_PATH`, common Codex/Playwright caches, system `PATH`, and common browser locations. Set `DRAWIO_VISIO_BROWSER` to an absolute executable path when automatic discovery is insufficient. Native macOS is tested; Linux is best-effort. Windows requires a Bash environment that exposes the `node`, `python3`, and `git` commands.

The browser permits only the conversion server's exact temporary HTTP origin,
blocks all WebSockets and service workers, and fulfills the pinned exporter
extension locally. Remote images, web fonts, and external custom-stencil assets
may therefore be absent from the export. Embed delivery-critical assets in the
source diagram before conversion.

The command prints resolved input and output paths, and `--expect` prints missing
phrases on failure. Do not publish conversion logs without reviewing them.

## Fidelity boundary

The result contains editable Visio shapes and connectors, but conversion is not guaranteed pixel-perfect for every Draw.io feature. Complex custom stencils, unsupported fonts, embedded remote images, advanced labels, and application-specific rendering may differ.

Use three evidence levels:

1. Package validated: OPC content types, relationship XML, Visio namespaces, and the document/pages/page relationship chain are consistent.
2. Page content validated: required phrases occur in shape text on referenced pages and shape/connect counts are plausible.
3. Visio visually validated: a real Microsoft Visio client opened and inspected the file.

Only claim the highest level actually completed.
