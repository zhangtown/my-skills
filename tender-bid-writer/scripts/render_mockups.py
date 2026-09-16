#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
render_mockups.py — 界面效果图流水线：静态 HTML 界面稿 → PNG →（可选）回填 content.json

约定（见 references/mockup_guide.md）：
  - 界面稿放在一个目录（默认 mockups/），一个 HTML 一张图；
  - **文件名 = figure 块的图题 title**（非法字符替换为 _），回填靠这个约定自动匹配；
  - 截图用本机 Edge/Chrome 无头模式，零额外依赖。

用法：
  python scripts/render_mockups.py mockups/                        # 渲染全部 html → 同名 png
  python scripts/render_mockups.py mockups/ --attach content.json  # 渲染 + 回填 img 路径
  可选：--width 1440 --height 900 --browser "C:\\...\\msedge.exe" --force
"""

import sys
import os
import re
import json
import argparse
import subprocess

BROWSER_CANDIDATES = [
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
]

ILLEGAL = re.compile(r'[\\/:*?"<>|]')


def sanitize(title):
    """图题 → 文件名（与 mockup_guide.md 的命名约定一致）。"""
    return ILLEGAL.sub("_", title.strip())


def find_browser(explicit=None):
    if explicit:
        if os.path.isfile(explicit):
            return explicit
        sys.exit(f"[错误] 指定的浏览器不存在：{explicit}")
    for p in BROWSER_CANDIDATES:
        if os.path.isfile(p):
            return p
    sys.exit("[错误] 未找到 Edge/Chrome，可用 --browser 指定 msedge.exe 完整路径。")


def render(browser, html_path, png_path, width, height):
    """无头截图。--virtual-time-budget 给 CDN 样式/脚本留渲染时间。"""
    cmd = [browser, "--headless=new", "--disable-gpu", "--hide-scrollbars",
           f"--window-size={width},{height}", "--virtual-time-budget=8000",
           f"--screenshot={os.path.abspath(png_path)}",
           "file:///" + os.path.abspath(html_path).replace("\\", "/")]
    r = subprocess.run(cmd, capture_output=True, timeout=60)
    ok = r.returncode == 0 and os.path.isfile(png_path) and os.path.getsize(png_path) > 0
    return ok, (r.stderr or b"").decode("utf-8", "ignore")[-300:]


def iter_figures(node):
    """递归找出 content 里所有 figure 块。"""
    if isinstance(node, dict):
        if node.get("type") == "figure":
            yield node
        for v in node.values():
            yield from iter_figures(v)
    elif isinstance(node, list):
        for it in node:
            yield from iter_figures(it)


def attach(content_path, png_dir, force):
    with open(content_path, "r", encoding="utf-8") as f:
        content = json.load(f)
    base = os.path.dirname(os.path.abspath(content_path))
    hit, miss, skip = [], [], []
    for fig in iter_figures(content):
        title = (fig.get("title") or "").strip()
        if not title:
            continue
        if fig.get("img") and not force:
            skip.append(title)
            continue
        png = os.path.join(png_dir, sanitize(title) + ".png")
        if os.path.isfile(png):
            fig["img"] = os.path.relpath(png, base).replace("\\", "/")
            fig.setdefault("width_cm", 15.0)
            hit.append(title)
        else:
            miss.append(title)
    if hit:
        with open(content_path, "w", encoding="utf-8") as f:
            json.dump(content, f, ensure_ascii=False, indent=2)
    print(f"[attach] 回填 {len(hit)} 张：{'、'.join(hit) or '—'}")
    if skip:
        print(f"[attach] 已有 img 跳过 {len(skip)} 张（--force 可覆盖）：{'、'.join(skip)}")
    if miss:
        print(f"[attach] 未找到同名 PNG（仍为占位框）{len(miss)} 张：{'、'.join(miss)}")
        print(f"         期望文件名 = 图题（非法字符→_）+ .png，目录：{png_dir}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mockup_dir", help="界面稿目录（*.html）")
    ap.add_argument("--attach", default=None, metavar="content.json",
                    help="渲染后按图题匹配同名 PNG，回填 figure.img")
    ap.add_argument("--width", type=int, default=1440)
    ap.add_argument("--height", type=int, default=900)
    ap.add_argument("--browser", default=None, help="msedge/chrome 可执行文件路径")
    ap.add_argument("--force", action="store_true",
                    help="重渲染已有 PNG / 覆盖 figure 已有 img")
    args = ap.parse_args()

    d = args.mockup_dir
    if not os.path.isdir(d):
        sys.exit(f"[错误] 目录不存在：{d}")
    htmls = sorted(f for f in os.listdir(d) if f.lower().endswith(".html"))
    if not htmls:
        print(f"[警告] {d} 下没有 .html 界面稿。")

    browser = find_browser(args.browser) if htmls else None
    fail = 0
    for h in htmls:
        src = os.path.join(d, h)
        dst = os.path.join(d, os.path.splitext(h)[0] + ".png")
        if os.path.isfile(dst) and not args.force:
            print(f"[跳过] {h}（PNG 已存在，--force 重渲染）")
            continue
        ok, err = render(browser, src, dst, args.width, args.height)
        if ok:
            print(f"[渲染] {h} → {os.path.basename(dst)}")
        else:
            fail += 1
            print(f"[失败] {h}：{err or '无输出'}")

    if args.attach:
        if not os.path.isfile(args.attach):
            sys.exit(f"[错误] 文件不存在：{args.attach}")
        attach(args.attach, d, args.force)
    return 1 if fail else 0


if __name__ == "__main__":
    sys.exit(main())
