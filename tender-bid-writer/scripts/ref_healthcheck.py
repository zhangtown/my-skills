# -*- coding: utf-8 -*-
"""参考文件结构体检 —— 绑定前先跑一遍，看清参考文件到底能被解析成什么样。

它回答三个问题：
  1) 解析器实际认出的章节树长什么样（层级编号 1/1.1/1.1.1，与 references.py 同源）；
  2) 有没有"看着像子标题、却没套 Word 标题样式 / 没有大纲级别"的段落——
     这类会被当正文吞进上一节、无法用编号单独绑定（源文件排版不规范所致）；
  3) 各级标题、疑似漏标题的数量小结。

用法：
  python scripts/ref_healthcheck.py <参考文件.docx|.md|.pdf>
  python scripts/ref_healthcheck.py <文件> --raw          # 逐段打印 样式/大纲级别/列表编号/加粗
  python scripts/ref_healthcheck.py <文件> --raw --kw 关键词   # --raw 下只看命中关键词前后

体检只对 docx 有意义（md/pdf 无样式概念）；对 md/pdf 仅打印解析出的章节树。
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from references import parse_reference, _hier_numbers  # noqa: E402

MAX_HEADING_LEN = 30            # 超过这个长度基本不可能是标题
END_PUNCT = "。！？；，,.!?;：:、"   # 以句读结尾的多半是正文，不是标题


def print_tree(refdoc):
    tag = "可靠" if refdoc.get("reliable") else "需确认(降级)"
    print(f"\n===== 解析出的章节树  {os.path.basename(refdoc['path'])}"
          f"  [{refdoc['kind']} · {tag}] =====")
    for w in refdoc.get("warnings", []):
        print(f"  ! {w}")
    secs = refdoc.get("sections", [])
    if not secs:
        print("  （未切出任何章节）")
        return
    nums = _hier_numbers(secs)
    for i, s in enumerate(secs):
        prev = s.get("text", "").strip().replace("\n", " ")[:26]
        print(f"  {nums[i]:<10}{'  ' * (s.get('level', 1) - 1)}{s.get('title', '')}"
              + (f"  〔{prev}…〕" if prev else "  〔（无正文）〕"))


def _docx_rows(path):
    """返回逐段 (idx, style, olvl, numid, ilvl, bold, is_heading, text)。"""
    from docx import Document
    from docx.oxml.ns import qn
    import re
    style_re = re.compile(r'(?:heading|标题)\s*(\d+)', re.I)
    doc = Document(path)
    rows = []
    for i, p in enumerate(doc.paragraphs):
        t = (p.text or "").strip()
        if not t:
            continue
        style = ""
        try:
            style = p.style.name or ""
        except Exception:
            pass
        olvl = numid = ilvl = ""
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
            if p.runs and p.runs[0].bold:
                bold = "B"
        except Exception:
            pass
        is_heading = bool(style_re.search(style) or olvl != "")
        rows.append((i, style, olvl, numid, ilvl, bold, is_heading, t))
    return rows


def raw_dump(path, kw=None):
    rows = _docx_rows(path)
    if kw:
        hit = [k for k, r in enumerate(rows) if kw in r[7]]
        keep = set()
        for k in hit:
            for j in range(max(0, k - 5), min(len(rows), k + 26)):
                keep.add(j)
        rows = [rows[j] for j in sorted(keep)]
    for i, style, olvl, numid, ilvl, bold, is_h, t in rows:
        flag = "H" if is_h else " "
        print(f"[{i:>4}] {flag} {style[:14]:<14} olvl={olvl or '-':<2} "
              f"num={numid or '-':<3} ilvl={ilvl or '-':<2} {bold or ' '} | {t[:44]}")


def suspects(path):
    """疑似漏标题：短、不以句读结尾、没套标题样式/大纲级别、不是题注。"""
    rows = _docx_rows(path)
    out = []
    last_heading = "（文首）"
    for i, style, olvl, numid, ilvl, bold, is_h, t in rows:
        if is_h:
            last_heading = t
            continue
        if "caption" in style.lower() or "题注" in style:
            continue
        if len(t) <= MAX_HEADING_LEN and t[-1] not in END_PUNCT:
            # 带列表编号或加粗的短行，更像被漏掉的小标题
            score = []
            if numid:
                score.append(f"列表编号 num={numid}/ilvl={ilvl or 0}")
            if bold:
                score.append("加粗")
            out.append((i, last_heading, t, style, "，".join(score)))
    return out


def main():
    ap = argparse.ArgumentParser(description="参考文件结构体检")
    ap.add_argument("path", help="参考文件路径（docx/md/pdf）")
    ap.add_argument("--raw", action="store_true", help="逐段打印样式/大纲级别/列表编号/加粗")
    ap.add_argument("--kw", default=None, help="配合 --raw，只看命中关键词前后")
    args = ap.parse_args()

    if args.raw:
        raw_dump(args.path, args.kw)
        return 0

    refdoc = parse_reference(args.path)
    print_tree(refdoc)

    if args.path.lower().endswith(".docx"):
        sus = suspects(args.path)
        print(f"\n===== 疑似漏标题（短行·未句读结尾·无标题样式）  共 {len(sus)} 处 =====")
        if not sus:
            print("  无。参考文件层级结构规范，可放心按编号绑定。")
        else:
            print("  下列段落被当作正文吞进了所属章节，无法用编号单独绑定；")
            print("  若你要绑定的正是其中某节，请在源 docx 里给它套上「标题N」样式后重跑。")
            for i, parent, t, style, why in sus[:80]:
                print(f"    [{i:>4}] 归属《{parent}》 | {t[:34]}"
                      + (f"  （{why}）" if why else f"  （{style}）"))
            if len(sus) > 80:
                print(f"    …另有 {len(sus) - 80} 处，用 --raw 查看全部。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
