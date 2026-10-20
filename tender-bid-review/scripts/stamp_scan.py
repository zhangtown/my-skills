#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
签章落位扫描 —— 找出手写签字/红章到底盖在哪几页，以及哪些该盖的地方没盖。

为什么必须单独扫：投标文件里"（公章）"后面跟的公司名往往是**打字打上去的**，
字符层面看起来"填了"，但一个真章都没有。纯文本审查 100% 漏掉这类问题。

方法：PDF 逐页渲染 → 找红色像素连通域 → 面积与形状达标的判为印章候选。
红色细线（表框、界面高亮）面积小或长宽比极端，会被自动降级。

用法：
    python stamp_scan.py 投标文件.pdf
    python stamp_scan.py 投标文件.pdf --dpi 200 --min-area 1500
    python stamp_scan.py 投标文件.pdf --pages 5-60 --json stamps.json
    python stamp_scan.py 投标文件.pdf --blue          # 同时找蓝色笔迹

依赖：PyMuPDF (pip install pymupdf)。numpy 可选（有则更快）。
"""

import argparse
import json
import sys
from collections import deque

try:
    import fitz  # PyMuPDF
except ImportError:
    print("❌ 需要 PyMuPDF：pip install pymupdf", file=sys.stderr)
    sys.exit(2)

try:
    import numpy as np
    HAVE_NP = True
except ImportError:
    HAVE_NP = False


def parse_pages(spec, total):
    if not spec:
        return list(range(total))
    out = []
    for part in spec.split(","):
        part = part.strip()
        if "-" in part:
            a, b = part.split("-", 1)
            a = int(a) if a else 1
            b = int(b) if b else total
            out.extend(range(a - 1, min(b, total)))
        elif part:
            out.append(int(part) - 1)
    return [p for p in out if 0 <= p < total]


def components_bfs(mask, min_area):
    """纯 Python 连通域（4 邻域）。mask 是 list[bytearray] 或 ndarray。"""
    if HAVE_NP and isinstance(mask, np.ndarray):
        h, w = mask.shape
        seen = np.zeros_like(mask, dtype=bool)
        comps = []
        ys, xs = np.nonzero(mask)
        for sy, sx in zip(ys, xs):
            if seen[sy, sx]:
                continue
            q = deque([(sy, sx)])
            seen[sy, sx] = True
            area = 0
            x0 = x1 = int(sx)
            y0 = y1 = int(sy)
            while q:
                y, x = q.popleft()
                area += 1
                if x < x0: x0 = x
                if x > x1: x1 = x
                if y < y0: y0 = y
                if y > y1: y1 = y
                for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    ny, nx = y + dy, x + dx
                    if 0 <= ny < h and 0 <= nx < w and mask[ny, nx] and not seen[ny, nx]:
                        seen[ny, nx] = True
                        q.append((ny, nx))
            if area >= min_area:
                comps.append((area, x0, y0, x1, y1))
        return comps

    h = len(mask)
    w = len(mask[0]) if h else 0
    seen = [bytearray(w) for _ in range(h)]
    comps = []
    for sy in range(h):
        row = mask[sy]
        for sx in range(w):
            if not row[sx] or seen[sy][sx]:
                continue
            q = deque([(sy, sx)])
            seen[sy][sx] = 1
            area = 0
            x0 = x1 = sx
            y0 = y1 = sy
            while q:
                y, x = q.popleft()
                area += 1
                if x < x0: x0 = x
                if x > x1: x1 = x
                if y < y0: y0 = y
                if y > y1: y1 = y
                for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    ny, nx = y + dy, x + dx
                    if 0 <= ny < h and 0 <= nx < w and mask[ny][nx] and not seen[ny][nx]:
                        seen[ny][nx] = 1
                        q.append((ny, nx))
            if area >= min_area:
                comps.append((area, x0, y0, x1, y1))
    return comps


def build_mask(pix, mode):
    w, h = pix.width, pix.height
    samples = pix.samples
    n = pix.n
    if HAVE_NP:
        arr = np.frombuffer(samples, dtype=np.uint8).reshape(h, w, n).astype(np.int16)
        r, g, b = arr[:, :, 0], arr[:, :, 1], arr[:, :, 2]
        if mode == "red":
            return ((r > 140) & (r - g > 55) & (r - b > 55)).astype(np.uint8)
        else:  # blue ink
            return ((b > 110) & (b - r > 40) & (b - g > 30)).astype(np.uint8)
    mask = []
    for y in range(h):
        row = bytearray(w)
        base = y * w * n
        for x in range(w):
            o = base + x * n
            R, G, B = samples[o], samples[o + 1], samples[o + 2]
            if mode == "red":
                row[x] = 1 if (R > 140 and R - G > 55 and R - B > 55) else 0
            else:
                row[x] = 1 if (B > 110 and B - R > 40 and B - G > 30) else 0
        mask.append(row)
    return mask


def to_cm(px, scale):
    """像素 → 厘米。显式 float() 是因为 numpy 整型经 round() 会返回 np.float64，
    打印出来是 `np.float64(4.9)` 这种没法读的东西。"""
    return round(float(px) / scale / 72.0 * 2.54, 1)


def region_label(x0, y0, x1, y1, page_w, page_h):
    """把印章位置说成人话——审查时要核的是"投标函那页落款处有没有章"，
    所以给"左下"这种区位比给坐标有用得多。"""
    cx, cy = (x0 + x1) / 2.0, (y0 + y1) / 2.0
    fx, fy = cx / float(page_w), cy / float(page_h)
    col = "左" if fx < 0.34 else ("右" if fx > 0.66 else "中")
    row = "上" if fy < 0.20 else ("下" if fy > 0.72 else "中")
    where = {
        ("左", "上"): "左上", ("中", "上"): "顶部居中", ("右", "上"): "右上",
        ("左", "中"): "左中", ("中", "中"): "居中", ("右", "中"): "右中",
        ("左", "下"): "左下(落款处)", ("中", "下"): "底部居中", ("右", "下"): "右下(落款处)",
    }[(col, row)]
    return where


def classify(area, x0, y0, x1, y1, page_area):
    bw = x1 - x0 + 1
    bh = y1 - y0 + 1
    if bw <= 0 or bh <= 0:
        return "噪声", 0.0
    fill = area / float(bw * bh)
    aspect = max(bw, bh) / float(min(bw, bh))
    coverage = area / float(page_area)
    if coverage > 0.5:
        return "整页红底(设计元素)", fill
    if aspect > 8 and fill < 0.4:
        return "细长红线(表框/界面高亮)", fill
    if bw < 12 or bh < 12:
        return "小色块", fill
    if area >= 1800 and fill >= 0.10:
        return "★印章候选", fill
    if area >= 500:
        return "中等红块", fill
    return "小色块", fill


def main():
    ap = argparse.ArgumentParser(description="投标文件签章落位扫描")
    ap.add_argument("path")
    ap.add_argument("--dpi", type=int, default=150, help="渲染 DPI，默认 150")
    ap.add_argument("--pages", help="页码范围，如 5-60,100,120-125（1 起）")
    ap.add_argument("--min-area", type=int, default=500, help="最小连通域面积(px)，默认 500")
    ap.add_argument("--blue", action="store_true", help="同时扫描蓝色笔迹")
    ap.add_argument("--json", help="导出 JSON")
    args = ap.parse_args()

    doc = fitz.open(args.path)
    pages = parse_pages(args.pages, doc.page_count)
    scale = args.dpi / 72.0

    print(f"文件: {args.path}  共 {doc.page_count} 页，扫描 {len(pages)} 页 @ {args.dpi} dpi")
    print(f"{'页':>5}  {'红块数':>6}  {'最大面积':>8}  判定 / 位置")
    print("-" * 82)

    results = []
    seal_pages = []
    for pno in pages:
        page = doc[pno]
        pix = page.get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False)
        page_area = pix.width * pix.height
        mask = build_mask(pix, "red")
        comps = components_bfs(mask, args.min_area)
        comps.sort(reverse=True)

        entries = []
        for area, x0, y0, x1, y1 in comps[:6]:
            kind, fill = classify(area, x0, y0, x1, y1, page_area)
            entries.append({
                "area": int(area), "bbox_px": [int(x0), int(y0), int(x1), int(y1)],
                "bbox_cm": [to_cm(x0, scale), to_cm(y0, scale),
                            to_cm(x1 - x0, scale), to_cm(y1 - y0, scale)],
                "where": region_label(x0, y0, x1, y1, pix.width, pix.height),
                "kind": kind, "fill": round(fill, 2),
            })
        blue_entries = []
        if args.blue:
            bmask = build_mask(pix, "blue")
            for area, x0, y0, x1, y1 in sorted(components_bfs(bmask, args.min_area), reverse=True)[:4]:
                kind, fill = classify(area, x0, y0, x1, y1, page_area)
                blue_entries.append({"area": int(area),
                                     "kind": "蓝笔迹" if kind != "细长红线(表框/界面高亮)" else kind,
                                     "bbox_cm": [to_cm(x0, scale), to_cm(y0, scale),
                                                 to_cm(x1 - x0, scale), to_cm(y1 - y0, scale)],
                                     "where": region_label(x0, y0, x1, y1, pix.width, pix.height)})

        seals = [e for e in entries if e["kind"] == "★印章候选"]
        if seals:
            seal_pages.append(pno + 1)
        biggest = entries[0]["area"] if entries else 0
        if entries:
            tag = "★印章候选" if seals else entries[0]["kind"]
            e = seals[0] if seals else entries[0]
            print(f"{pno+1:>5}  {len(entries):>6}  {biggest:>8}  {tag}  "
                  f"{e['where']} {e['bbox_cm'][2]}×{e['bbox_cm'][3]}cm")
        elif blue_entries:
            e = blue_entries[0]
            print(f"{pno+1:>5}  {0:>6}  {0:>8}  {e['kind']}  "
                  f"{e['where']} {e['bbox_cm'][2]}×{e['bbox_cm'][3]}cm")

        results.append({"page": pno + 1, "red": entries, "blue": blue_entries})

    doc.close()

    print("\n" + "=" * 82)
    if seal_pages:
        print(f"检出印章候选的页（共 {len(seal_pages)} 页）：{seal_pages}")
        print("\n→ 拿这份清单去对'应该盖章的地方'：投标函、开标一览表、报价明细表、法人授权委托书、")
        print("  投标承诺书、驻场服务承诺书、各承诺函、偏离表、营业执照/财务报表/纳税社保/业绩合同")
        print("  复印件、▲项产品彩页复印件。清单以外的页不用管，清单里缺的就是漏盖。")
    else:
        print("❌ 未检出任何印章候选。若这份标书应当盖章，说明**一个章都没有盖**——")
        print("   这是最典型的必废项。请核对：投标函、开标一览表、报价明细表、法人授权委托书、")
        print("   投标承诺书、驻场服务承诺书、各承诺函、偏离表、营业执照/财务报表/纳税社保/")
        print("   业绩合同复印件、▲项产品彩页复印件。")

    if args.json:
        with open(args.json, "w", encoding="utf-8") as fh:
            json.dump({"file": args.path, "dpi": args.dpi,
                       "seal_pages": seal_pages, "pages": results},
                      fh, ensure_ascii=False, indent=1)
        print(f"\n→ JSON 已写入 {args.json}")


if __name__ == "__main__":
    main()
