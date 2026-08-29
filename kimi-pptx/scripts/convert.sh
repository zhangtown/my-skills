#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

export PYTHONUTF8=1
: "${LC_ALL:=C.UTF-8}"; export LC_ALL
: "${LANG:=C.UTF-8}";   export LANG
export PYTHONPATH="$SCRIPT_DIR${PYTHONPATH:+:$PYTHONPATH}"

PYTHON_BIN="${KIMI_PPT_DSL_PYTHON:-${PPTD_PYTHON:-python3}}"

if [ -f "$SCRIPT_DIR/kimi_ppt_dsl.pyz" ]; then
    exec "$PYTHON_BIN" "$SCRIPT_DIR/kimi_ppt_dsl.pyz" convert "$@"
fi

exec "$PYTHON_BIN" -m kimi_ppt_dsl convert "$@"
