#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""drawio2vsdx - convert draw.io diagrams into Visio (.vsdx / .svg).

Pipeline:   foo.drawio  --(draw.io desktop CLI)-->  foo.svg  --(Visio COM)-->  foo.vsdx

Why not the CLI alone?  The draw.io desktop CLI can only export
pdf / png / jpg / svg / xml (verified: `drawio.exe --help`).  There is no
vsdx target, so Visio itself has to do the last hop, driven over COM.

Why the SVG and not the .drawio XML directly?  Visio can import plain SVG as
*native, editable* shapes (group -> sub-shapes -> text shapes), which keeps
text editable and selectable in Visio.  Pasting a PNG would not.

Known trap this script guards against: draw.io sometimes emits SVG text as
<switch><foreignObject>(XHTML)</foreignObject>...</switch>.  Visio ignores the
foreignObject branch, so labels vanish or turn into a single misplaced blob
(the classic "中文乱码 / 文字跑到左上角" report).  `fix-svg` rewrites those
back to plain <text> elements.  On draw.io desktop >= 20 the exporter already
emits plain <text> (verified locally), so this step is a defensive no-op there.

Usage:
    python drawio2vsdx.py doctor
    python drawio2vsdx.py convert 图.drawio                 -> 图.vsdx
    python drawio2vsdx.py convert a.drawio b.drawio --outdir out --mode svg
    python drawio2vsdx.py convert big.drawio --all-pages    -> big.p1.vsdx ...
    python drawio2vsdx.py fix-svg in.svg -o out.svg
    python drawio2vsdx.py verify 图.vsdx                    # prove text is editable
"""

from __future__ import annotations

import argparse
import html as html_mod
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

# ---------------------------------------------------------------- environment

DRAWIO_CANDIDATES = [
    r"C:\Program Files\draw.io\draw.io.exe",
    r"C:\Program Files (x86)\draw.io\draw.io.exe",
    os.path.expanduser(r"~\AppData\Local\Programs\draw.io\draw.io.exe"),
]
VISIO_CANDIDATES = [
    r"C:\Program Files\Microsoft Office\root\Office16\VISIO.EXE",
    r"C:\Program Files (x86)\Microsoft Office\root\Office16\VISIO.EXE",
    r"C:\Program Files\Microsoft Office\Office16\VISIO.EXE",
    r"C:\Program Files (x86)\Microsoft Office\Office16\VISIO.EXE",
]


def find_drawio() -> str | None:
    env = os.environ.get("DRAWIO_EXE")
    if env and Path(env).is_file():
        return env
    for c in DRAWIO_CANDIDATES:
        if Path(c).is_file():
            return c
    return shutil.which("drawio") or shutil.which("draw.io")


def find_visio() -> str | None:
    env = os.environ.get("VISIO_EXE")
    if env and Path(env).is_file():
        return env
    for c in VISIO_CANDIDATES:
        if Path(c).is_file():
            return c
    return shutil.which("visio")


def win32com_available() -> bool:
    try:
        import win32com.client  # noqa: F401
    except Exception:
        return False
    return True


def drawio_version(exe: str) -> str:
    try:
        r = subprocess.run([exe, "--version"], capture_output=True, text=True, timeout=90)
        return (r.stdout or r.stderr).strip().splitlines()[0] if (r.stdout or r.stderr).strip() else "?"
    except Exception as e:  # pragma: no cover
        return f"<{e}>"


# ------------------------------------------------------------- drawio export


def count_pages(drawio_file: Path) -> int:
    """Number of <diagram> elements in a .drawio file (1 if unknown/compressed)."""
    try:
        txt = drawio_file.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return 1
    n = len(re.findall(r"<diagram\b", txt))
    return max(1, n)


def export_svg(
    drawio_exe: str,
    src: Path,
    out_svg: Path,
    page: int | None = None,
    theme: str | None = None,
    embed_diagram: bool = False,
    timeout: int = 300,
) -> None:
    """draw.io CLI: .drawio -> .svg.  `page` is 1-based (CLI --page-index)."""
    out_svg.parent.mkdir(parents=True, exist_ok=True)
    cmd = [drawio_exe, "-x", "-f", "svg", "-o", str(out_svg)]
    if page is not None:
        cmd += ["-p", str(page)]
    if theme:
        cmd += ["--svg-theme", theme]
    if embed_diagram:
        cmd += ["-e"]
    cmd.append(str(src))
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    if not out_svg.is_file() or out_svg.stat().st_size == 0:
        tail = ((r.stdout or "") + (r.stderr or "")).strip()[-800:]
        raise RuntimeError(f"draw.io export failed for {src.name} (rc={r.returncode})\n{tail}")


# ------------------------------------------- foreignObject -> plain <text> fix

_SWITCH_RE = re.compile(r"<switch\b.*?</switch>", re.S)
_TEXT_EL_RE = re.compile(r"<text\b[^>]*>.*?</text>|<text\b[^>]*/>", re.S)
_TAGS_RE = re.compile(r"<[^>]+>")
_FO_XML_RE = re.compile(r"<foreignObject\b([^>]*)>", re.S)


def _fo_plain_text(fo_inner: str) -> str:
    """Extract readable text out of draw.io's XHTML inside foreignObject."""
    s = re.sub(r"<br\s*/?>", "\n", fo_inner, flags=re.I)
    s = re.sub(r"</(div|p|li|tr|h\d)>", "\n", s, flags=re.I)
    s = _TAGS_RE.sub("", s)
    s = html_mod.unescape(s)
    lines = [ln.strip() for ln in s.splitlines()]
    return "\n".join(ln for ln in lines if ln)


