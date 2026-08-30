#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Chrome headless 批量截图（1920×1080）。
用法: python screenshot_all.py <工作目录> [--chrome <chrome路径>]
输入: <工作目录>/mockgen/mockups/*.html
输出: <工作目录>/shots/<同名>.png
"""
import subprocess, os, sys, glob

def main():
    base = sys.argv[1] if len(sys.argv) > 1 else "."
    chrome = os.environ.get("CHROME_PATH", r"C:\Program Files\Google\Chrome\Application\chrome.exe")
    if "--chrome" in sys.argv:
        chrome = sys.argv[sys.argv.index("--chrome") + 1]
    if not os.path.exists(chrome):
        alt = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
        if os.path.exists(alt):
            chrome = alt
        else:
            sys.exit(f"未找到 Chrome/Edge: {chrome}")

    mockups = os.path.join(base, "mockgen", "mockups")
    shots = os.path.join(base, "shots")
    os.makedirs(shots, exist_ok=True)
    files = sorted(glob.glob(os.path.join(mockups, "*.html")))
    if not files:
        sys.exit(f"无 HTML 页面: {mockups}")

    for f in files:
        name = os.path.splitext(os.path.basename(f))[0]
        out = os.path.join(shots, f"{name}.png")
        url = "file:///" + f.replace("\\", "/")
        subprocess.run([chrome, "--headless=new", "--disable-gpu", "--hide-scrollbars",
                        "--force-device-scale-factor=1", "--window-size=1920,1080",
                        f"--screenshot={out}", url],
                       capture_output=True)
    print(f"截图完成: {len(files)} 张 -> {shots}")

if __name__ == "__main__":
    main()
