# -*- coding: utf-8 -*-
"""修复 build.js 中双引号字符串内的 ASCII 引号为中文引号"""
import sys

def fix_js_line(line):
    out = []
    i = 0
    n = len(line)
    state = None  # None | '"' | "'" | '`'
    inner = 0
    while i < n:
        ch = line[i]
        if state is None:
            if ch in ('"', "'", "`"):
                state = ch
                out.append(ch)
            else:
                out.append(ch)
            i += 1
            continue
        if ch == "\\":
            out.append(ch)
            if i + 1 < n:
                out.append(line[i + 1])
            i += 2
            continue
        if state == '"' and ch == '"':
            j = i + 1
            while j < n and line[j] in " \t":
                j += 1
            if j >= n or line[j] in ",)]:;}":
                state = None
                out.append(ch)
            else:
                inner += 1
                out.append("\u201c" if inner % 2 == 1 else "\u201d")
            i += 1
            continue
        if ch == state:
            state = None
            out.append(ch)
            i += 1
            continue
        out.append(ch)
        i += 1
    return "".join(out)

def main(path):
    src = open(path, encoding="utf-8").read()
    lines = src.split("\n")
    new = [fix_js_line(ln) for ln in lines]
    open(path, "w", encoding="utf-8").write("\n".join(new))
    print(path, "fixed")

if __name__ == "__main__":
    main(sys.argv[1])