def _attr(tag: str, name: str) -> str | None:
    m = re.search(rf'\b{name}\s*=\s*"([^"]*)"', tag)
    return m.group(1) if m else None


def fix_foreign_object(svg_text: str) -> tuple[str, int]:
    """Rewrite <switch><foreignObject>…</foreignObject>…</switch> to <text>."""
    if "foreignObject" not in svg_text:
        return svg_text, 0
    fixed = 0

    def repl(m: re.Match) -> str:
        nonlocal fixed
        block = m.group(0)
        if "foreignObject" not in block:
            return block
        fixed += 1
        fo_open = _FO_XML_RE.search(block)
        fo_inner_m = re.search(r"<foreignObject\b[^>]*>(.*?)</foreignObject>", block, re.S)
        text = _fo_plain_text(fo_inner_m.group(1)) if fo_inner_m else ""

        fallback = _TEXT_EL_RE.search(block)
        if fallback and "foreignObject" not in fallback.group(0):
            open_tag = fallback.group(0)[: fallback.group(0).find(">") + 1]
        else:  # synthesize a text element centred on the foreignObject box
            attrs = fo_open.group(1) if fo_open else ""
            x = _attr("<fo " + attrs + ">", "x") or "0"
            y = _attr("<fo " + attrs + ">", "y") or "0"
            w = _attr("<fo " + attrs + ">", "width") or "0"
            h = _attr("<fo " + attrs + ">", "height") or "0"
            try:
                cx, cy = float(x) + float(w) / 2, float(y) + float(h) / 2
            except ValueError:
                cx, cy = 0.0, 0.0
            open_tag = (
                f'<text x="{cx:.1f}" y="{cy:.1f}" text-anchor="middle" '
                f'font-family="Helvetica" font-size="12" fill="#000000">'
            )

        esc = html_mod.escape(text) if text else ""
        return open_tag + esc + "</text>"

    return _SWITCH_RE.sub(repl, svg_text), fixed


def fix_svg_file(src: Path, dst: Path) -> int:
    txt = src.read_text(encoding="utf-8", errors="strict")
    out, n = fix_foreign_object(txt)
    if n:
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_text(out, encoding="utf-8")
    return n


# ------------------------------------------------------------------- Visio IO


def _shape_lines(shapes, depth: int, out: list[str], max_text: int = 60) -> int:
    """Recursively collect shapes; returns number of text-bearing shapes."""
    ntext = 0
    for i in range(1, shapes.Count + 1):
        try:
            sh = shapes.Item(i)
        except Exception:
            continue
        try:
            name = sh.Name
        except Exception:
            name = "?"
        try:
            text = (sh.Text or "").strip()
        except Exception:
            text = ""
        if text:
            ntext += 1
            shown = text.replace("\n", "\\n")
            if len(shown) > max_text:
                shown = shown[:max_text] + "…"
            label = f'text={shown!r}'
        else:
            label = "(no text)"
        out.append(f"{'    ' * depth}- {name}  {label}")
        try:
            kids = sh.Shapes if sh.Shapes.Count > 0 else None
        except Exception:
            kids = None
        if kids is not None:
            ntext += _shape_lines(kids, depth + 1, out, max_text)
    return ntext


