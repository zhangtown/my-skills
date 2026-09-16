# -*- coding: utf-8 -*-
"""临时诊断：把 docx 每个非空段落的 样式名 / outlineLvl / 文本前 44 字 打出来，
用于查清"某些子标题为何没被解析成章节"。用完可删。
用法： python scripts/diag_docx.py "参考文件.docx"  [关键词]
    带关键词时只打印命中关键词那段前后 25 行，便于聚焦。"""
import sys, re
from docx import Document
from docx.oxml.ns import qn

path = sys.argv[1]
kw = sys.argv[2] if len(sys.argv) > 2 else None
doc = Document(path)

rows = []
for p in doc.paragraphs:
    t = (p.text or "").strip()
    if not t:
        continue
    style = ""
    try:
        style = p.style.name or ""
    except Exception:
        pass
    olvl = ""
    numid = ""
    ilvl = ""
    try:
        pPr = p._p.pPr
        if pPr is not None:
            el = pPr.find(qn('w:outlineLvl'))
            if el is not None:
                olvl = el.get(qn('w:val'))
            npr = pPr.find(qn('w:numPr'))
            if npr is not None:
                nid = npr.find(qn('w:numId'))
                il = npr.find(qn('w:ilvl'))
                numid = nid.get(qn('w:val')) if nid is not None else ""
                ilvl = il.get(qn('w:val')) if il is not None else ""
    except Exception:
        pass
    bold = ""
    try:
        r0 = p.runs[0] if p.runs else None
        if r0 is not None and r0.bold:
            bold = "B"
    except Exception:
        pass
    rows.append((style, olvl, numid, ilvl, bold, t))

if kw:
    hit = [i for i, r in enumerate(rows) if kw in r[5]]
    keep = set()
    for i in hit:
        for j in range(max(0, i - 5), min(len(rows), i + 26)):
            keep.add(j)
    idxs = sorted(keep)
else:
    idxs = range(len(rows))

for i in idxs:
    style, olvl, numid, ilvl, bold, t = rows[i]
    print(f"[{i:>4}] {style[:14]:<14} olvl={olvl or '-':<2} num={numid or '-':<3} "
          f"ilvl={ilvl or '-':<2} {bold or ' '} | {t[:40]}")
