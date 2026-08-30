#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""全文纯黑检查：document.xml 与 styles.xml 中所有 <w:color> 必须为 000000。
用法: python check_black.py <输出.docx>
"""
import sys, re, zipfile
from collections import Counter

def main():
    if len(sys.argv) < 2:
        sys.exit("用法: python check_black.py <输出.docx>")
    z = zipfile.ZipFile(sys.argv[1])
    total = Counter()
    bad = []
    for part in ("word/document.xml", "word/styles.xml", "word/header1.xml", "word/footer1.xml",
                 "word/headers/header1.xml", "word/footers/footer1.xml"):
        try:
            xml = z.read(part).decode("utf-8")
        except KeyError:
            continue
        colors = Counter(re.findall(r'<w:color w:val="([^"]+)"/>', xml))
        total.update(colors)
        for c in colors:
            if c.lower() != "000000":
                bad.append((part, c))
    print("颜色分布:", dict(total))
    if bad:
        print("非黑色残留:")
        for part, c in bad:
            print("  ", part, c)
        sys.exit(1)
    print("全文纯黑 ✓")

if __name__ == "__main__":
    main()