def svg_to_vsdx(svg: Path, vsdx: Path, visible: bool = False) -> tuple[int, int]:
    """Visio COM: import SVG, save as .vsdx.  Returns (shape_count, text_count)."""
    import win32com.client  # imported lazily so `fix-svg` needs no pywin32

    svg, vsdx = Path(svg).resolve(), Path(vsdx).resolve()
    vsdx.parent.mkdir(parents=True, exist_ok=True)
    app = win32com.client.DispatchEx("Visio.Application")
    try:
        try:
            app.Visible = visible
        except Exception:
            pass
        try:
            app.ScreenUpdating = False
        except Exception:
            pass
        doc = app.Documents.Open(str(svg))
        try:
            page = doc.Pages.Item(1)
            total = page.Shapes.Count
            scratch: list[str] = []
            ntext = _shape_lines(page.Shapes, 0, scratch)
            if os.path.exists(vsdx):
                os.remove(vsdx)
            doc.SaveAs(str(vsdx))
        finally:
            doc.Close()
    finally:
        try:
            app.Quit()
        except Exception:
            pass
    if not vsdx.is_file():
        raise RuntimeError(f"Visio did not produce {vsdx}")
    return total, ntext


def dump_vsdx(vsdx: Path) -> tuple[list[str], int, int]:
    """Open a .vsdx read-only and dump its shape tree (proves text is editable)."""
    import win32com.client

    vsdx = Path(vsdx).resolve()
    app = win32com.client.DispatchEx("Visio.Application")
    try:
        try:
            app.Visible = False
        except Exception:
            pass
        doc = app.Documents.Open(str(vsdx))
        try:
            page = doc.Pages.Item(1)
            total = page.Shapes.Count
            out: list[str] = []
            ntext = _shape_lines(page.Shapes, 0, out)
        finally:
            doc.Close()
    finally:
        try:
            app.Quit()
        except Exception:
            pass
    return out, total, ntext


# ------------------------------------------------- Word / WPS 文字 文档插图


def svg_to_emf(svg: Path, emf: Path, visible: bool = False) -> Path:
    """Visio COM: import SVG and export a vector EMF (crisp at any zoom)."""
    import win32com.client

    svg, emf = Path(svg).resolve(), Path(emf).resolve()
    app = win32com.client.DispatchEx("Visio.Application")
    try:
        try:
            app.Visible = visible
        except Exception:
            pass
        doc = app.Documents.Open(str(svg))
        try:
            if emf.exists():
                emf.unlink()
            doc.Pages.Item(1).Export(str(emf))
        finally:
            doc.Close()
    finally:
        try:
            app.Quit()
        except Exception:
            pass
    if not emf.is_file() or emf.stat().st_size == 0:
        raise RuntimeError(f"Visio EMF export failed: {emf}")
    return emf


def docx_app():
    """Open the word processor over COM.

    WPS 文字 registers itself as KWPS.Application (and reports Name='Microsoft
    Word', Version='12.0'), so this works whether the machine runs WPS or real
    MS Word.
    """
    import win32com.client

    last = None
    for prog in ("KWPS.Application", "Word.Application"):
        try:
            return win32com.client.DispatchEx(prog), prog
        except Exception as e:          # try the next ProgID
            last = e
    raise RuntimeError(f"no word processor COM server (KWPS.Application / Word.Application): {last}")


def _find_marker_range(doc, marker: str):
    """Paragraph scan (works in WPS; Range.Find is flakier there).  Returns a
    Range covering just the marker text, or None."""
    try:
        n = doc.Paragraphs.Count
    except Exception:
        return None
    for i in range(1, n + 1):
        try:
            pr = doc.Paragraphs.Item(i).Range
            txt = pr.Text or ""
        except Exception:
            continue
        idx = txt.find(marker)
        if idx >= 0:
            start = pr.Start + idx
            return doc.Range(start, start + len(marker))
    return None


