#!/usr/bin/env bash
set -euo pipefail

DRAWIO_VERSION="26.0.16"
DRAWIO_COMMIT="987146fb55a547a975961f57dddc781abf7648ba"
PLAYWRIGHT_VERSION="1.62.0"
SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEFAULT_CACHE="${XDG_CACHE_HOME:-${HOME}/.cache}/drawio-to-visio/drawio-${DRAWIO_VERSION}"

usage() {
  cat <<'EOF'
Usage: convert_drawio_to_vsdx.sh INPUT.drawio [OUTPUT.vsdx] [options]

Options:
  --force              overwrite an existing output
  --expect TEXT        require TEXT in the generated VSDX; repeatable
  --no-download        do not fetch diagrams.net when the cache is missing
  --cache-dir PATH     override diagrams.net cache path
  --timeout SECONDS    browser/export timeout, integer >= 30 (default: 180)
EOF
}

if [[ $# -eq 1 && ( "$1" == "-h" || "$1" == "--help" ) ]]; then
  usage
  exit 0
fi
if [[ $# -lt 1 ]]; then
  usage >&2
  exit 2
fi

INPUT="$1"
shift
OUTPUT=""
if [[ $# -gt 0 && "$1" != --* ]]; then
  OUTPUT="$1"
  shift
fi

FORCE=0
ALLOW_DOWNLOAD=1
CACHE_DIR="$DEFAULT_CACHE"
TIMEOUT=180
EXPECTS=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    --force) FORCE=1; shift ;;
    --no-download) ALLOW_DOWNLOAD=0; shift ;;
    --expect)
      [[ $# -ge 2 ]] || { echo "ERROR: --expect requires text" >&2; exit 2; }
      EXPECTS+=("$2"); shift 2 ;;
    --cache-dir)
      [[ $# -ge 2 ]] || { echo "ERROR: --cache-dir requires a path" >&2; exit 2; }
      CACHE_DIR="$2"; shift 2 ;;
    --timeout)
      [[ $# -ge 2 ]] || { echo "ERROR: --timeout requires seconds" >&2; exit 2; }
      TIMEOUT="$2"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "ERROR: unknown option: $1" >&2; usage >&2; exit 2 ;;
  esac
done

if [[ ! "$TIMEOUT" =~ ^[0-9]+$ || "$TIMEOUT" -lt 30 ]]; then
  echo "ERROR: --timeout must be a positive integer of at least 30 seconds" >&2
  exit 2
fi

[[ -f "$INPUT" ]] || { echo "ERROR: input not found: $INPUT" >&2; exit 1; }
INPUT="$(cd "$(dirname "$INPUT")" && pwd)/$(basename "$INPUT")"

if [[ -z "$OUTPUT" ]]; then
  OUTPUT="${INPUT%.*}.vsdx"
fi
[[ "${OUTPUT##*.}" == "vsdx" ]] || { echo "ERROR: output must end with .vsdx" >&2; exit 1; }

if [[ -e "$OUTPUT" && "$FORCE" -ne 1 ]]; then
  echo "ERROR: output exists; pass --force to replace it: $OUTPUT" >&2
  exit 1
fi

command -v python3 >/dev/null 2>&1 || { echo "ERROR: Python 3 is required" >&2; exit 1; }
command -v git >/dev/null 2>&1 || { echo "ERROR: git is required to verify diagrams.net" >&2; exit 1; }

NODE_BIN="${DRAWIO_VISIO_NODE:-$(command -v node || true)}"
[[ -n "$NODE_BIN" ]] || { echo "ERROR: Node.js is required" >&2; exit 1; }
NODE_MAJOR="$("$NODE_BIN" -p "Number(process.versions.node.split('.')[0])" 2>/dev/null || true)"
[[ "$NODE_MAJOR" =~ ^[0-9]+$ && "$NODE_MAJOR" -ge 20 ]] || {
  echo "ERROR: Node.js 20 or later is required" >&2
  exit 1
}

if [[ -f "$SKILL_DIR/node_modules/playwright/package.json" ]]; then
  export NODE_PATH="$SKILL_DIR/node_modules${NODE_PATH:+:$NODE_PATH}"
fi
if ! "$NODE_BIN" -e "require('playwright')" >/dev/null 2>&1; then
  for candidate in "${HOME}"/.cache/codex-runtimes/*/dependencies/node/node_modules; do
    if [[ -f "$candidate/playwright/package.json" ]]; then
      export NODE_PATH="$candidate${NODE_PATH:+:$NODE_PATH}"
      break
    fi
  done
fi
"$NODE_BIN" -e "require('playwright')" >/dev/null 2>&1 || {
  echo "ERROR: Playwright Node package not found; run 'npm ci' in $SKILL_DIR" >&2
  exit 1
}
ACTUAL_PLAYWRIGHT_VERSION="$("$NODE_BIN" -p "require('playwright/package.json').version")"
[[ "$ACTUAL_PLAYWRIGHT_VERSION" == "$PLAYWRIGHT_VERSION" ]] || {
  echo "ERROR: expected Playwright ${PLAYWRIGHT_VERSION}, found ${ACTUAL_PLAYWRIGHT_VERSION}" >&2
  exit 1
}

if command -v xmllint >/dev/null 2>&1; then
  xmllint --noout "$INPUT" || { echo "ERROR: invalid Draw.io XML" >&2; exit 1; }
fi

if [[ -e "$CACHE_DIR" && ! -f "$CACHE_DIR/src/main/webapp/index.html" ]]; then
  echo "ERROR: incomplete diagrams.net cache; remove it or use --cache-dir: $CACHE_DIR" >&2
  exit 1
fi
if [[ ! -f "$CACHE_DIR/src/main/webapp/index.html" ]]; then
  if [[ "$ALLOW_DOWNLOAD" -ne 1 ]]; then
    echo "ERROR: diagrams.net cache missing and --no-download was set: $CACHE_DIR" >&2
    exit 1
  fi
  mkdir -p "$(dirname "$CACHE_DIR")"
  CACHE_LOCK_DIR="${CACHE_DIR}.lock"
  if ! mkdir "$CACHE_LOCK_DIR" 2>/dev/null; then
    echo "ERROR: cache initialization is already in progress: $CACHE_LOCK_DIR" >&2
    exit 1
  fi
  TMP_CACHE="${CACHE_DIR}.tmp.$$"
  cleanup_cache_setup() {
    rm -rf -- "${TMP_CACHE:-}"
    rmdir -- "${CACHE_LOCK_DIR:-}" 2>/dev/null || true
  }
  trap cleanup_cache_setup EXIT
  git clone --quiet --branch "v${DRAWIO_VERSION}" --depth 1 https://github.com/jgraph/drawio.git "$TMP_CACHE"
  ACTUAL_COMMIT="$(git -C "$TMP_CACHE" rev-parse HEAD)"
  [[ "$ACTUAL_COMMIT" == "$DRAWIO_COMMIT" ]] || {
    echo "ERROR: unexpected diagrams.net commit: $ACTUAL_COMMIT" >&2
    exit 1
  }
  mv "$TMP_CACHE" "$CACHE_DIR"
  rmdir "$CACHE_LOCK_DIR"
  trap - EXIT
fi

ACTUAL_VERSION="$(tr -d '[:space:]' < "$CACHE_DIR/VERSION")"
[[ "$ACTUAL_VERSION" == "$DRAWIO_VERSION" ]] || {
  echo "ERROR: expected diagrams.net ${DRAWIO_VERSION}, found ${ACTUAL_VERSION}" >&2
  exit 1
}

[[ -d "$CACHE_DIR/.git" ]] || {
  echo "ERROR: diagrams.net cache lacks Git metadata and cannot be verified: $CACHE_DIR" >&2
  exit 1
}
ACTUAL_COMMIT="$(git -C "$CACHE_DIR" rev-parse HEAD)"
[[ "$ACTUAL_COMMIT" == "$DRAWIO_COMMIT" ]] || {
  echo "ERROR: expected diagrams.net commit ${DRAWIO_COMMIT}, found ${ACTUAL_COMMIT}" >&2
  exit 1
}
if [[ -n "$(git -C "$CACHE_DIR" status --porcelain --untracked-files=all)" ]]; then
  echo "ERROR: diagrams.net cache has modified or untracked files: $CACHE_DIR" >&2
  exit 1
fi

mkdir -p "$(dirname "$OUTPUT")"
OUTPUT="$(cd "$(dirname "$OUTPUT")" && pwd)/$(basename "$OUTPUT")"
if [[ -e "$OUTPUT" && "$FORCE" -ne 1 ]]; then
  echo "ERROR: output exists; pass --force to replace it: $OUTPUT" >&2
  exit 1
fi

WEBROOT="$CACHE_DIR/src/main/webapp"
TMP_OUTPUT="${OUTPUT}.tmp.$$"
rm -f "$TMP_OUTPUT"
trap 'rm -f "${TMP_OUTPUT:-}"' EXIT

"$NODE_BIN" "$SKILL_DIR/scripts/export_vsdx.js" "$INPUT" "$TMP_OUTPUT" "$WEBROOT" "$TIMEOUT"

VALIDATE_ARGS=("$TMP_OUTPUT")
for text in "${EXPECTS[@]}"; do
  VALIDATE_ARGS+=(--expect "$text")
done
python3 "$SKILL_DIR/scripts/validate_vsdx.py" "${VALIDATE_ARGS[@]}"

if [[ -e "$OUTPUT" ]]; then
  rm -f "$OUTPUT"
fi
mv "$TMP_OUTPUT" "$OUTPUT"
trap - EXIT
echo "VSDX ready: $OUTPUT"
