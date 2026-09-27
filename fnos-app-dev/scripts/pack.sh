#!/usr/bin/env bash
# 飞牛 fpk 打包模板 —— 复制到项目的 deploy/fnos-app/pack.sh（或 packaging/fnos/<app>/pack.sh）后，
# 只改下面「配置」块里的几行即可。
#
#   bash deploy/fnos-app/pack.sh            # 用 manifest 里现有版本号
#   BUMP=1 bash deploy/fnos-app/pack.sh     # 先把版本号 patch +1 再打包
#   UI=1 bash deploy/fnos-app/pack.sh       # 先构建前端再打包
#
# 前置：fnpack 放进 .toolchain/fnpack/（不入库）
#   Windows: https://static2.fnnas.com/fnpack/fnpack-1.2.3-windows-amd64 → .toolchain/fnpack/fnpack.exe
#   Linux:   https://static2.fnnas.com/fnpack/fnpack-1.2.3-linux-amd64   → .toolchain/fnpack/fnpack
#
# 产物：deploy/fnos-app/<app>.fpk —— 安装/升级请用 install.sh（install-fpk 对已装应用无效！）
set -e

# ======== 配置 ========
APP_NAME=myapp                    # manifest 里的 appname
PKG_DIR=packaging/fnos/myapp      # 包目录（含 manifest / cmd / config / app / ICON*）
BIN_NAME=myapp                    # 可执行文件名
GO_TARGET=./cmd/myapp             # go build 的目标包路径
BIN_SUBDIR=app/bin                # 二进制放进包里的子目录（端口模式常用 app/server）
GEN_ICON=0                        # 1 = 用 tools/mkicon 生成图标（必须在编译之前跑）
UI_DIR=                           # 前端目录（如 ui）；为空则跳过前端构建
# =====================

cd "$(dirname "$0")/../.."
case "$(uname -s)" in
  MINGW*|MSYS*|CYGWIN*) FNPACK=${FNPACK:-.toolchain/fnpack/fnpack.exe} ;;
  *) FNPACK=${FNPACK:-.toolchain/fnpack/fnpack} ;;
esac

# 0) 可选：版本号 patch +1。manifest 两种写法都支持（key=value / key = value）
if [ -n "$BUMP" ]; then
  cur="$(sed -n 's/^version *=[[:space:]]*//p' "$PKG_DIR/manifest" | head -n1)"
  new="$(printf '%s' "$cur" | awk -F. '{printf "%s.%s.%d", $1, $2, $3+1}')"
  sed -i "s/^version *=[[:space:]]*.*/version=$new/" "$PKG_DIR/manifest"
  echo "== 版本 $cur → $new"
fi
VERSION="$(sed -n 's/^version *=[[:space:]]*//p' "$PKG_DIR/manifest" | head -n1)"
[ -n "$VERSION" ] || { echo "读不到 $PKG_DIR/manifest 里的 version"; exit 1; }

# locate go（新开的 shell 可能没有 PATH）
if ! command -v go >/dev/null 2>&1; then
  for c in /c/Users/*/go-sdk/go/bin/go.exe "$USERPROFILE/go-sdk/go/bin/go.exe" /usr/local/go/bin/go; do
    [ -x "$c" ] && export PATH="$(dirname "$c"):$PATH" && break
  done
fi
command -v go >/dev/null 2>&1 || { echo "go not found"; exit 1; }

# 1) 图标：必须在编译之前（程序常用 //go:embed icon.png 供 favicon，顺序反了界面里永远是旧图标）
if [ "$GEN_ICON" = "1" ]; then
  echo "== 生成图标"
  go run ./tools/mkicon -out "$PKG_DIR"
fi

# 2) 前端（可选）。产物路径要与后端 //go:embed 的目录一致
if [ -n "$UI" ] && [ -n "$UI_DIR" ]; then
  echo "== 构建前端"
  ( cd "$UI_DIR" && npm run build )
fi

# 3) 后端：linux/amd64 静态二进制，版本号同时写进二进制（health 端点能吐出它，才能证明装的哪一版）
echo "== 构建 $BIN_NAME (linux/amd64, $VERSION)"
mkdir -p "$PKG_DIR/$BIN_SUBDIR"
CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build -trimpath \
  -ldflags="-s -w -X main.version=$VERSION" \
  -o "$PKG_DIR/$BIN_SUBDIR/$BIN_NAME" "$GO_TARGET"
chmod +x "$PKG_DIR/$BIN_SUBDIR/$BIN_NAME"
ls -la "$PKG_DIR/$BIN_SUBDIR/$BIN_NAME"

# 4) 打包
echo "== fnpack build"
[ -x "$FNPACK" ] || { echo "缺少 $FNPACK（见脚本头注释）；也可用 PATH 里的 fnpack"; exit 1; }
mkdir -p deploy/fnos-app
"$FNPACK" build --directory "$PKG_DIR"
mv -f ./*.fpk deploy/fnos-app/ 2>/dev/null || true
ls -la "deploy/fnos-app/$APP_NAME.fpk"

# 5) 包内容自检：fpk 就是 tar.gz
echo "== 包内容"
tar tzf "deploy/fnos-app/$APP_NAME.fpk" | head -20
echo -n "   wizard 条目数: "; tar tzf "deploy/fnos-app/$APP_NAME.fpk" | grep -c wizard || true
echo
echo "== done: deploy/fnos-app/$APP_NAME.fpk  ($VERSION)"
echo "   安装/升级：bash deploy/fnos-app/install.sh"
