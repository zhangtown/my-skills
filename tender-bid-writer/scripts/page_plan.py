#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
page_plan.py — 篇幅规划的确定性算术（不调模型，可单测）

职责：把"总页数 + 各一级章节技术分 + 各叶子权重"换算成每个叶子的 page_budget / word_budget。
叶子判定、兜底、按权重分页全部在这里，保证数值精确。

算法：
  B = total_pages / A（A=技术总分，仅作展示）
  一级章节页数 = 章节分占比 × total_pages，低于 min_pages_per_chapter 的抬到兜底，
                其余按分数等比缩放，保证 Σ章节页 = total_pages。
  章内：章节页数按叶子 weight 加权分到叶子（叶子至少 1 页）。
  word_budget = round(page_budget × 每页字数)

每页字数按正文排版样式（字号 × 行距）查表（实测值），
默认排版 = 宋体小四 + 1.5倍行距 → 883 字/页。
"""

# (字号, 行距) → 每页字数（宋体正文、A4 默认页边距下的实测经验值）
WORDS_PER_PAGE_TABLE = {
    ("四号", "固定值22"): 860,
    ("四号", "1.5倍"):   731,
    ("四号", "单倍"):    953,
    ("小四", "固定值22"): 1031,
    ("小四", "1.5倍"):   883,
    ("小四", "单倍"):    1299,
}
DEFAULT_FONT_SIZE = "小四"
DEFAULT_LINE_SPACING = "1.5倍"
WORDS_PER_PAGE = WORDS_PER_PAGE_TABLE[(DEFAULT_FONT_SIZE, DEFAULT_LINE_SPACING)]


def words_per_page(font_size=None, line_spacing=None, override=None):
    """按排版样式查每页字数；override 直接指定；查不到时报 KeyError 列出可选组合。"""
    if override:
        return int(override)
    key = (font_size or DEFAULT_FONT_SIZE, line_spacing or DEFAULT_LINE_SPACING)
    if key not in WORDS_PER_PAGE_TABLE:
        opts = "、".join(f"{k[0]}+{k[1]}" for k in WORDS_PER_PAGE_TABLE)
        raise KeyError(f"无 ({key[0]}, {key[1]}) 的每页字数数据，可选：{opts}；"
                       f"或用 --words-per-page 直接指定")
    return WORDS_PER_PAGE_TABLE[key]
TABLE_DISCOUNT_WORDS = 200    # 每个表格约占的版面字数（从字数预算中扣除）
FIGURE_DISCOUNT_WORDS = 220   # 每个配图（含图题）约占的版面字数
MIN_LEAF_WORDS = 250          # 叶子字数预算下限


def is_leaf(node):
    return not node.get("children")


def iter_leaves(node):
    """生成器：返回某节点子树下的所有叶子（含自身若自身是叶子）。"""
    if is_leaf(node):
        yield node
    else:
        for ch in node["children"]:
            yield from iter_leaves(ch)


def alloc_floor(weights, total, floor):
    """把 total 按 weights 分配，每份不低于 floor，且 Σ=total（floor 不可行时等分）。"""
    n = len(weights)
    if n == 0:
        return []
    if total <= floor * n:
        return [total / n] * n  # 连兜底都不够，等分（调用方告警）
    fixed = [False] * n
    alloc = [0.0] * n
    while True:
        used = sum(alloc[i] for i in range(n) if fixed[i])
        free = [i for i in range(n) if not fixed[i]]
        rem = total - used
        wsum = sum(weights[i] for i in free)
        for i in free:
            alloc[i] = rem * (weights[i] / wsum) if wsum > 0 else rem / len(free)
        below = [i for i in free if alloc[i] < floor - 1e-9]
        if not below:
            break
        for i in below:
            fixed[i] = True
            alloc[i] = floor
        if all(fixed):
            break
    return alloc


def apply_page_plan(plan):
    """读取 plan['outline'] 与 plan['page_plan']，原地填 chapter_pages/page_budget/word_budget。
    返回 (warnings)。"""
    warns = []
    pp = plan.setdefault("page_plan", {})
    outline = plan.get("outline", [])
    total = float(pp.get("total_pages", 0) or 0)
    floor = float(pp.get("min_pages_per_chapter", 10) or 0)

    if total <= 0:
        warns.append("page_plan.total_pages 未设置或非正，跳过页数分配。")
        return warns
    if not outline:
        warns.append("outline 为空。")
        return warns

    wpp = int(pp.get("words_per_page") or WORDS_PER_PAGE)
    pp["words_per_page"] = wpp

    scores = [float(ch.get("chapter_score", 0) or 0) for ch in outline]
    A = sum(scores)
    pp["technical_total_score"] = A
    pp["pages_per_point"] = round(total / A, 4) if A > 0 else None
    if A <= 0:
        warns.append("所有一级章节 chapter_score 为 0，按章节数等分页数。")
        scores = [1.0] * len(outline)

    # 兜底不可行时不再直接等分（等分会让评分权重完全失效），
    # 而是把兜底降到"等分份额的一半"，仍按分数加权分配。
    eff_floor = floor
    if total < floor * len(outline):
        eff_floor = max(1.0, round(total / len(outline) * 0.5, 2))
        warns.append(f"总页数 {total:g} 不足以让 {len(outline)} 个一级章节各占 {floor:g} 页兜底，"
                     f"已把兜底降为 {eff_floor:g} 页/章，仍按分数加权分配。"
                     f"建议确认总页数或调低 --min-pages。")

    chapter_pages = alloc_floor(scores, total, eff_floor)
    for ch, cp in zip(outline, chapter_pages):
        ch["chapter_pages"] = round(cp, 2)
        leaves = list(iter_leaves(ch))
        if not leaves:
            continue
        wts = [float(lf.get("weight", 1) or 1) for lf in leaves]
        leaf_floor = 1.0
        if cp < len(leaves) * leaf_floor:
            leaf_floor = max(0.2, round(cp / len(leaves) * 0.5, 2))
            warns.append(f"章节「{ch.get('title','')}」页数 {cp:.1f} 少于叶子数 {len(leaves)}，"
                         f"叶子兜底降为 {leaf_floor:g} 页，仍按 weight 加权。")
        leaf_pages = alloc_floor(wts, cp, leaf_floor)
        for lf, lp in zip(leaves, leaf_pages):
            lf["page_budget"] = round(lp, 2)
            wb = lp * wpp
            el = lf.get("elements") or {}
            if el.get("table"):
                wb -= TABLE_DISCOUNT_WORDS
            if el.get("figure"):
                wb -= FIGURE_DISCOUNT_WORDS
            lf["word_budget"] = max(MIN_LEAF_WORDS, int(round(wb)))
    return warns


def plan_summary(plan):
    """返回一段可读的页数/字数分配表（供审核）。"""
    lines = []
    pp = plan.get("page_plan", {})
    lines.append(f"总页数 {pp.get('total_pages')}｜技术总分 A={pp.get('technical_total_score')}"
                 f"｜每分 B={pp.get('pages_per_point')} 页｜兜底 {pp.get('min_pages_per_chapter')} 页/章"
                 f"｜每页 {pp.get('words_per_page', WORDS_PER_PAGE)} 字"
                 + (f"（{pp.get('body_style')}）" if pp.get('body_style') else ""))
    total_w = 0
    for ch in plan.get("outline", []):
        lines.append(f"■ {ch.get('title','')}  分={ch.get('chapter_score',0)}  页={ch.get('chapter_pages','-')}")
        for lf in iter_leaves(ch):
            total_w += lf.get("word_budget", 0) or 0
            floor = max(int(lf.get("word_budget", 0) or 0), int(lf.get("min_words", 0) or 0))
            n_asp = len(lf.get("aspects", []) or [])
            lines.append(f"    · {lf.get('title','')}  页={lf.get('page_budget','-')}"
                         f"  至少{floor}字  方面{n_asp}个  权重={lf.get('weight',1)}")
    lines.append(f"全篇预算字数合计 ≈ {total_w}")
    return "\n".join(lines)


if __name__ == "__main__":
    import sys
    import json
    if len(sys.argv) != 2:
        print("用法: python page_plan.py plan.json   # 重算并打印分配表")
        sys.exit(1)
    with open(sys.argv[1], "r", encoding="utf-8") as f:
        plan = json.load(f)
    for w in apply_page_plan(plan):
        print("[警告]", w)
    print(plan_summary(plan))
