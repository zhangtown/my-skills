#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
招标文件"尺子"提取 —— 审查前必须先把判定标准逐字取出来，不要凭印象审。

取四样东西：
  1. 标记符号体系（★ ※ ▲ △ ◎ ◆ 各多少个）——每家代理机构用的符号不同，
     而且**同一项目的不同采购包可能不同**，所以必须先探测再数。
  2. 无效投标 / 废标条款（含"实质性要求"的定义范围）。
  3. 关键数字：最高限价、保证金、投标有效期、份数、异常低价三条线。
  4. 第六章"投标文件格式及附件"的表单清单与落款格式。

用法：
    python tender_scan.py 招标文件.docx
    python tender_scan.py 招标文件.docx --clauses     # 只列废标条款
    python tender_scan.py 招标文件.docx --symbols     # 只数符号
    python tender_scan.py 招标文件.docx --forms       # 只列格式清单
    python tender_scan.py 招标文件.docx --json out.json
    python tender_scan.py 招标文件.txt                # 也接受已提取的纯文本

.doc 老格式先转：WPS COM 自动化比 antiword 可靠（antiword 对中文 GB 文档经常直接失败）。
"""

import argparse
import json
import re
import sys
import zipfile
from xml.etree import ElementTree as ET

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"

SYMBOLS = ["★", "☆", "※", "▲", "△", "◎", "◆", "●", "○", "■", "□", "√"]

CLAUSE_KEYS = [
    "无效投标", "废标", "作无效", "按无效", "实质性要求", "实质性响应",
    "不得开标", "不足3家", "不足三家", "拒绝接受",
]

KEY_NUMBERS = [
    (r"最高限价[：:\s]*([\d,，.]+\s*万?元?)", "最高限价"),
    (r"预算金额[：:\s]*([\d,，.]+\s*万?元?)", "预算金额"),
    (r"投标保证金[：:\s]*([\d,，.]+\s*万?元?)[^\n]{0,30}", "投标保证金"),
    (r"投标有效期[^\n]{0,40}?(\d+\s*天|九十天|90\s*天)", "投标有效期"),
    (r"正本[^\n]{0,20}", "份数-正本"),
    (r"副本[^\n]{0,20}", "份数-副本"),
    (r"最高限价\s*[×x\*]\s*45%", "异常低价线3"),
    (r"报价平均值\s*[×x\*]\s*50%", "异常低价线1"),
    (r"次低报价[^\n]{0,30}50%", "异常低价线2"),
    (r"解密[^\n]{0,60}", "解密要求"),
    (r"演示[^\n]{0,80}", "演示要求"),
]


def read_docx_paragraphs(path):
    zf = zipfile.ZipFile(path)
    root = ET.fromstring(zf.read("word/document.xml"))
    body = root.find(W + "body")
    if body is None:
        body = root
    paras, tables = [], []
    t_index = 0

    def rec(node):
        nonlocal t_index
        for child in node:
            if child.tag == W + "p":
                t = "".join(x.text or "" for x in child.iter(W + "t")).strip()
                paras.append(t)
            elif child.tag == W + "tbl":
                rows = []
                for tr in child.findall(W + "tr"):
                    rows.append(["".join(x.text or "" for x in tc.iter(W + "t")).strip()
                                 for tc in tr.findall(W + "tc")])
                tables.append({"i": t_index, "rows": rows})
                t_index += 1
                rec(child)
            elif child.tag in (W + "sdt", W + "sdtContent", W + "tc", W + "txbxContent"):
                rec(child)
            else:
                if child.find(W + "p") is not None or child.find(W + "tbl") is not None:
                    rec(child)

    rec(body)
    return paras, tables


def main():
    ap = argparse.ArgumentParser(description="招标文件尺子提取")
    ap.add_argument("path")
    ap.add_argument("--clauses", action="store_true")
    ap.add_argument("--symbols", action="store_true")
    ap.add_argument("--forms", action="store_true")
    ap.add_argument("--numbers", action="store_true")
    ap.add_argument("--json")
    args = ap.parse_args()

    if args.path.lower().endswith(".doc"):
        print("❌ .doc 老格式先转 .docx（建议用 WPS COM 自动化；antiword 对中文 GB 文档不可靠）",
              file=sys.stderr)
        sys.exit(2)

    if args.path.lower().endswith((".docx", ".docm")):
        paras, tables = read_docx_paragraphs(args.path)
        full = "\n".join(paras)
    else:
        full = open(args.path, encoding="utf-8", errors="ignore").read()
        paras = [l.strip() for l in full.splitlines()]
        tables = []

    do_all = not (args.clauses or args.symbols or args.forms or args.numbers)
    result = {"file": args.path,
              "stats": {"paragraphs": len(paras), "tables": len(tables),
                        "chars": len(full)}}

    # ---- 1. 符号体系 ----
    if do_all or args.symbols:
        counts = {}
        for s in SYMBOLS:
            c = full.count(s)
            if c:
                counts[s] = c
        result["symbols"] = counts
        print("=" * 78)
        print("【标记符号体系】—— 先确认本项目用哪个符号，再决定数什么")
        for s, c in sorted(counts.items(), key=lambda kv: -kv[1]):
            role = {"★": "实质性/废标线（不得负偏离）", "☆": "参考项",
                    "※": "本包用的是这个！等同 ★（不得缺失或无效）",
                    "▲": "关键技术指标（扣分线，非废标）",
                    "△": "一般技术指标", "◎": "可能也是关键项",
                    "◆": "可能也是关键项"}.get(s, "未知标记")
            print(f"  {s}  {c:>4} 处   {role}")
        if "★" not in counts and "※" not in counts:
            print("  ⚠️ 本招标文件既无 ★ 也无 ※ —— 但**实质性要求仍然存在**：")
            print("     招标通常把'必须'和'应（应当）'句也定义为实质性要求。")

    # ---- 2. 废标条款 ----
    if do_all or args.clauses:
        hits = []
        for i, t in enumerate(paras):
            if any(k in t for k in CLAUSE_KEYS) and 4 < len(t) < 600:
                hits.append({"i": i, "text": t})
        # 去重
        seen, uniq = set(), []
        for h in hits:
            k = h["text"][:40]
            if k not in seen:
                seen.add(k)
                uniq.append(h)
        result["clauses"] = uniq
        print("\n" + "=" * 78)
        print(f"【无效投标 / 废标条款】共 {len(uniq)} 条")
        for h in uniq:
            print(f"  [{h['i']:>4}] {h['text']}")

    # ---- 3. 关键数字 ----
    if do_all or args.numbers:
        nums = []
        for pat, label in KEY_NUMBERS:
            for m in re.finditer(pat, full):
                s = m.group(0).strip()[:160]
                nums.append({"label": label, "text": s})
        seen, uniq = set(), []
        for n in nums:
            if n["text"] not in seen:
                seen.add(n["text"])
                uniq.append(n)
        result["numbers"] = uniq
        print("\n" + "=" * 78)
        print("【关键数字与约束】")
        for n in uniq:
            print(f"  [{n['label']}] {n['text']}")

    # ---- 4. 格式清单 ----
    if do_all or args.forms:
        # 第六章之后的部分才算格式附件
        start = 0
        for i, t in enumerate(paras):
            if re.match(r"^第[五六]章\s*投标文件格式", t):
                start = i
                break
        tail = paras[start:] if start else paras[-400:]
        forms = []
        pat = re.compile(r"(函|表|书|声明|承诺|附件[一二三四五六七八九十\d]+|格式)")
        for t in tail:
            if len(t) < 40 and pat.search(t) and not t.startswith("注"):
                forms.append(t)
        seen, uniq = set(), []
        for f in forms:
            if f not in seen:
                seen.add(f)
                uniq.append(f)
        result["forms"] = uniq
        print("\n" + "=" * 78)
        print(f"【第六章 投标文件格式及附件 · 表单清单】共 {len(uniq)} 项")
        print("（逐项确认投标文件里都有，且栏目名称与顺序一致）")
        for f in uniq:
            print(f"  - {f}")

    # ---- 评分表 ----
    if tables:
        scored = []
        for tb in tables:
            txt = "\n".join(" | ".join(r) for r in tb["rows"])
            if re.search(r"(分值|得分|评分|扣分|满分)", txt) and len(tb["rows"]) >= 2:
                scored.append(tb)
        result["scoring_tables"] = scored
        if scored:
            print("\n" + "=" * 78)
            print(f"【疑似评分表】{len(scored)} 张")
            for tb in scored[:6]:
                print(f"\n--- 表 {tb['i']}（{len(tb['rows'])} 行）---")
                for r in tb["rows"][:80]:
                    cells = [c.replace("\n", " ")[:60] for c in r]
                    if any(cells):
                        print("  | " + " | ".join(cells))

    print("\n" + "=" * 78)
    print("提醒：以上是尺子。审查时每一条发现都要引用这里的原文，不要凭印象判断。")

    if args.json:
        with open(args.json, "w", encoding="utf-8") as fh:
            json.dump(result, fh, ensure_ascii=False, indent=1)
        print(f"→ JSON 已写入 {args.json}")


if __name__ == "__main__":
    main()