def insert_into_doc(doc_path: Path, media: Path, out_path: Path, mode: str = "ole",
                    at: str = "end", width_cm: float | None = None, caption: str | None = None,
                    visible: bool = False) -> dict:
    """Insert a .vsdx (as an editable OLE object) or an .emf (vector picture) into a .docx."""
    media, doc_path, out_path = Path(media).resolve(), Path(doc_path).resolve(), Path(out_path).resolve()
    app, prog = docx_app()
    info: dict = {"progid": prog, "placement": at}
    try:
        try:
            app.Visible = visible
        except Exception:
            pass
        try:
            app.DisplayAlerts = 0
        except Exception:
            pass
        doc = app.Documents.Open(str(doc_path))
        try:
            if at == "end":
                rng = doc.Range(doc.Content.End - 1, doc.Content.End - 1)
            elif at == "start":
                rng = doc.Range(0, 0)
            else:
                found = _find_marker_range(doc, at)
                if found is None:
                    raise RuntimeError(f"marker {at!r} not found in {doc_path.name}")
                start = found.Start
                found.Delete()
                rng = doc.Range(start, start)
                info["placement"] = f"marker {at!r} replaced"

            if mode == "ole":
                shp = rng.InlineShapes.AddOLEObject(ClassType="Visio.Drawing.15",
                                                    FileName=str(media), LinkToFile=False)
            else:
                shp = rng.InlineShapes.AddPicture(str(media))
            try:
                if width_cm:
                    ratio = shp.Height / shp.Width
                    shp.Width = width_cm * 28.3465
                    shp.Height = shp.Width * ratio
                info["size_pt"] = (round(shp.Width, 1), round(shp.Height, 1))
                info["shape_type"] = shp.Type      # 1 = embedded OLE object, 3 = picture
            except Exception:
                pass
            try:
                rng.Paragraphs.Item(1).Alignment = 1       # centre the diagram
            except Exception:
                pass

            if caption:
                try:
                    rng2 = doc.Range(rng.End, rng.End)
                    rng2.InsertParagraphAfter()
                    rng2 = doc.Range(rng.End + 1, rng.End + 1)
                    rng2.Text = caption
                    rng2.Paragraphs.Item(1).Alignment = 1
                    info["caption"] = caption
                except Exception as e:
                    info["caption_error"] = str(e)

            out_path.parent.mkdir(parents=True, exist_ok=True)
            same_file = os.path.normcase(str(out_path)) == os.path.normcase(str(doc_path))
            if same_file:
                doc.Save()                          # in place: the open file is locked, cannot unlink
            else:
                if out_path.exists():
                    out_path.unlink()
                doc.SaveAs(str(out_path), 16)      # wdFormatDocumentDefault (.docx)
        finally:
            doc.Close(0)                            # wdDoNotSaveChanges
    finally:
        try:
            app.Quit()
        except Exception:
            pass
    if not out_path.is_file():
        raise RuntimeError(f"word processor did not write {out_path}")
    info["out"] = str(out_path)
    info["out_bytes"] = out_path.stat().st_size
    return info


def inspect_docx(path: Path) -> dict:
    """Prove what actually landed inside the .docx (OLE bin / ProgID / media)."""
    import zipfile

    res: dict = {"ole": [], "media": [], "progids": [], "ole_tags": []}
    with zipfile.ZipFile(path) as z:
        for n in z.namelist():
            if n.endswith("/"):
                continue                      # directory entries carry no payload
            if "embeddings/" in n:
                b = z.read(n)
                res["ole"].append((n, len(b)))
                for pat in (b"Visio.Drawing.15", b"Visio.Drawing.11", b"Visio.Drawing.5"):
                    if pat in b:
                        res["progids"].append(pat.decode())
            elif n.startswith("word/media/"):
                res["media"].append((n, z.getinfo(n).file_size))
        try:
            doc = z.read("word/document.xml").decode("utf-8", "ignore")
            res["ole_tags"] = re.findall(r'<o:OLEObject[^>]*ProgID="([^"]+)"', doc)
            res["text"] = "".join(re.findall(r"<w:t[^>]*>([^<]*)</w:t>", doc))
        except Exception:
            pass
    return res


