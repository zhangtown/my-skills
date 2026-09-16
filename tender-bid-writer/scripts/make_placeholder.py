#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
make_placeholder.py — 生成占位图 (placeholder figure)

按用户要求："占位图 + 图题"。本脚本生成一张带说明文字的灰底占位 PNG，
供 build_docx.py 引用，后续由人工替换为真实截图/示意图。

用法:
  python make_placeholder.py "数据接入界面示意" figures/fig1.png [宽px 高px]

依赖: Pillow (pip install Pillow)。若未安装 Pillow，可改用 build_docx 内置的
文字占位框 (在 content.json 中省略 figure.img 字段即可)。
"""
import sys
import os

def make(label, out_path, w=1000, h=560):
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        sys.stderr.write("未安装 Pillow，无法生成图片占位。"
                         "请改为在 content.json 中省略 figure.img 字段使用文字占位。\n")
        sys.exit(2)
    os.makedirs(os.path.dirname(os.path.abspath(out_path)) or ".", exist_ok=True)
    img = Image.new("RGB", (w, h), (245, 246, 248))
    d = ImageDraw.Draw(img)
    # 边框
    d.rectangle([4, 4, w - 5, h - 5], outline=(160, 165, 172), width=3)
    # 对角线 (示意"图片")
    d.line([4, 4, w - 5, h - 5], fill=(210, 213, 218), width=2)
    d.line([w - 5, 4, 4, h - 5], fill=(210, 213, 218), width=2)
    # 文字
    font = None
    for fp in ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
               "C:/Windows/Fonts/msyh.ttc", "C:/Windows/Fonts/simhei.ttf"):
        if os.path.exists(fp):
            try:
                font = ImageFont.truetype(fp, 34)
                break
            except Exception:
                pass
    if font is None:
        font = ImageFont.load_default()
    text = f"占位图  {label}"
    try:
        bbox = d.textbbox((0, 0), text, font=font)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    except Exception:
        tw, th = len(text) * 18, 34
    d.text(((w - tw) / 2, (h - th) / 2), text, fill=(110, 116, 124), font=font)
    img.save(out_path)
    print(f"已生成占位图: {out_path}")


if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("用法: python make_placeholder.py \"图题/说明\" out.png [宽px 高px]")
        sys.exit(1)
    label = sys.argv[1]
    out = sys.argv[2]
    w = int(sys.argv[3]) if len(sys.argv) > 3 else 1000
    h = int(sys.argv[4]) if len(sys.argv) > 4 else 560
    make(label, out, w, h)
