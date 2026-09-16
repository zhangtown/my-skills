#!/usr/bin/env bash
# win-mingw-toolchain-bootstrap/bootstrap.sh
# Sets up a self-contained mingw-w64 GCC 15.2.0 toolchain under ./.toolchain/
# Safe to re-run (skips already-downloaded pkgs).

set -euo pipefail

TC="${1:-$PWD/.toolchain}"
echo "[bootstrap] target = $TC"
mkdir -p "$TC/pkgs" "$TC/root"

BASE="https://mirrors.tuna.tsinghua.edu.cn/msys2/mingw/ucrt64"
WIN_TAR="/c/Windows/System32/tar.exe"

BASE_PKGS=(
  "mingw-w64-ucrt-x86_64-headers-git-13.0.0.r380.gb83511db8-1-any.pkg.tar.zst"
  "mingw-w64-ucrt-x86_64-crt-git-13.0.0.r380.gb83511db8-1-any.pkg.tar.zst"
  "mingw-w64-ucrt-x86_64-winpthreads-git-12.0.0.r747.g1a99f8514-1-any.pkg.tar.zst"
  "mingw-w64-ucrt-x86_64-gcc-15.2.0-14-any.pkg.tar.zst"
  "mingw-w64-ucrt-x86_64-gcc-libs-15.2.0-14-any.pkg.tar.zst"
  "mingw-w64-ucrt-x86_64-binutils-2.47-3-any.pkg.tar.zst"
  "mingw-w64-ucrt-x86_64-windows-default-manifest-20260815-1-any.pkg.tar.zst"
)

MATH_PKGS=(
  "mingw-w64-ucrt-x86_64-gmp-6.3.0-2-any.pkg.tar.zst"
  "mingw-w64-ucrt-x86_64-mpfr-4.2.2-3-any.pkg.tar.zst"
  "mingw-w64-ucrt-x86_64-mpc-1.3.1-2-any.pkg.tar.zst"
  "mingw-w64-ucrt-x86_64-isl-0.27-1-any.pkg.tar.zst"
  "mingw-w64-ucrt-x86_64-zstd-1.5.7-2-any.pkg.tar.zst"
  "mingw-w64-ucrt-x86_64-zlib-1.3.2-2-any.pkg.tar.zst"
  "mingw-w64-ucrt-x86_64-libiconv-1.18-1-any.pkg.tar.zst"
)

cd "$TC/pkgs"
echo "[bootstrap] Downloading ${#BASE_PKGS[@]} base packages..."
for f in "${BASE_PKGS[@]}"; do
  if [ ! -s "$f" ]; then
    curl -s --noproxy "*" --max-time 300 -O "$BASE/$f" || { echo "FAIL: $f"; exit 1; }
  fi
done
echo "[bootstrap] Downloading ${#MATH_PKGS[@]} math packages..."
for f in "${MATH_PKGS[@]}"; do
  if [ ! -s "$f" ]; then
    curl -s --noproxy "*" --max-time 120 -O "$BASE/$f" || { echo "FAIL: $f"; exit 1; }
  fi
done

cd "$TC"
echo "[bootstrap] Extracting packages to root/..."
for f in pkgs/*.pkg.tar.zst; do
  "$WIN_TAR" -x -C root -f "$(cygpath -w "$PWD/$f")"
done

echo "[bootstrap] Copying UCRT API-set forwarders next to cc1.exe..."
mkdir -p root/ucrt64/lib/gcc/x86_64-w64-mingw32/15.2.0/
cp /c/Windows/System32/downlevel/api-ms-win-crt-*.dll \
   root/ucrt64/lib/gcc/x86_64-w64-mingw32/15.2.0/

echo "[bootstrap] Smoke test..."
export PATH="$TC/root/ucrt64/bin:$PATH"
TMPH=$(cygpath -w "$(mktemp -d)")
echo 'int main(){return 0;}' > "$TMPH/h.c"
gcc "$TMPH/h.c" -o "$TMPH/h.exe" && "$TMPH/h.exe" && echo "[bootstrap] OK"
rm -rf "$TMPH"

echo "[bootstrap] Done. Add to your build:"
echo "  export PATH=\"\\\"$TC/root/ucrt64/bin:\\\$PATH\\\"\""
echo "  export CC=gcc"
echo "  CGO_ENABLED=1 go build ..."