def cmd_word(a) -> int:
    import tempfile

    src = Path(a.input)
    if not src.is_file():
        print(f"error: no such file: {src}", file=sys.stderr)
        return 2
    target_doc = Path(a.doc)
    if not target_doc.is_file():
        print(f"error: no such document: {target_doc}", file=sys.stderr)
        return 2
    if a.in_place:
        out = target_doc
    elif a.output:
        out = Path(a.output)
    else:
        out = target_doc.with_name(target_doc.stem + "_插图" + target_doc.suffix)

    tmp = Path(tempfile.mkdtemp(prefix="d2w-"))
    try:
        vsdx = svg = None
        if src.suffix.lower() == ".vsdx":
            vsdx = src
        else:
            if src.suffix.lower() == ".drawio":
                drawio = find_drawio()
                if not drawio:
                    print("error: draw.io Desktop CLI not found; set DRAWIO_EXE", file=sys.stderr)
                    return 2
                svg = tmp / (src.stem + ".svg")
                export_svg(drawio, src, svg, theme=a.theme)
            elif src.suffix.lower() == ".svg":
                svg = src
            else:
                print(f"error: unsupported input {src.suffix} (use .drawio / .svg / .vsdx)", file=sys.stderr)
                return 2
            if svg is not src and fix_svg_file(svg, svg):
                pass
            print(f"[ok]   SVG   {svg}" + ("" if svg is src else "  (temp)"))

        if a.mode == "ole":
            if vsdx is None:
                vsdx = tmp / (src.stem + ".vsdx")
                total, ntext = svg_to_vsdx(svg, vsdx, visible=a.visible)
                print(f"[ok]   VSDX  {vsdx}   ({total} shapes, {ntext} text shapes)  (temp)")
            else:
                print(f"[ok]   VSDX  {vsdx}   (given)")
            media = vsdx
        else:                                       # --mode picture needs a vector EMF
            if svg is None:
                print("error: --mode picture needs a .drawio or .svg input", file=sys.stderr)
                return 2
            emf = tmp / (src.stem + ".emf")
            svg_to_emf(svg, emf, visible=a.visible)
            print(f"[ok]   EMF   {emf}   ({emf.stat().st_size:,} B, vector)  (temp)")
            media = emf

        if a.in_place:
            backup = target_doc.with_name(target_doc.stem + ".bak" + target_doc.suffix)
            shutil.copy2(target_doc, backup)
            print(f"      backup: {backup}")
        info = insert_into_doc(target_doc, media, out, mode=a.mode, at=a.at,
                               width_cm=a.width_cm, caption=a.caption, visible=a.visible)
        size = f", {info['size_pt'][0]}x{info['size_pt'][1]} pt" if info.get("size_pt") else ""
        print(f"[ok]   DOCX  {out}   ({info['out_bytes']:,} B, {info['progid']}, "
              f"at {info['placement']}{size})")

        chk = inspect_docx(out)
        if a.mode == "ole":
            if chk["ole"] and chk["ole_tags"]:
                print(f"[ok]   embedded Visio object: {chk['ole_tags'][0]}, "
                      f"{chk['ole'][0][0]} {chk['ole'][0][1]:,} B — double-click opens Visio")
            else:
                print("[warn] no embedded OLE object found in the saved .docx")
        for n, sz in chk["media"]:
            print(f"       media {n} {sz:,} B")
        if a.at not in ("end", "start") and a.at not in (chk.get("text") or ""):
            print(f"[ok]   marker {a.at!r} no longer in the text (replaced by the diagram)")
    finally:
        if a.keep_temp:
            print(f"      temp kept: {tmp}")
        else:
            shutil.rmtree(tmp, ignore_errors=True)
    return 0


# ------------------------------------------------------------------ commands


def cmd_doctor(a) -> int:
    ok = True
    print("drawio2vsdx doctor")
    print("-" * 58)
    d = find_drawio()
    if d:
        print(f"[ok]   draw.io  : {d}  (version {drawio_version(d)})")
    else:
        ok = False
        print("[FAIL] draw.io  : not found — install draw.io Desktop, or set DRAWIO_EXE")
    v = find_visio()
    if v:
        print(f"[ok]   Visio    : {v}")
    else:
        print("[warn] Visio    : not found — .vsdx output unavailable (SVG export still works); set VISIO_EXE if installed elsewhere")
    if win32com_available():
        print("[ok]   pywin32   : importable")
    else:
        ok = False
        print("[FAIL] pywin32   : missing — run: python -m pip install pywin32  (needed for .vsdx)")
    print("-" * 58)
    print("VERDICT:", "ready for .drawio -> .vsdx" if (ok and v) else
          ("SVG-only mode" if ok else "cannot convert yet"))
    return 0 if ok else 1


