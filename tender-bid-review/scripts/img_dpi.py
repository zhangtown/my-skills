#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
有效 DPI 审计 —— 证明材料的清晰度到底够不够。

关键概念：判断"打印出来会不会糊"不能看图片文件本身多少像素，要看它
在文档里被放大到了多大。一张 4000px 的图拉满 A4 整页，有效分辨率可能
只有 120 dpi。

    有效 DPI = 像素宽 ÷ 文档内显示宽度（英寸）

显示宽度取自段落的 wp:extent（EMU；1 inch = 914400 EMU，1 cm = 360000 EMU）。

判读口径（实测标定）：
    ≥300 印刷级 | 200–300 良好 | 150–200 及格
    120–150 偏弱（数字/英文/小字发虚）
    <120  不合格（评委核对可量化指标会很吃力）

用法：
    python img_dpi.py 投标文件.docx
    python img_dpi.py 投标文件.docx --map            # 带上下文，看图文对应
    python img_dpi.py 投标文件.docx --only-weak      # 只列低于阈值的
    python img_dpi.py 投标文件.docx --threshold 150
    python img_dpi.py 投标文件.docx --json out.json
"""

import argparse
import json
import re
import struct
import sys
import zipfile
from xml.etree import ElementTree as ET

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
R = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
A = "{http://schemas.openxmlformats.org/drawingml/2006/main}"
WP = "{http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing}"
V = "{urn:schemas-microsoft-com:vml}"

EMU_PER_CM = 360000
CM_PER_INCH = 2.54


# ---------- 图片尺寸解析（不依赖 PIL） ----------

def img_size(data):
    """返回 (宽px, 高px) 或 None。"""
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        w, h = struct.unpack(">II", data[16:24])
        return w, h
    if data[:3] == b"GIF":
        w, h = struct.unpack("<HH", data[6:10])
        return w, h
    if data[:2] == b"BM":
        w, h = struct.unpack("<ii", data[18:26])
        return abs(w), abs(h)
    if data[:2] == b"\xff\xd8":  # JPEG：扫 SOF 标记
        i = 2
        n = len(data)
        while i < n - 9:
            if data[i] != 0xFF:
                i += 1
                continue
            marker = data[i + 1]
            if marker in (0xD8, 0x01) or 0xD0 <= marker <= 0xD7:
                i += 2
                continue
            seglen = struct.unpack(">H", data[i + 2:i + 4])[0]
            if marker in (0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7,
                          0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF):
                h, w = struct.unpack(">HH", data[i + 5:i + 9])
                return w, h
            i += 2 + seglen
        return None
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        ck = data[12:16]
        if ck == b"VP8 ":
            w, h = struct.unpack("<HH", data[26:30])
            return w & 0x3FFF, h & 0x3FFF
        if ck == b"VP8L":
            b = data[21:25]
            bits = struct.unpack("<I", b)[0]
            return (bits & 0x3FFF) + 1, ((bits >> 14) & 0x3FFF) + 1
        if ck == b"VP8X":
            w = int.from_bytes(data[24:27], "little") + 1
            h = int.from_bytes(data[27:30], "little") + 1
            return w, h
        return None
    if data[:4] == b"\x01\x00\x00\x00":  # EMF（矢量）
        return None
    return None


def emf_size_cm(data):
    """EMF 是矢量：从 rclFrame（.01 mm）拿物理尺寸。"""
    try:
        if len(data) < 88:
            return None
        # EMF 头：iType(4) nSize(4) rclBounds(16) rclFrame(16) ...
        left, top, right, bottom = struct.unpack("<iiii", data[8 + 16:8 + 32])
        w_cm = (right - left) / 1000.0
        h_cm = (bottom - top) / 1000.0
        if 0 < w_cm < 200 and 0 < h_cm < 200:
            return round(w_cm, 2), round(h_cm, 2)
    except struct.error:
        pass
    return None


# ---------- 文档遍历 ----------

def load_rels(zf):
    out = {}
    try:
        root = ET.fromstring(zf.read("word/_rels/document.xml.rels"))
    except (KeyError, ET.ParseError):
        return out
    for rel in root:
        out[rel.get("Id")] = rel.get("Target", "")
    return out


def para_images(p, rels):
    """[(media名, 显示宽cm, 显示高cm)]"""
    rids = []
    for blip in p.iter(A + "blip"):
        rid = blip.get(R + "embed")
        if rid:
            rids.append(rid)
    for img in p.iter(V + "imagedata"):
        rid = img.get(R + "id")
        if rid:
            rids.append(rid)

    dims = []
    for ex in p.iter(WP + "extent"):
        try:
            cx, cy = int(ex.get("cx", 0)), int(ex.get("cy", 0))
            if cx:
                dims.append((round(cx / EMU_PER_CM, 2), round(cy / EMU_PER_CM, 2)))
        except (TypeError, ValueError):
            pass
    for sh in p.iter(V + "shape"):
        m = re.search(r"width:([\d.]+)pt;height:([\d.]+)pt", sh.get("style", "") or "")
        if m:
            dims.append((round(float(m.group(1)) / 72 * CM_PER_INCH, 2),
                         round(float(m.group(2)) / 72 * CM_PER_INCH, 2)))

    out = []
    for i, rid in enumerate(rids):
        target = rels.get(rid, "")
        name = "word/" + target.replace("../", "")
        d = dims[i] if i < len(dims) else (dims[0] if dims else (None, None))
        out.append((name, d[0], d[1]))
    return out


def walk(path):
    zf = zipfile.ZipFile(path)
    rels = load_rels(zf)
    doc = ET.fromstring(zf.read("word/document.xml"))
    body = doc.find(W + "body")
    if body is None:
        body = doc

    paras = []

    def rec(node):
        for child in node:
            tag = child.tag
            if tag == W + "p":
                txt = "".join(t.text or "" for t in child.iter(W + "t")).strip()
                paras.append((txt, para_images(child, rels)))
            elif tag == W + "tbl":
                rec(child)
            elif tag in (W + "sdt", W + "sdtContent", W + "tc", W + "txbxContent"):
                rec(child)
            else:
                if child.find(W + "p") is not None or child.find(W + "tbl") is not None:
                    rec(child)

    rec(body)
    return zf, paras


def verdict(dpi):
    if dpi is None:
        return "矢量/未知"
    if dpi >= 300:
        return "印刷级"
    if dpi >= 200:
        return "良好"
    if dpi >= 150:
        return "及格"
    if dpi >= 120:
        return "⚠️偏弱"
    return "❌不合格"


def main():
    ap = argparse.ArgumentParser(description="投标文件图片有效 DPI 审计")
    ap.add_argument("path")
    ap.add_argument("--map", action="store_true", help="按段落顺序列出，带上下文（看图文对应）")
    ap.add_argument("--only-weak", action="store_true", help="只列低于阈值的图")
    ap.add_argument("--threshold", type=float, default=150, help="判定阈值，默认 150 dpi")
    ap.add_argument("--json", help="同时导出 JSON")
    args = ap.parse_args()

    zf, paras = walk(args.path)
    rows = []
    for pi, (txt, imgs) in enumerate(paras):
        for name, wcm, hcm in imgs:
            try:
                data = zf.read(name)
            except KeyError:
                rows.append({"p": pi, "file": name, "verdict": "缺失",
                             "context": txt[:60]})
                continue
            px = img_size(data)
            is_emf = name.lower().endswith((".emf", ".wmf"))
            if px is None and is_emf:
                ec = emf_size_cm(data)
                rows.append({
                    "p": pi, "file": name, "bytes": len(data),
                    "vector": True, "emf_cm": ec,
                    "display_cm": (wcm, hcm), "dpi": None,
                    "verdict": "矢量(EMF/WMF)", "context": txt[:60],
                })
                continue
            if px is None:
                rows.append({"p": pi, "file": name, "bytes": len(data),
                             "dpi": None, "verdict": "无法解析", "context": txt[:60]})
                continue
            pw, ph = px
            dpi = None
            if wcm and wcm > 0:
                dpi = round(pw / (wcm / CM_PER_INCH), 1)
            rows.append({
                "p": pi, "file": name, "bytes": len(data),
                "px": f"{pw}x{ph}", "display_cm": (wcm, hcm), "dpi": dpi,
                "verdict": verdict(dpi), "context": txt[:60],
            })

    if args.only_weak:
        rows = [r for r in rows if (r.get("dpi") or 0) < args.threshold]

    # 终端表格
    print(f"{'段':>5} {'文件':<28} {'像素':<12} {'显示cm':<14} {'DPI':>7}  判定")
    print("-" * 96)
    for r in rows:
        d = r.get("display_cm") or (None, None)
        dstr = f"{d[0]}x{d[1]}" if d[0] else "-"
        if args.map:
            print(f"{r['p']:>5} {r['file'][-26:]:<28} {r.get('px','-'):<12} {dstr:<14} "
                  f"{str(r.get('dpi') or '-'):>7}  {r['verdict']}")
            if r.get("context"):
                print(f"      └ {r['context']}")
        else:
            print(f"{r['p']:>5} {r['file'][-26:]:<28} {r.get('px','-'):<12} {dstr:<14} "
                  f"{str(r.get('dpi') or '-'):>7}  {r['verdict']}")

    # 分组统计
    real = [r for r in rows if r.get("dpi")]
    if real:
        vals = sorted(r["dpi"] for r in real)
        n = len(vals)
        print("\n统计")
        print(f"  位图 {n} 张 | 最低 {vals[0]} | 中位 {vals[n//2]} | 最高 {vals[-1]} dpi")
        weak = [r for r in real if r["dpi"] < args.threshold]
        if weak:
            print(f"  ⚠️ 低于 {args.threshold} dpi 的有 {len(weak)} 张：")
            for r in weak:
                wcm = r["display_cm"][0]
                print(f"     P{r['p']} {r['file'][-30:]} {r['px']} → {r['dpi']} dpi "
                      f"(显示宽 {wcm} cm) {r['verdict']}")
        vec = [r for r in rows if r.get("vector")]
        if vec:
            print(f"  矢量图 {len(vec)} 张（EMF/WMF，不受 DPI 限制）")

    if args.json:
        with open(args.json, "w", encoding="utf-8") as fh:
            json.dump(rows, fh, ensure_ascii=False, indent=1)
        print(f"\n→ JSON 已写入 {args.json}")


if __name__ == "__main__":
    main()
