#!/usr/bin/env bash
# 飞牛应用一键部署/升级模板 —— 复制到项目的 deploy/fnos-app/install.sh 后改「配置」块。
#
#   bash deploy/fnos-app/install.sh              # 默认：版本号 patch+1 后打包并安装
#   bash deploy/fnos-app/install.sh --no-bump    # 用当前版本号（首次安装用）
#
# 为什么不用 `appcenter-cli install-fpk`：对**已安装**的同名应用它是空操作
# （只打印 "Application [<app>] is installed."，文件一个字节都不换）。
# 必须 `install-local -d <解包目录> -v <卷>` 才会真正替换（内部：停止 → 卸载 → 安装 → 启动）。
# 数据目录 /usr/local/apps/@appdata/<app> 不受影响（卸载向导默认"保留数据"）。
#
# 连接信息从 deploy/fnos-app/nas.env 读（该文件不入库）：
#   NAS=user@host  NAS_PORT=22  NAS_KEY=~/.ssh/id_ed25519  NAS_VOL=1
set -e

# ======== 配置 ========
APP_NAME=myapp                    # manifest 的 appname（也是 /var/apps/<app> 的目录名）
PKG_DIR=packaging/fnos/myapp      # 包目录（给 pack.sh 用）
MODE=socket                       # socket = 内嵌走网关；port = 独立端口
PORT=15100                        # MODE=port 时用于探活
SOCK_REL=target/app.sock          # MODE=socket 时，socket 相对 /var/apps/<app>/ 的路径
DATA_REL=var                      # 数据目录相对 /var/apps/<app>/ 的路径（一般就是 var）
# =====================

cd "$(dirname "$0")/../.."
[ -f deploy/fnos-app/nas.env ] && . deploy/fnos-app/nas.env
NAS="${NAS:-}"; NAS_PORT="${NAS_PORT:-22}"; NAS_KEY="${NAS_KEY:-$HOME/.ssh/id_ed25519}"; NAS_VOL="${NAS_VOL:-1}"
if [ -z "$NAS" ]; then
  echo "缺少 NAS 连接信息：cp deploy/fnos-app/nas.env.example deploy/fnos-app/nas.env 并填自己的 NAS" >&2
  exit 2
fi
SSH=(ssh -i "$NAS_KEY" -p "$NAS_PORT" -o BatchMode=yes -o ConnectTimeout=8 "$NAS")
SCP=(scp -i "$NAS_KEY" -P "$NAS_PORT" -o BatchMode=yes)

BUMP=1
[ "$1" = "--no-bump" ] && BUMP=
FPK=deploy/fnos-app/$APP_NAME.fpk

# 1) 打包
if [ -n "$BUMP" ]; then BUMP=1 bash "$PKG_DIR/../$(basename "$PKG_DIR")/../../deploy/fnos-app/pack.sh" 2>/dev/null || BUMP=1 bash deploy/fnos-app/pack.sh
else bash deploy/fnos-app/pack.sh; fi
VERSION="$(sed -n 's/^version *=[[:space:]]*//p' "$PKG_DIR/manifest" | head -n1)"
[ -f "$FPK" ] || { echo "没找到 $FPK"; exit 1; }
LOCAL_ICON_MD5="$(md5sum < icon.png 2>/dev/null | awk '{print $1}')"

# 2) 上传 + 远端安装
echo "== 上传 $APP_NAME $VERSION 到 $NAS"
"${SCP[@]}" "$FPK" "$NAS:/tmp/$APP_NAME-$VERSION.fpk" >/dev/null
"${SSH[@]}" bash -s <<REMOTE
set -e
# 升级前备份数据目录（sudo -n cp 实测在白名单里；ls/md5sum 不在，别用）
BK=/tmp/$APP_NAME-data-backup-\$(date +%H%M)
sudo -n cp -a /usr/local/apps/@appdata/$APP_NAME "\$BK" 2>/dev/null && echo "   数据已备份到 \$BK" || echo '   （无数据目录，跳过备份）'
rm -rf ~/$APP_NAME-pkg && mkdir -p ~/$APP_NAME-pkg
tar xzf /tmp/$APP_NAME-$VERSION.fpk -C ~/$APP_NAME-pkg
sudo -n /usr/local/bin/appcenter-cli install-local -d "\$HOME/$APP_NAME-pkg" -v $NAS_VOL 2>&1 \\
  | tr '\r' '\n' | grep -vE '^[\\\\/|.-]* ?(Verifying|installing|uninstalling|starting|stopping)' | tail -5
sleep 3
REMOTE

# 3) 自检（只用免密可用的命令 + 不需要 sudo 的 HTTP 探测）
echo "== 验证"
if [ "$MODE" = "socket" ]; then
"${SSH[@]}" bash -s <<REMOTE
set +e
echo -n '  登记版本: '; sudo -n /usr/local/bin/appcenter-cli list 2>&1 | awk -F'│' '/$APP_NAME/{gsub(/ /,"",\$4); print \$4"  "\$5}'
SOCK=/var/apps/$APP_NAME/$SOCK_REL
echo -n '  health:   '; curl -s -m 5 --unix-socket \$SOCK http://localhost/api/health; echo
echo -n '  入口页:   '; curl -s -m 5 --unix-socket \$SOCK -o /dev/null -w 'HTTP %{http_code}  %{content_type}  %{size_download}B' http://localhost/; echo
echo -n '  socket:   '; ls -l \$SOCK 2>&1 | awk '{print \$1" "\$NF}'
REMOTE
else
"${SSH[@]}" bash -s <<REMOTE
set +e
echo -n '  登记版本: '; sudo -n /usr/local/bin/appcenter-cli list 2>&1 | awk -F'│' '/$APP_NAME/{gsub(/ /,"",\$4); print \$4"  "\$5}'
echo -n '  health:   '; curl -s -m 5 http://127.0.0.1:$PORT/api/health; echo
echo -n '  入口页:   '; curl -s -m 5 -o /dev/null -w 'HTTP %{http_code}  %{content_type}  %{size_download}B' http://127.0.0.1:$PORT/; echo
echo -n '  favicon:  '; curl -s -m 5 http://127.0.0.1:$PORT/icon.png | md5sum | awk '{print \$1}'
echo "              （仓库 icon.png: ${LOCAL_ICON_MD5}）"
REMOTE
fi
echo
echo "== 完成。桌面/应用中心打开「$APP_NAME」；若图标或界面看着没变，先用无痕窗口排掉客户端缓存。"