def _convert_one(
    src: Path, outdir: Path | None, args, drawio: str, visio: str | None
) -> int:
    mode = args.mode
    if mode == "auto":
        mode = "vsdx" if (visio and win32com_available()) else "svg"
        if mode == "svg":
            print("      note: Visio or pywin32 unavailable -> writing SVG only")
    outdir = outdir or src.parent
    stamp = None
    if args.all_pages:
        n = count_pages(src)
        pages = list(range(1, n + 1))
        if n > 1:
            print(f"      {n} pages detected -> one output per page")
    else:
        pages = [args.page]

    rc = 0
    for pg in pages:
        stem = src.stem
        if args.all_pages and len(pages) > 1:
            stem = f"{stem}.p{pg}"
        svg = outdir / f"{stem}.svg"
        try:
            export_svg(drawio, src, svg, page=pg, theme=args.theme,
                       embed_diagram=args.embed_diagram)
        except Exception as e:
            print(f"[FAIL] {src.name} page {pg}: {e}")
            rc = 1
            continue

        n_fix = 0
        if args.rewrite_foreignobject or mode == "vsdx":
            try:
                n_fix = fix_svg_file(svg, svg)
            except Exception as e:
                print(f"      warn: foreignObject rewrite skipped ({e})")
        if n_fix:
            print(f"      rewrote {n_fix} <foreignObject> block(s) -> plain <text>")

        print(f"[ok]   SVG   {svg}" + (f"   (page {pg})" if pg else ""))

        if mode == "vsdx":
            vsdx = outdir / f"{stem}.vsdx"
            try:
                total, ntext = svg_to_vsdx(svg, vsdx, visible=args.visible)
            except Exception as e:
                print(f"[FAIL] Visio import for {src.name}: {e}")
                rc = 1
                continue
            size = vsdx.stat().st_size
            print(f"[ok]   VSDX  {vsdx}   ({total} top-level shapes, "
                  f"{ntext} text shapes, {size:,} B)")
            if ntext == 0 and total > 0:
                print("      warn: no text shapes found — check the diagram in Visio")
            if not args.keep_svg:
                try:
                    svg.unlink()
                    print(f"      removed intermediate {svg.name} (use --keep-svg to keep)")
                except Exception:
                    pass
    return rc


def cmd_convert(a) -> int:
    drawio = find_drawio()
    if not drawio:
        print("error: draw.io Desktop CLI not found; set DRAWIO_EXE", file=sys.stderr)
        return 2
    visio = find_visio()
    inputs: list[Path] = []
    for raw in a.input:
        p = Path(raw)
        if p.is_dir():
            pat = "**/*.drawio" if a.recursive else "*.drawio"
            inputs += sorted(p.glob(pat))
        elif p.is_file():
            inputs.append(p)
        else:
            print(f"error: no such file: {p}", file=sys.stderr)
            return 2
    if not inputs:
        print("error: no .drawio input found", file=sys.stderr)
        return 2
    outdir = Path(a.outdir) if a.outdir else None
    if outdir:
        outdir.mkdir(parents=True, exist_ok=True)
    rc = 0
    for i, src in enumerate(inputs, 1):
        print(f"({i}/{len(inputs)}) {src}")
        rc |= _convert_one(src, outdir, a, drawio, visio)
    return rc


def cmd_fix_svg(a) -> int:
    src = Path(a.input)
    dst = Path(a.output) if a.output else src
    if not src.is_file():
        print(f"error: no such file: {src}", file=sys.stderr)
        return 2
    n = fix_svg_file(src, dst)
    if n:
        print(f"rewrote {n} <foreignObject> block(s) -> {dst}")
    else:
        print("nothing to do: no <foreignObject> found (draw.io already emits plain <text>)")
    return 0


