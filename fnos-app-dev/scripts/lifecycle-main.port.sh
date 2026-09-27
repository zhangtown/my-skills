#!/bin/sh
# app/cmd/main —— 独立端口模式（桌面点图标后**跳转到一个新端口**）的生命周期脚本模板
#
# 与内嵌版的区别只有一件事：后端要在网关/反代之外再监听一个 TCP 端口（因为桌面是直接跳过去的）。
# 端口号必须与应用中心显示的一致；用向导安装时从环境变量取（$wizard_app_port 之类，变量名与
# config/ 里的向导定义一致），非交互安装（install-local）时必须有默认值兜底——
# 否则会出现"卸载成功、安装失败"的中间态：应用从应用中心消失、服务没起来。

APPDIR="$(cd "$(dirname "$0")/.." && pwd)"
BIN="$APPDIR/app/server/myapp"
PORT="${wizard_app_port:-15100}"        # ← 非交互安装时用的默认端口

export MYAPP_DATA="${TRIM_PKGVAR:-$APPDIR/var}"
export MYAPP_LOG_DIR="${TRIM_PKGETC:-$APPDIR/etc}"
export MYAPP_PORT="$PORT"

start()  { exec "$BIN" -listen "0.0.0.0:$PORT" -data "$MYAPP_DATA" >>"${MYAPP_LOG_DIR}/myapp.log" 2>&1; }
stop()   { pkill -f "$BIN" >/dev/null 2>&1 || true; }
status() { pgrep -f "$BIN" >/dev/null 2>&1; }

case "$1" in
  start)  start  ;;
  stop)   stop   ;;
  status) status ;;
  log)    tail -n 200 "${MYAPP_LOG_DIR}/myapp.log" 2>/dev/null ;;
  *)      echo "usage: $0 {start|stop|status|log}" >&2; exit 1 ;;
esac
