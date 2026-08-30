#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成产品功能截图 HTML（mockgen 设计系统渲染）。
用法: python gen_mockups.py <工作目录>
约定: 工作目录下 mockgen/ 含 base.py（设计系统）与 pages*.py（页面规格，导出 ALL_PAGES）
输出: mockgen/mockups/*.html（1920×1080 设计稿，供 screenshot_all.py 截图）
"""
import sys, os

def main():
    base = sys.argv[1] if len(sys.argv) > 1 else "."
    mockgen_dir = os.path.join(base, "mockgen")
    if not os.path.isdir(mockgen_dir):
        sys.exit(f"mockgen 目录不存在: {mockgen_dir}")

    sys.path.insert(0, mockgen_dir)
    # 导入页面规格模块（约定含 ALL_PAGES 与 render_all()）
    import importlib.util, glob
    pages_mods = []
    for f in sorted(glob.glob(os.path.join(mockgen_dir, "pages*.py"))):
        name = "pages_" + os.path.splitext(os.path.basename(f))[0]
        spec = importlib.util.spec_from_file_location(name, f)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        pages_mods.append(mod)

    all_pages = {}
    for mod in pages_mods:
        if hasattr(mod, "ALL_PAGES"):
            all_pages.update(mod.ALL_PAGES)
    if not all_pages:
        sys.exit("未找到页面规格（需要 pages*.py 导出 ALL_PAGES）")

    # 渲染（由第一个模块的 render_all 或本脚本直接写）
    from base import shell
    out_dir = os.path.join(mockgen_dir, "mockups")
    os.makedirs(out_dir, exist_ok=True)
    for name, (grp, label, crumb_l, crumb_r, title, sub, fn) in all_pages.items():
        html = shell(grp, label, crumb_l, crumb_r, title, sub, fn())
        with open(os.path.join(out_dir, f"{name}.html"), "w", encoding="utf-8") as fp:
            fp.write(html)
    print(f"渲染 {len(all_pages)} 个页面 -> {out_dir}")

if __name__ == "__main__":
    main()