def cmd_verify(a) -> int:
    p = Path(a.input)
    if not p.is_file():
        print(f"error: no such file: {p}", file=sys.stderr)
        return 2
    if not win32com_available():
        print("error: pywin32 missing (python -m pip install pywin32)", file=sys.stderr)
        return 2
    lines, total, ntext = dump_vsdx(p)
    print(f"{p}  ({p.stat().st_size:,} B)")
    print(f"page 1: {total} top-level shape(s), {ntext} text-bearing shape(s), "
          f"{len(lines)} node(s) total")
    print("-" * 58)
    print("\n".join(lines[: a.limit]))
    if len(lines) > a.limit:
        print(f"... {len(lines) - a.limit} more node(s) (use --limit 0 for all)")
    return 0 if ntext else 1


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="drawio2vsdx",
        description="Convert draw.io diagrams to Visio .vsdx (or Visio-friendly SVG).",
    )
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("doctor", help="check draw.io + Visio + pywin32 availability").set_defaults(func=cmd_doctor)

    c = sub.add_parser("convert", help=".drawio -> .vsdx / .svg")
    c.add_argument("input", nargs="+", help=".drawio file(s) or folder(s)")
    c.add_argument("-o", "--outdir", help="output folder (default: next to the input)")
    c.add_argument("--mode", choices=["auto", "vsdx", "svg"], default="auto")
    c.add_argument("-p", "--page", type=int, default=None, metavar="N",
                   help="single page number (1-based); default = first page")
    c.add_argument("--all-pages", action="store_true", help="export every page (one file per page)")
    c.add_argument("--theme", choices=["light", "dark", "auto"], default="light",
                   help="SVG colour theme (default light = best for Visio)")
    c.add_argument("--embed-diagram", action="store_true",
                   help="keep the .drawio XML inside the SVG (re-editable in draw.io)")
    c.add_argument("--rewrite-foreignobject", action="store_true",
                   help="force the foreignObject-><text> rewrite (auto for vsdx)")
    c.add_argument("--keep-svg", action="store_true", help="keep the intermediate SVG")
    c.add_argument("--recursive", action="store_true", help="recurse into sub-folders")
    c.add_argument("--visible", action="store_true", help="show the Visio window while working")
    c.set_defaults(func=cmd_convert)

    f = sub.add_parser("fix-svg", help="rewrite <foreignObject> text to plain <text>")
    f.add_argument("input", help="SVG file (in place by default)")
    f.add_argument("-o", "--output", help="output SVG (default: overwrite input)")
    f.set_defaults(func=cmd_fix_svg)

    w = sub.add_parser("word", help="insert the diagram into a .docx (WPS 文字 / MS Word) as an editable Visio object")
    w.add_argument("input", help=".drawio / .svg / .vsdx to place into the document")
    w.add_argument("-d", "--doc", required=True, help="target .docx document")
    w.add_argument("-o", "--output", help="output .docx (default: <doc>_插图.docx)")
    w.add_argument("--in-place", action="store_true",
                   help="overwrite the original document (a .bak copy is written first)")
    w.add_argument("--at", default="end", metavar="end|start|MARKER",
                   help="where to put it: end / start / a marker text to replace (e.g. '{{流程图}}')")
    w.add_argument("--mode", choices=["ole", "picture"], default="ole",
                   help="ole = editable Visio object (default); picture = vector EMF image")
    w.add_argument("--theme", choices=["light", "dark", "auto"], default="light")
    w.add_argument("--width-cm", type=float, help="scale the diagram to this width")
    w.add_argument("--caption", help="caption line inserted under the diagram")
    w.add_argument("--keep-temp", action="store_true", help="keep intermediate SVG/VSDX/EMF files")
    w.add_argument("--visible", action="store_true", help="show Visio / WPS windows while working")
    w.set_defaults(func=cmd_word)

    v = sub.add_parser("verify", help="dump a .vsdx shape/text structure (proves text is editable)")
    v.add_argument("input", help=".vsdx file")
    v.add_argument("--limit", type=int, default=60, help="max nodes to print (0 = all)")
    v.set_defaults(func=cmd_verify)

    a = ap.parse_args(argv)
    if getattr(a, "limit", None) == 0:
        a.limit = 10 ** 9
    return a.func(a)


if __name__ == "__main__":
    sys.exit(main())
