# Troubleshooting Win Mingw Bootstrap

## Symptom: `error while loading shared libraries: libmpfr-6.dll`

`cc1.exe` needs `libmpfr-6.dll` for multiprecision arithmetic. It's **not** in the `gcc` package — it's split out into `mingw-w64-ucrt-x86_64-mpfr`. The base SKILL.md includes it; if you trimmed packages, re-add.

Other typical missing-DLL → package mappings:

| DLL | Package |
|---|---|
| `libgmp-10.dll` / `libgmpxx-4.dll` | `mingw-w64-ucrt-x86_64-gmp` |
| `libmpfr-6.dll` | `mingw-w64-ucrt-x86_64-mpfr` |
| `libmpc-3.dll` | `mingw-w64-ucrt-x86_64-mpc` |
| `libisl-*.dll` | `mingw-w64-ucrt-x86_64-isl` |
| `libzstd.dll` | `mingw-w64-ucrt-x86_64-zstd` |
| `libz.dll` | `mingw-w64-ucrt-x86_64-zlib` |
| `libiconv-2.dll` | `mingw-w64-ucrt-x86_64-libiconv` |
| `api-ms-win-*.dll` (UCRT) | (Windows itself, in `System32\downlevel\`) |
| `libwinpthread-1.dll` | `mingw-w64-ucrt-x86_64-winpthreads-git` |

Resolution path: read the missing-DLL name → grep the Tsinghua index page → download → extract → retry.

## Symptom: `ld returned 1 exit status`

Almost always a missing linker object, not a real linker bug. Things to try in order:
1. Re-extract `windows-default-manifest` (specifically `ucrt64/lib/default-manifest.o`).
2. Check `ucrt64/lib/crt2.o` and `ucrt64/lib/libmingw32.a` exist (come from `crt-git`).
3. `gcc -v helloworld.c -o helloworld.exe` and look for the actual error message in collect2/ld output.

## Symptom: `gcc: command not found` even after `export PATH=...`

The shell you're in is not picking up your export. Verify with `which gcc` or `command -v gcc`. Common confusion: shell sub-process (e.g. `go build` spawning cgo) does inherit env, but Bash `2>/dev/null | tee` pipelines sometimes drop env. Use absolute path or `source ./env.sh`.

## Symptom: GUI builds (Fyne) succeed but the binary crashes with "missing DLL" on a different machine

It's missing `libgcc_s_seh-1.dll` / `libstdc++-6.dll`. Either:
- ship them alongside the .exe (recommended), or
- link statically with `-ldflags '-extldflags "-static"'` (only works for cgo, doubles exe size).

## Symptom: `gcc` exits silently (no stdout, no stderr, exit 1)

Almost always `cc1.exe` missing a DLL at startup. Run `gcc -v` to force gcc to print the COLLECT options; the failure will become visible. Most common: UCRT forwarder missing — re-copy from `System32\downlevel`.

## Symptom: Go cgo says `CGO_ENABLED=0 is required` even with `export CGO_ENABLED=1`

Make sure you're not setting `CGO_ENABLED=0` further down in the shell. `CGO_ENABLED` only matters if a C compiler is reachable; check `go env CC` and `go env CGO_ENABLED`.
