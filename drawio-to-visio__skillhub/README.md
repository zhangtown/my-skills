# Draw.io to Visio Skill

Convert existing Draw.io / diagrams.net XML diagrams into editable Microsoft Visio `.vsdx` files with local browser automation and structural validation.

The repository is both a Codex Agent Skill and a directly runnable converter.

## Why this exists

Current diagrams.net releases no longer expose VSDX export. This project pins the last supported exporter, diagrams.net `26.0.16`, and drives it locally through Playwright.

- Customer diagrams are served only from `127.0.0.1`.
- Browser requests to non-local hosts are blocked after the diagram is loaded.
- The generated file is checked as a real Visio ZIP/OPC package.
- Required Visio XML, pages, shapes, connectors, and optional key phrases are validated.

## Install as a Codex Skill

```bash
git clone https://github.com/Larry-Labs/drawio-to-visio.git \
  ~/.codex/skills/drawio-to-visio
cd ~/.codex/skills/drawio-to-visio
npm ci
```

Start a new Codex task, then ask:

```text
Use $drawio-to-visio to convert /absolute/path/diagram.drawio to Visio.
```

## Run directly

Install the locked Node dependency once:

```bash
npm ci
```

```bash
bash scripts/convert_drawio_to_vsdx.sh \
  "/absolute/path/input.drawio" \
  "/absolute/path/output.vsdx"
```

Require important labels to survive conversion:

```bash
bash scripts/convert_drawio_to_vsdx.sh \
  "/absolute/path/input.drawio" \
  "/absolute/path/output.vsdx" \
  --expect "Approval" \
  --expect "Database"
```

Available options:

| Option | Purpose |
| --- | --- |
| `--force` | Replace an existing output file. |
| `--expect TEXT` | Require text in the VSDX; repeat as needed. |
| `--no-download` | Refuse first-time network setup and use the existing cache only. |
| `--cache-dir PATH` | Override the diagrams.net cache directory. |
| `--timeout SECONDS` | Override the timeout with an integer of at least 30 seconds; default is 180. |

## Requirements

- macOS is tested. Linux is best-effort and requires Bash plus a compatible Chromium installation or Playwright cache.
- Node.js 20 or later.
- The pinned Playwright Node package installed with `npm ci`.
- Chromium, Chrome, Edge, or Playwright Chromium.
- Python 3.
- Git for first-time setup and later verification of the pinned diagrams.net cache.

On first use, the wrapper clones the official diagrams.net `v26.0.16` source into the user cache and verifies the pinned commit. This happens before customer content is opened. Later runs can use `--no-download` for an offline conversion.

## Privacy and fidelity notes

- Diagram XML is served from one temporary `127.0.0.1` origin and is not sent to a third-party conversion service.
- Other HTTP origins, all WebSockets, and service workers are blocked. Remote images, web fonts, and external custom-stencil assets may therefore be missing; embed critical assets before conversion.
- The command logs resolved input and output paths. Failed `--expect` checks identify missing phrases. Review logs before sharing them.
- The first run downloads the pinned diagrams.net source from GitHub unless `--no-download` is set.

## Validation levels

The bundled validator proves:

1. The output is a ZIP/OPC package, not a PDF renamed to `.vsdx`.
2. OPC content types and relationship parts are valid XML.
3. The package contains a consistent Visio document-to-pages-to-page relationship chain with Visio namespaces.
4. Referenced pages contain Visio shapes and report connector counts.
5. Every supplied `--expect` phrase appears in the text of a shape on a referenced Visio page.

This does not guarantee pixel-perfect Microsoft Visio rendering. For high-stakes delivery, open the result in a real Microsoft Visio client and perform a visual check.

## Troubleshooting

- `Playwright Node package not found`: run `npm ci` in this repository.
- `no compatible Chromium...`: install Chrome, Edge, Chromium, or run `npx playwright install chromium`.
- Override browser discovery with `DRAWIO_VISIO_BROWSER=/absolute/path/to/browser`; Playwright's `PLAYWRIGHT_BROWSERS_PATH` is also supported.
- On Windows, use a Bash environment that exposes Node.js and Python through the `node`, `python3`, and `git` commands.
- `cache lacks Git metadata`, `cache has modified...`, or `incomplete cache`: remove that generated cache directory and rerun so the pinned upstream source can be fetched and verified.
- Missing images or fonts: replace remote assets with embedded/local assets in the Draw.io source.

## Development checks

```bash
python3 -m unittest discover -s tests -v
python3 scripts/validate_vsdx.py output.vsdx --expect "Required label"
```

## Provenance

- Export engine: [jgraph/drawio](https://github.com/jgraph/drawio), version `26.0.16`.
- Pinned commit: `987146fb55a547a975961f57dddc781abf7648ba`.
- Upstream change log: [VSDX export history](https://github.com/jgraph/drawio/blob/dev/ChangeLog).
- Background: [draw.io discussion #5173](https://github.com/jgraph/drawio/discussions/5173).

The diagrams.net source is not bundled in this repository. It is fetched from the official upstream repository when needed and remains under its Apache License 2.0.

This is an independent project and is not affiliated with or endorsed by JGraph,
diagrams.net, draw.io, or Microsoft. Product names and trademarks belong to their
respective owners.

## License

Apache License 2.0. See [LICENSE](LICENSE).
