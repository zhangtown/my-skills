# -*- coding: utf-8 -*-
"""
prepare-svg：把 draw.io 导出的 SVG 修成 Visio 能正确导入的形态。

解决 draw.io v29.0.3 的三个缺陷（详见 SKILL.md）：
  A. 每个 <text> 的坐标是假的 (0,0)、字体字号也不对
     → 按同一 cell 的 <rect> 几何重建 <text>，字号取自 .drawio 的 fontSize
  B. 嵌套 <g data-cell-id> 让 Visio 生成按比例缩放的子形状，导致中文折行
     → 扁平化：抽掉所有 <g>，只留 rect/text/path/line/ellipse/polygon
  C. 根 <svg> 的 width/height 写 px 会被 Visio 按 96dpi 折算（×0.75）
     → 改成 pt

用法：
    python prepare_svg.py in.svg out.svg --drawio in.drawio
    python prepare_svg.py in.svg out.svg            # 不给 drawio 就沿用 SVG 里的字号

之后：drawio2vsdx.py convert out.svg --mode vsdx
"""
import argparse
import html as html_mod
import os
import re

TAGS = re.compile(r"<[^>]+>")


def plain_text(xhtml):
    """从 XHTML 片段里抽出纯文本。"""
    x = re.sub(r"<br\s*/?>", "\n", xhtml, flags=re.I)
    x = re.sub(r"</(div|p|li|tr|h\d)>", "\n", x, flags=re.I)
    x = html_mod.unescape(TAGS.sub("", x))
    return " ".join(t.strip() for t in x.splitlines() if t.strip())


def to_float(v, default=0.0):
    try:
        return float(str(v).replace("px", "").strip())
    except (TypeError, ValueError):
        return default


def load_drawio_styles(path):
    """{标签: (fontSize, align)} —— 从 .drawio 的 mxCell style 里抽。"""
    if not path or not os.path.exists(path):
        return {}
    src = open(path, encoding="utf-8", errors="ignore").read()
    styles = {}
    for m in re.finditer(r'<mxCell[^>]*?value="([^"]*)"[^>]*?style="([^"]*)"', src):
        val = html_mod.unescape(m.group(1))
        sty = m.group(2)
        if not val:
            continue
        fs = re.search(r"fontSize=([\d.]+)", sty)
        al = re.search(r"align=(\w+)", sty)
        styles.setdefault(val, (
            float(fs.group(1)) if fs else 9.0,
            al.group(1) if al else "center",
        ))
    return styles


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("dst")
    ap.add_argument("--drawio", default=None, help="对应的 .drawio，用于取真实字号")
    ap.add_argument("--font", default="Microsoft YaHei, SimHei, SimSun, sans-serif")
    ap.add_argument("--shrink", type=float, default=1.0,
                    help="字号再乘一个系数（给文本框留余量，如 0.92）")
    a = ap.parse_args()

    svg = open(a.src, encoding="utf-8").read()
    styles = load_drawio_styles(a.drawio)
    print("drawio 样式表: %d 条" % len(styles))

    # --- 收集每个 cell 的 rect 几何 + 原始文字 ---
    cells = []
    for m in re.finditer(r'<g data-cell-id="([^"]+)">(.*?)(?=<g data-cell-id="|</g></g></g>|\Z)',
                         svg, re.S):
        cid, body = m.group(1), m.group(2)
        rm = re.search(r'<rect\b[^>]*?x="([^"]*)"[^>]*?y="([^"]*)"'
                       r'[^>]*?width="([^"]*)"[^>]*?height="([^"]*)"', body)
        tm = re.search(r"<text\b[^>]*>(.*?)</text>", body, re.S)
        if not (rm and tm):
            continue
        txt = plain_text(tm.group(1))
        if txt:
            cells.append((cid, tuple(to_float(v) for v in rm.groups()), txt))
    print("带文字的单元格: %d" % len(cells))

    out = svg
    n = 0
    for cid, (rx, ry, rw, rh), txt in cells:
        fs, al = styles.get(txt, (9.0, "center"))
        fs *= a.shrink
        if al == "left":
            tx, anchor = rx + 2.0, "start"
        else:
            tx, anchor = rx + rw / 2, "middle"
        ty = ry + rh / 2
        new = ('<text x="%.1f" y="%.1f" text-anchor="%s" dominant-baseline="central" '
               'font-family="%s" font-size="%.2f" fill="#000000">%s</text>'
               % (tx, ty, anchor, a.font, fs, html_mod.escape(txt)))
        pat = re.compile(r'(<g data-cell-id="%s">.*?)(<text\b[^>]*>.*?</text>)(.*?)'
                         r'(?=<g data-cell-id="|</g></g></g>|\Z)' % re.escape(cid), re.S)
        out, k = pat.subn(lambda mm: mm.group(1) + new + mm.group(3), out, count=1)
        n += k
    print("重建 <text>: %d" % n)

    # 去掉 drawio 的 light-dark() CSS 覆盖（Visio 会当成高亮色）
    out = re.sub(r'\s*style="[^"]*light-dark[^"]*"', "", out)
    out = re.sub(r'\s*style="background:[^"]*"', "", out, count=1)
    out = re.sub(r'\s*color-scheme="[^"]*"', "", out)
    out = re.sub(r'<text\b[^>]*>Text is not SVG[^<]*</text>', "", out)

    # 根尺寸 px -> pt
    i = out.find("<svg")
    head = out[i:out.find(">", i) + 1]
    wm = re.search(r'viewBox="([\d.\- ]+)"', head)
    if wm:
        vb = [float(x) for x in wm.group(1).split()]
        new_head = re.sub(r'width="[^"]*"', 'width="%.0fpt"' % vb[2], head)
        new_head = re.sub(r'height="[^"]*"', 'height="%.0fpt"' % vb[3], new_head)
        out = out.replace(head, new_head, 1)
        print("根尺寸 -> %.0f x %.0f pt" % (vb[2], vb[3]))

    # --- 扁平化：抽掉所有 <g>，只留绘制元素 ---
    j = out.find("<svg")
    head = out[j:out.find(">", j) + 1]
    body = out[out.find(">", j) + 1:]
    body = re.sub(r"</?g\b[^>]*>", "", body)
    body = re.sub(r"<defs\b.*?</defs>", "", body, flags=re.S)
    elems = re.findall(
        r"<(?:rect|text|path|line|ellipse|polygon)\b[^>]*?(?:/>|>.*?</(?:text|rect|ellipse|polygon|path|line)>)",
        body, re.S)
    flat = ('<?xml version="1.0" encoding="UTF-8"?>\n'
            + head + "\n" + "".join(elems) + "\n</svg>")
    print("扁平元素: %d  (text %d / rect %d)"
          % (len(elems), flat.count("<text"), flat.count("<rect>")))

    open(a.dst, "w", encoding="utf-8").write(flat)
    print("->", a.dst, os.path.getsize(a.dst), "B")
    print("下一步:  python <drawio2vsdx>/scripts/drawio2vsdx.py convert %s --mode vsdx" % a.dst)


if __name__ == "__main__":
    main()
