#!/usr/bin/env bash
# 投标文件风险审查报告 —— 一键构建（自动准备依赖 + 构建 + 校验）
#
# 用法：
#   bash scripts/report_docx/build.sh <report.json> <output.docx> [--no-validate]
#
# 依赖解析顺序：本地 node_modules → kimi-docx 共享依赖目录（自动安装）。
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SKILL_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
DOCX_SKILL_DIR="${DOCX_SKILL_DIR:-$(cd "$SKILL_DIR/../kimi-docx" 2>/dev/null && pwd || true)}"

report_path="${1:-}"
output_path="${2:-}"
validate=1
for arg in "$@"; do
    [[ "$arg" == "--no-validate" ]] && validate=0
done

if [[ -z "$report_path" || -z "$output_path" ]]; then
    echo "用法：bash scripts/report_docx/build.sh <report.json> <output.docx> [--no-validate]" >&2
    exit 2
fi

need_cmd() {
    if ! command -v "$1" >/dev/null 2>&1; then
        echo "缺少命令：$1" >&2
        exit 1
    fi
}
need_cmd node

# 共享依赖：docx 不可解析时，用 kimi-docx 的 setup_node_env 预置到共享缓存
DOCX_CACHE="${XDG_CACHE_HOME:-$HOME/.cache}/claw-office-docx/npm/node_modules/docx"
docx_resolvable() {
    node --input-type=module -e 'await import("docx")' >/dev/null 2>&1 && return 0
    [[ -d "$DOCX_CACHE" ]] && return 0
    return 1
}
if ! docx_resolvable; then
    if [[ -n "$DOCX_SKILL_DIR" && -f "$DOCX_SKILL_DIR/scripts/setup_node_env" ]]; then
        echo "预置 docx 依赖（docx@^9）..." >&2
        bash "$DOCX_SKILL_DIR/scripts/setup_node_env" ensure-docx >&2
    fi
fi

node "$SCRIPT_DIR/build.js" "$report_path" "$output_path"

if [[ "$validate" == "1" && -n "$DOCX_SKILL_DIR" && -f "$DOCX_SKILL_DIR/scripts/docx" ]]; then
    bash "$DOCX_SKILL_DIR/scripts/docx" validate "$output_path"
fi
