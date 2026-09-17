---
name: win-mingw-toolchain-bootstrap
description: >-
  This skill should be used when a Windows machine needs a working mingw-w64 GCC toolchain to
  build CGo-based Go programs (e.g. Fyne GUI) and GitHub release zips are throttled by the
  corporate proxy at ~5 KB/s. It downloads the exact set of msys2 ucrt64 packages from the
  Tsinghua mirror (verified 5 MB/s in this sandbox), stitches them into a self-contained
  project-local `.toolchain/` directory that just works for `CGO_ENABLED=1 go build`, and
  documents the two non-obvious blockers: missing UCRT API-set forwarders (`api-ms-win-*.dll`,
  found only in `C:\Windows\System32\downlevel\`) and missing math-library runtimes
  (gmp/mpfr/mpc/isl/zstd/zlib/libiconv). Use when GUI builds fail with `error while loading shared
  libraries: api-ms-win-crt-utility-l1-1-0.dll` or when w64devkit / MSYS2 download is too slow.
agent_created: true
---

# Win Mingw Toolchain Bootstrap

## Overview

Set up a self-contained mingw-w64 GCC 15.2.0 toolchain under any project root for building CGo Go programs (Fyne GUI, cgo plugins, anything requiring a C compiler) on Windows, **without** needing GitHub downloads or admin install. Builds directly from the Tsinghua msys2 mirror at LAN-speed (5 MB/s in this sandbox).

## When to Use

- Your Go code uses CGo (e.g. `fyne.io/fyne/v2` GUI) and `go build` fails with `error while loading shared libraries: api-ms-win-crt-utility-l1-1-0.dll`
- You don't have admin rights to install MSYS2 or Visual Studio Build Tools
- GitHub release-asset download (w64devkit) is being throttled to ~5 KB/s by your corporate proxy
- You want a self-contained toolchain that can be re-deployed by copying one directory

## Prerequisites

- Windows 10+ (`ver` reports 10.0.x). UCRT API-set forwarders in `System32\downlevel\` are required and pre-installed.
- Any shell that has `curl` and access to Windows `C:\Windows\System32\tar.exe` (Win10 1803+ ships with zstd support).
- `python.exe` is **optional** — used only for an extra pip-based zstd fallback we will not hit.

## Quick Start

From any project that needs the toolchain (e.g. `D:\ProgramData\RemoteNet`):

```bash
TC="$PWD/.toolchain"   # toolchain root directory
mkdir -p "$TC/pkgs" "$TC/root"

# 1. Download the seven base packages from Tsinghua msys2 mirror
cd "$TC/pkgs"
BASE="https://mirrors.tuna.tsinghua.edu.cn/msys2/mingw/ucrt64"
for f in \
  mingw-w64-ucrt-x86_64-headers-git-13.0.0.r380.gb83511db8-1-any.pkg.tar.zst \
  mingw-w64-ucrt-x86_64-crt-git-13.0.0.r380.gb83511db8-1-any.pkg.tar.zst \
  mingw-w64-ucrt-x86_64-winpthreads-git-12.0.0.r747.g1a99f8514-1-any.pkg.tar.zst \
  mingw-w64-ucrt-x86_64-gcc-15.2.0-14-any.pkg.tar.zst \
  mingw-w64-ucrt-x86_64-gcc-libs-15.2.0-14-any.pkg.tar.zst \
  mingw-w64-ucrt-x86_64-binutils-2.47-3-any.pkg.tar.zst \
  mingw-w64-ucrt-x86_64-windows-default-manifest-20260815-1-any.pkg.tar.zst; do
  curl -s --noproxy "*" --max-time 300 -O "$BASE/$f"
done

# 2. Extract them (use -C so paths land under root/)
cd "$TC"
for f in pkgs/*.pkg.tar.zst; do
  /c/Windows/System32/tar.exe -x -C root -f "$(cygpath -w "$PWD/$f")"
done

# 3. Download + extract math libraries (these are what cc1.exe links to at runtime)
cd "$TC/pkgs"
for f in \
  mingw-w64-ucrt-x86_64-gmp-6.3.0-2-any.pkg.tar.zst \
  mingw-w64-ucrt-x86_64-mpfr-4.2.2-3-any.pkg.tar.zst \
  mingw-w64-ucrt-x86_64-mpc-1.3.1-2-any.pkg.tar.zst \
  mingw-w64-ucrt-x86_64-isl-0.27-1-any.pkg.tar.zst \
  mingw-w64-ucrt-x86_64-zstd-1.5.7-2-any.pkg.tar.zst \
  mingw-w64-ucrt-x86_64-zlib-1.3.2-2-any.pkg.tar.zst \
  mingw-w64-ucrt-x86_64-libiconv-1.18-1-any.pkg.tar.zst; do
  curl -s --noproxy "*" --max-time 120 -O "$BASE/$f"
done
cd "$TC"
for pkg in gmp-6.3.0-2 mpfr-4.2.2-3 mpc-1.3.1-2 isl-0.27-1 zstd-1.5.7-2 zlib-1.3.2-2 libiconv-1.18-1; do
  f=$(ls pkks/mingw-w64-ucrt-x86_64-${pkg}-any.pkg.tar.zst 2>/dev/null || ls pkgs/mingw-w64-ucrt-x86_64-${pkg}-any.pkg.tar.zst)
  /c/Windows/System32/tar.exe -x -C root -f "$(cygpath -w "$f")"
done

# 4. THE TRICK THAT MAKES IT WORK: copy UCRT API-set forwarders next to cc1.exe
#    (Search-path order: app dir → PATH → KnownDLLs. downlevel/ is none of these.)
mkdir -p root/ucrt64/lib/gcc/x86_64-w64-mingw32/15.2.0/
cp /c/Windows/System32/downlevel/api-ms-win-crt-*.dll \
   root/ucrt64/lib/gcc/x86_64-w64-mingw32/15.2.0/

# 4b. TWO MORE SILENT KILLERS (found 2026-09-05): gcc/cc1 need libwinpthread-1.dll
#     and ld/objdump need libintl-8.dll — the package list above covers neither.
#     Symptom: the process dies with exit 0xC0000135 (STATUS_DLL_NOT_FOUND) and
#     ZERO stderr, so cgo only says "cgo.exe: exit status 2". Worse: it reproduces
#     only from a clean Explorer PATH — a Git-Bash shell masks it because
#     C:\Program Files\Git\mingw64\bin (on bash's PATH) supplies both DLLs.
#     Smoke-test with a PATH that does NOT include Git's dirs, not just bash.
#     Fix: copy both from Git for Windows, or add the msys2 packages
#     (mingw-w64-ucrt-x86_64-libwinpthread-git / -gettext) to the download loop.
for f in /c/Program\ Files/Git/mingw64/bin/libwinpthread-1.dll \
         /c/Program\ Files/Git/mingw64/bin/libintl-8.dll; do
  [ -f "$f" ] && cp "$f" root/ucrt64/bin/
done
[ -f root/ucrt64/bin/libwinpthread-1.dll ] && \
  cp root/ucrt64/bin/libwinpthread-1.dll \
     root/ucrt64/lib/gcc/x86_64-w64-mingw32/15.2.0/

# 5. Smoke-test — must run WITHOUT Git dirs on PATH to be meaningful
export PATH="$TC/root/ucrt64/bin:/c/Windows/System32:/c/Windows"
echo 'int main(){return 0;}' > h.c
gcc h.c -o h.exe && ./h.exe   # expect rc=0
ld --version >/dev/null       # expect rc=0 (libintl check)
rm -f h.c h.exe
```

If your real project hits *another* missing DLL (e.g. `libgomp-1.dll`), inspect the failing name and pull the matching `mingw-w64-ucrt-x86_64-<name>-*.pkg.tar.zst` from the same mirror.

## Build Integration

For CGo projects, set two env vars before `go build`:

```bash
export PATH="$PWD/.toolchain/root/ucrt64/bin:$PATH"
export CC=gcc
CGO_ENABLED=1 go build -o dist/<project>.exe ./cmd/<main>
```

`go build` finds `gcc`, forks `cc1.exe` with the right `-B` / `-I` / `-L` flags, and links via the bundled `bin/ld.exe`. No Go toolchain config change is required.

## Version Pinning (Aug 2026)

| Package | Version |
|---|---|
| gcc | 15.2.0-14 (MSYS2 pkgtype=split; built-in specs, no .specs file shipped) |
| headers / crt | git-13.0.0.r380.gb83511db8-1 |
| winpthreads | git-12.0.0.r747.g1a99f8514-1 |
| binutils | 2.47-3 |
| gmp / mpfr / mpc / isl | 6.3.0 / 4.2.2 / 1.3.1 / 0.27 |
| zstd / zlib / libiconv | 1.5.7 / 1.3.2 / 1.18 |
| windows-default-manifest | 20260815-1 |

Refresh by re-listing the mirror page: `curl -s --noproxy "*" https://mirrors.tuna.tsinghua.edu.cn/msys2/mingw/ucrt64/ | grep -oE 'mingw-w64-ucrt-x86_64-gcc-15\.[0-9.]+-[0-9]+-any\.pkg\.tar\.zst' | sort -u | tail -1`.

## Gotchas (Discovered During Bootstrapping)

1. **UCRT forwarders** — `api-ms-win-*.dll` live in `System32\downlevel\` on Win10+, not the standard search path. `cc1.exe` (UCRT-linked) fails with `error while loading shared libraries`. Fix: copy them next to cc1.exe.
2. **PATH `ucrt64/bin` alone is not enough** — Windows DLL search starts from the *application* directory, then PATH. Putting them in `ucrt64/bin` does not help cc1.exe living in `ucrt64/lib/gcc/.../15.2.0/`.
3. **msys2 gcc is split (`pkgtype=split`)** — the `gcc-15.2.0-14` package has `cc1.exe / cc1plus.exe / collect2.exe / lto-wrapper.exe` but no `specs` file. This is **fine**: gcc falls back to compiled-in specs. The "missing specs" theory was a dead-end; the real culprit was always UCRT forwarders.
4. **tar.exe from Git Bash (libarchive) differs from Windows tar** — use `/c/Windows/System32/tar.exe` (Win10+, supports zstd, knows Windows paths via `-C`).
5. **`--noproxy "*"` breaks GitHub redirects** (302 not followed). Leave curl default for GitHub URLs even when mirror speeds matter.
6. **`/tmp` in Git Bash can silently lose files** — write to `D:/` or absolute paths whenever a file's survival is critical (e.g. `curl -o d:/foo.html`).
7. **`go build` > 2 min gets SIGTERM** in this WorkBuddy sandbox — always `run_in_background: true` for the real GUI build; foreground is fine for vet / list / `-E` dry runs.

## Verification

After running the Quick Start:

```bash
export PATH="$PWD/.toolchain/root/ucrt64/bin:$PATH"
gcc --version   # expect 15.2.0 (Rev14, Built by MSYS2 project)
```

A passing CGo build is the real test:

```bash
CC=gcc CGO_ENABLED=1 go build ./<your-cgo-package>
```

Should produce a working `.exe` with no DLL load errors at startup (other than possibly `libgcc_s_seh-1.dll` if your exe is moved away from the toolchain — embed it via `go build -ldflags '-extldflags "-static"'` or ship it beside the binary).

## What This Skill Does NOT Cover

- msvc/clang (you do not have Visual Studio).
- Cross-compilation from Linux/WSL.
- Producing a single statically-linked binary — msys2's runtime DLLs (`libstdc++-6.dll`, `libgcc_s_seh-1.dll`) must ship beside your `.exe` or be pulled from system32 (Win10+ only).

## Resources

### scripts/
- `bootstrap.sh` — full copy-paste bootstrap script (single-shot usable).

### references/
- `troubleshooting.md` — diagnosing additional DLL load errors that turn up for specific projects.
