#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
check_consistency.py — 成稿一致性检查 (方案B 高价值子集)

以 plan.json 的数据字典与每节要点为基准，对 content.json 成稿做三项确定性核对：
  1. 指标矛盾：同一指标在全文出现互相打架的数值 → 错误。
  2. 得分点覆盖：每节 must_keywords 未在该节正文出现 → 错误（漏应答）。
  3. 术语统一：出现 dictionary.terms 里登记的禁用同义词 → 警告。

纯标准库，Windows / Mac 通用。

用法：
  python check_consistency.py content.json plan.json
  返回码 0 = 无错误；1 = 有错误。
"""

import sys
import os
import re
import json
# (re-saved to refresh workspace mount)

# 指标值里抓数字（支持 ≥≤约/千万/百分比/单位）
NUM = r'[≥≤≈<>]?\s*\d[\d,，.]*\s*%?\s*(?:万|千|亿|秒|毫秒|分钟|小时|天|条|类|个|TPS|QPS|ms|s)?'
RE_VALUE_NUM = re.compile(NUM)


def norm_num(s):
    """把一个数值串归一化（去空格、统一符号、全角转半角）。"""
    if not s:
        return ""
    s = s.strip().replace(" ", "")
    trans = str.maketrans("，％０１２３４５６７８９＜＞＝", ",%0123456789<>=")
    s = s.translate(trans)
    s = s.replace("≥", ">=").replace("≤", "<=").replace("约", "").replace("不超过", "<=").replace("不低于", ">=")
    return s


def core_num(s):
    """只保留数值核心（数字+单位/百分号），忽略≥≤等比较符与"不低于/不超过"等措辞。
    用于判定矛盾：核心不同才算冲突，避免"≥1000"与"不低于1000"被误判。"""
    s = norm_num(s).replace(",", "")
    s = re.sub(r'[<>=]', '', s).replace("不低于", "").replace("不超过", "")
    return s


# ---------------- 提取成稿各节文本 ----------------
def iter_sections(content):
    """按 h1/h2 把 body 切成 (h1标题, h2标题, 该节文本) 段。"""
    body = content.get("body", [])
    cur_h1, cur_h2, buf = None, None, []
    out = []

    def flush():
        if cur_h2 is not None:
            out.append((cur_h1, cur_h2, "".join(buf)))

    for b in body:
        if not isinstance(b, dict):
            continue
        t = b.get("type")
        if t == "h1":
            flush()
            cur_h1 = b.get("text", "")
            cur_h2 = None
            buf.clear()
        elif t == "h2":
            flush()
            cur_h2 = b.get("text", "")
            buf.clear()
        else:
            buf.append(_block_text(b))
    flush()
    return out


def _block_text(b):
    t = b.get("type")
    if t in ("h3", "h4", "h5", "p", "hnum"):
        return b.get("text", "")
    if t == "list":
        parts = []

        def walk(items):
            for it in items:
                if isinstance(it, dict):
                    parts.append(it.get("t", ""))
                    if it.get("children"):
                        walk(it["children"])
                else:
                    parts.append(str(it))
        walk(b.get("items", []))
        return "".join(parts)
    if t == "table":
        return "".join(str(c) for row in b.get("rows", []) for c in row) + b.get("title", "")
    if t == "figure":
        return b.get("title", "")
    return ""


def full_text(content):
    return "".join(_block_text(b) for b in content.get("body", []) if isinstance(b, dict))


# ---------------- 三项检查 ----------------
def check_metrics(content, plan, errors, warns):
    """取关键词后 20 字内最近的一个数值与标准值比较，核心不同才报矛盾。
    每个指标的每种冲突值只报一次；跳过年份（如 2026年）避免误报。"""
    text = full_text(content)
    for m in plan.get("dictionary", {}).get("metrics", []):
        canon = m.get("value", "")
        canon_core = core_num(canon)
        if not canon_core:
            continue
        seen = set()
        for kw in m.get("keywords", []):
            for mt in re.finditer(re.escape(kw), text):
                after = text[mt.end(): mt.end() + 20]
                vm = RE_VALUE_NUM.search(after)
                if not vm:
                    continue
                val = vm.group(0).strip()
                if not re.search(r'\d', val):
                    continue
                # 跳过年份：形如 19xx/20xx 且后一字符是"年"
                tail = after[vm.end():vm.end() + 1]
                if tail == "年" and re.fullmatch(r'(19|20)\d{2}', core_num(val)):
                    continue
                cv = core_num(val)
                if cv != canon_core and cv not in seen:
                    seen.add(cv)
                    errors.append(
                        f"指标矛盾：「{m.get('name','')}」标准值 {canon}，"
                        f"但正文「{kw}{after[:12]}…」出现 {val}")


# —— 新 schema（plan.outline 树）：按大纲顺序把成稿切成"每叶子一段文本" ——
def _outline_expected(plan):
    """按文档顺序展开大纲：返回 [(title, level, leaf_node_or_None), ...]。"""
    out = []

    def walk(nodes, depth):
        for nd in nodes:
            lvl = min(depth + 1, 5)
            is_leaf = not nd.get("children")
            out.append((nd.get("title", ""), lvl, nd if is_leaf else None))
            if not is_leaf:
                walk(nd["children"], depth + 1)

    walk(plan.get("outline", []), 0)
    return out


def leaf_texts_by_order(content, plan):
    """顺序对齐成稿标题与大纲标题（同文本同层级同顺序），
    叶子标题之后、下一个大纲标题之前的所有块（含模型加的更深子标题）归入该叶子。
    返回 (dict: 叶子序号->文本, expected 列表, 已匹配到第几个大纲标题)。"""
    expected = _outline_expected(plan)
    texts = {}
    ei = 0
    cur_leaf = None       # 当前叶子在 expected 中的序号
    leaf_index = {}       # expected 下标 -> 叶子序号
    li = 0
    for idx, (_t, _l, nd) in enumerate(expected):
        if nd is not None:
            leaf_index[idx] = li
            li += 1

    for b in content.get("body", []):
        if not isinstance(b, dict):
            continue
        t = b.get("type", "")
        # 序号标题（引擎把末级标题降级为"（1）"）：仅按文本匹配大纲叶子（层级已被抹平）
        if t == "hnum":
            txt = b.get("text", "")
            if ei < len(expected) and txt == expected[ei][0] and expected[ei][2] is not None:
                cur_leaf = leaf_index.get(ei)
                ei += 1
                continue
            if cur_leaf is not None:
                texts[cur_leaf] = texts.get(cur_leaf, "") + txt
            continue
        if t in ("h1", "h2", "h3", "h4", "h5"):
            lvl = int(t[1])
            txt = b.get("text", "")
            if ei < len(expected) and txt == expected[ei][0] and lvl == expected[ei][1]:
                cur_leaf = leaf_index.get(ei)   # 非叶子标题 → None
                ei += 1
                continue
            # 与大纲不匹配的标题 = 叶子内部模型加的子标题，文本计入当前叶子
            if cur_leaf is not None:
                texts[cur_leaf] = texts.get(cur_leaf, "") + txt
            continue
        if cur_leaf is not None:
            texts[cur_leaf] = texts.get(cur_leaf, "") + _block_text(b)
    return texts, expected, ei


def check_coverage(content, plan, errors, warns):
    # —— 新 schema：plan.outline 树（plan.py 的产物）——
    if plan.get("outline"):
        texts, expected, ei = leaf_texts_by_order(content, plan)
        if ei < len(expected):
            warns.append(f"覆盖检查：{len(expected) - ei} 个大纲标题未在成稿中按序匹配"
                         f"（从「{expected[ei][0]}」起），其后叶子无法定位，请核对成稿结构")
        li = 0
        for (_title, _lvl, nd) in expected:
            if nd is None:
                continue
            txt = texts.get(li)
            li += 1
            if txt is None:
                warns.append(f"覆盖检查：未在成稿中定位到叶子「{nd.get('title','')}」")
                continue
            for kw in nd.get("must_keywords", []) or []:
                if kw and kw not in txt:
                    errors.append(
                        f"得分点漏应答：叶子「{nd.get('title','')}」缺少关键词「{kw}」"
                        f"（评分点：{'、'.join(nd.get('scoring_points', []) or []) or '—'}）")
        return
    # —— 旧 schema 兼容：plan.chapters[].sections[]（手写 plan）——
    sections = {h2: txt for (_h1, h2, txt) in iter_sections(content)}
    for ch in plan.get("chapters", []):
        for se in ch.get("sections", []):
            title = se.get("title", "")
            txt = sections.get(title)
            if txt is None:
                warns.append(f"覆盖检查：未在成稿中找到章节「{title}」")
                continue
            for kw in se.get("must_keywords", []):
                if kw and kw not in txt:
                    errors.append(f"得分点漏应答：章节「{title}」缺少关键词「{kw}」"
                                  f"（评分点：{'、'.join(se.get('scoring_points', [])) or '—'}）")


# —— 参考资料审查报告（排版前人工闸口用）——
_METRIC_UNIT = re.compile(r'[≥≤<>]|%|万|千|亿|秒|毫秒|分钟|小时|天|条|类|个|TPS|QPS|ms')


def _looks_like_metric(val):
    """粗判一个数值串是否像'指标'（含比较符/百分号/常见单位），过滤掉普通计数与年份。"""
    if re.fullmatch(r'\s*(19|20)\d{2}\s*年?\s*', val):
        return False
    return bool(_METRIC_UNIT.search(val))


def check_reference_report(content, plan, errors, warns):
    """审查闸口三件事（全部为警告，供人工核对，不阻断）：
      1. 列清单：哪些章节参考了外部资料、引用了参考文件的哪一节（含自动匹配标注）。
      2. 疑似指标告警：被参考章节正文里出现、但不在数据字典里的指标型数字 → 提示核对是否与招标文件冲突。
      3. 重复引用提示：同一「文件+节」被多个章节引用 → 可能造成内容重复。
    references_used 由 generate.py 写入 content.meta；无参考资料时本函数直接返回。

    fail-loud：usage 里 status=="未匹配" 的是"精准绑定却没解析上"的失败项——用户明确绑了、
    却因章节号/标题对不上而静默退回纯生成。这类项计入 errors（非零退出、[错误] 醒目提示），
    绝不淹没在普通警告里。"""
    usage = (content.get("meta") or {}).get("references_used") or []
    if not usage:
        return
    # —— fail-loud：先把"精准绑定解析失败"的项响亮报为错误 ——
    failed = [u for u in usage if u.get("status") == "未匹配"]
    usage = [u for u in usage if u.get("status") != "未匹配"]
    if failed:
        errors.append(f"参考绑定失败 {len(failed)} 处：这些章节明确绑定了参考、却没解析上，"
                      f"已退回纯大模型生成，成稿会与参考相差很大——请核对章节号/标题后重绑再重生成。")
        for u in failed:
            errors.append(f"    ✗ 章节「{u.get('leaf','')}」→《{u.get('file','')}》"
                          f"「{u.get('section','')}」：{u.get('reason','未匹配')}")
    if not usage:
        return
    warns.append(f"—— 参考资料审查（共 {len(usage)} 个章节参考了外部资料，请人工核对）——")
    _MODE_CN = {"adapt": "改写借鉴", "keep_headings": "保子标题·优化", "verbatim": "完整照抄"}
    for u in usage:
        how = f"自动匹配(相似度{u.get('score','?')})" if u.get("auto") else "手动绑定"
        mode_cn = _MODE_CN.get(u.get("mode", "adapt"), u.get("mode", "adapt"))
        rep = f"，已按字典替换冲突指标{u['replaced']}处" if u.get("replaced") else ""
        warns.append(f"  · 章节「{u.get('leaf','')}」参考《{u.get('file','')}》"
                     f"「{u.get('section','')}」节（{mode_cn}，{how}，摘录约{u.get('chars','?')}字{rep}）")
    # 重复引用
    seen = {}
    for u in usage:
        seen.setdefault((u.get("file"), u.get("section")), []).append(u.get("leaf"))
    for (fn, sec), leaves in seen.items():
        if len(leaves) > 1:
            warns.append(f"  重复引用：《{fn}》「{sec}」被多个章节引用（{'、'.join(leaves)}），"
                         f"请检查是否内容重复。")
    # 疑似指标：被参考章节里出现、字典没有的指标型数字
    dict_cores = {core_num(m.get("value", "")) for m in
                  plan.get("dictionary", {}).get("metrics", []) if m.get("value")}
    texts, _expected, _ei = leaf_texts_by_order(content, plan)
    title_text = {}
    li = 0
    for (title, _lvl, nd) in _outline_expected(plan):
        if nd is not None:
            title_text[title] = texts.get(li, "")
            li += 1
    ref_titles = {u.get("leaf") for u in usage}
    for title in ref_titles:
        txt = title_text.get(title, "")
        if not txt:
            continue
        flagged = []
        for vm in RE_VALUE_NUM.finditer(txt):
            val = vm.group(0).strip()
            if not re.search(r'\d', val) or not _looks_like_metric(val):
                continue
            if core_num(val) in dict_cores:
                continue
            if val not in flagged:
                flagged.append(val)
        if flagged:
            warns.append(f"  疑似指标：章节「{title}」出现字典外指标数字 {('、'.join(flagged[:8]))}"
                         + ("…" if len(flagged) > 8 else "")
                         + "，请确认是否来自参考资料且与招标文件不冲突。")


# 疑似投标人机构名后缀（暗标查漏；保守取强机构后缀，避免误伤"数据中心/监控中心"等）
_ORG_SUFFIX = re.compile(
    r'[一-龥A-Za-z0-9（）()·]{2,30}?'
    r'(?:股份有限公司|有限责任公司|有限公司|集团有限公司|集团股份|集团公司|集团|'
    r'科技股份|设计研究院|设计院|研究院|勘察院|事务所)')


def check_blind_bid(content, plan, errors, warns):
    """暗标查漏（仅 meta.blind_bid 为真时执行；靠规则+提示词，启发式告警不阻断）：
      1. 扫描疑似投标人机构名（…有限公司/集团/研究院/事务所 等后缀）。
      2. 人名与带 logo 图片程序无法可靠识别，末尾提示人工复核。"""
    blind = (content.get("meta") or {}).get("blind_bid") or plan.get("meta", {}).get("blind_bid")
    if not blind:
        return
    text = full_text(content)
    hits = sorted({m.group(0).strip() for m in _ORG_SUFFIX.finditer(text)})
    if hits:
        warns.append(f"—— 暗标查漏：正文出现 {len(hits)} 处疑似机构名，暗标下须删除或匿名化 ——")
        for h in hits[:20]:
            warns.append(f"  · 疑似机构名：{h}")
        if len(hits) > 20:
            warns.append(f"  · …另有 {len(hits) - 20} 处，详见成稿")
    warns.append("—— 暗标提醒：人员姓名/职务、带 logo 或单位标识的图片程序无法可靠识别，"
                 "请务必人工通读复核，确保无任何可推断投标人身份的痕迹。——")


def check_terms(content, plan, errors, warns):
    text = full_text(content)
    for t in plan.get("dictionary", {}).get("terms", []):
        canon = t.get("canonical", "")
        for fb in t.get("forbidden", []):
            if fb and fb in text:
                warns.append(f"术语不统一：出现禁用同义词「{fb}」，应统一为「{canon}」")


def main():
    if len(sys.argv) != 3:
        print("用法: python check_consistency.py content.json plan.json")
        return 1
    with open(sys.argv[1], "r", encoding="utf-8") as f:
        content = json.load(f)
    with open(sys.argv[2], "r", encoding="utf-8") as f:
        plan = json.load(f)

    errors, warns = [], []
    check_metrics(content, plan, errors, warns)
    check_coverage(content, plan, errors, warns)
    check_terms(content, plan, errors, warns)
    check_reference_report(content, plan, errors, warns)
    check_blind_bid(content, plan, errors, warns)

    for w in warns:
        print(f"[警告] {w}")
    for e in errors:
        print(f"[错误] {e}")
    print(f"\n一致性检查：{len(errors)} 个错误，{len(warns)} 个警告。", end="")
    if errors:
        print(" 建议定点重写相关章节后重检。")
        return 1
    print(" 通过。" if not warns else " 无硬冲突，建议处理警告。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
