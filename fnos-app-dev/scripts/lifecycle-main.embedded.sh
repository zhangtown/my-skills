#!/bin/sh
# app/cmd/main —— 内嵌应用（走飞牛统一网关、无独立端口）的生命周期脚本模板
#
# 飞牛的应用中心会以不同参数调用它：start / stop / status / log 等，返回 0 表示成功。
# 建议做成"薄壳"：只负责把参数转发给真正的后端进程，不要在这里写业务逻辑。
# 若后端不在 PATH 里，用绝对路径（可从 $TRIM_APPDEST 拼出来）。

APPDIR="$(cd "$(dirname "$0")/.." && pwd)"
BIN="$APPDIR/app/bin/myapp"

# 内嵌应用一般由网关转发，不需要监听 TCP 端口；只要进程活着，网关就能连上它的 unix socket。
# 数据目录 / 日志目录等信息由应用中心通过环境变量传进来，别写死路径。
export MYAPP_DATA="${TRIM_PKGVAR:-$APPDIR/var}"
export MYAPP_LOG_DIR="${TRIM_PKGETC:-$APPDIR/etc}"

start()  { exec "$BIN" >>"${MYAPP_LOG_DIR}/myapp.log" 2>&1; }
stop()   { pkill -f "$BIN" >/dev/null 2>&1 || true; }
status() { pgrep -f "$BIN" >/dev/null 2>&1; }

case "$1" in
  start)  start  ;;
  stop)   stop   ;;
  status) status ;;
  log)    tail -n 200 "${MYAPP_LOG_DIR}/myapp.log" 2>/dev/null ;;
  *)      echo "usage: $0 {start|stop|status|log}" >&2; exit 1 ;;
esac
