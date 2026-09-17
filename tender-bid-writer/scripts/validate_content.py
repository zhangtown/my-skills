#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
validate_content.py — content.json 校验器 (方案A)

把 build_docx.py "默认你会满足" 的结构假设显式化，在渲染前用确定性代码逐条检查，
用人能看懂的话报出来。纯标准库实现，Windows / Mac / Linux 通用，无需额外安装。

分两级：
  - 错误 (ERROR)：会让引擎崩溃或静默渲染错的结构问题 —— 阻断生成。
  - 警告 (WARN) ：质量/规范问题 (手写编号、短语碎片、跳级等) —— 提示但不阻断。

用法：
  python validate_content.py content.json
  返回码 0 = 无错误 (可能有警告)；1 = 有错误或文件无法解析。

也可被 build_docx.py 直接 import：validate(data, base_dir) -> (errors, warns)
"""

import sys
import os
import re
import json

# ----------------------------- 常量 -----------------------------
HEADING_TYPES = {"h1", "h2", "h3", "h4", "h5"}
# hnum 是引擎内部块（末级标题降级为"（1）"序号标题），由 generate.py 生成、build_docx.py 渲染
VALID_TYPES = HEADING_TYPES | {"p", "list", "table", "figure", "hnum"}
MAX_LIST_DEPTH = 3
MAX_WIDTH_CM = 17.0
PARA_MAX_CHARS = 500       # 单段字数上限（超出应拆段）

# 手写编号正则 (只匹配文本开头，误报率低)
RE_NUM_HEAD = re.compile(r'^\s*\d+([.．]\d+)*[\s、.．:：]')      # 1 / 1.1 / 1.1.1.
RE_NUM_CN = re.compile(r'^\s*[一二三四五六七八九十]+\s*[、.．]')   # 一、二、
RE_NUM_PAREN = re.compile(r'^\s*[（(]\s*\d+\s*[）)]')            # （1）
RE_NUM_HALF = re.compile(r'^\s*\d+\s*[）)]')                    # 1）
RE_NUM_CIRCLED = re.compile(r'^\s*[①-⑳]')            # ①..⑳
RE_TBL_CAP = re.compile(r'^\s*表\s*\d+\s*[-－—]')               # 表2-1
RE_FIG_CAP = re.compile(r'^\s*图\s*\d+\s*[-－—]')               # 图2-1
# 投标人自称（应在生成阶段规范化去除；宾格位残留由此告警提示人工核对）
RE_SELF_REF = re.compile(r'我方|我公司|我司|我单位|本公司|本单位')

# 短语碎片判定参数
FRAG_MIN_SEGS = 4      # 顿号/分号切出的片段数下限
FRAG_MAX_ENDERS = 1    # 句末标点 (。！？) 数量上限
FRAG_MAX_AVG = 14      # 平均片段字符数上限


def _zh_len(text):
    """段落字数：中文按字符计，连续 ASCII（英文/数字）按空白切成的词计一个。
    与 generate.py 的 cjk_count 口径一致，避免两处判定打架。"""
    t = str(text)
    cjk = len(re.findall(r'[一-鿿]', t))
    ascii_tokens = len(re.findall(r'[A-Za-z0-9]+', t))
    return cjk + ascii_tokens


def _is_manual_number(text):
    """文本开头是否疑似手写标题编号。"""
    return bool(RE_NUM_HEAD.match(text) or RE_NUM_CN.match(text))


def _is_manual_list_marker(text):
    """文本开头是否疑似手写列表序号。"""
    return bool(RE_NUM_PAREN.match(text) or RE_NUM_HALF.match(text)
                or RE_NUM_CIRCLED.match(text) or RE_NUM_CN.match(text))


def _is_fragment_pile(text):
    """是否为"短语碎片堆砌"：多个顿号/分号片段、几乎没有句号、平均很短。"""
    t = text.strip()
    if not t:
        return False
    segs = [s for s in re.split(r'[；、]', t) if s.strip()]
    enders = len(re.findall(r'[。！？]', t))
    if len(segs) >= FRAG_MIN_SEGS and enders <= FRAG_MAX_ENDERS:
        avg = len(t) / len(segs)
        if avg < FRAG_MAX_AVG:
            return True
    return False


def _walk_list(items, errors, warns, loc, depth=1):
    """递归校验列表：深度、结构、手写序号。"""
    if not isinstance(items, list):
        errors.append(f"{loc}: list.items 应为数组，实际为 {type(items).__name__}")
        return
    if depth == 1 and len(items) == 0:
        warns.append(f"{loc}: list 为空")
    for i, item in enumerate(items):
        iloc = f"{loc}.items[{i}]"
        if isinstance(item, dict):
            t = item.get("t", "")
            if not str(t).strip():
                warns.append(f"{iloc}: 列表项文本 't' 为空")
            elif _is_manual_list_marker(str(t)):
                warns.append(f"{iloc}: 疑似手写序号「{str(t)[:12]}」—— 序号由引擎自动生成，请删除")
            if str(t) and RE_SELF_REF.search(str(t)):
                warns.append(f"{iloc}: 列表项出现投标人自称「{RE_SELF_REF.search(str(t)).group(0)}」——应改为客观陈述")
            children = item.get("children")
            if children:
                if depth >= MAX_LIST_DEPTH:
                    warns.append(f"{iloc}: 列表嵌套超过 {MAX_LIST_DEPTH} 级，超出部分会被引擎忽略")
                else:
                    _walk_list(children, errors, warns, iloc, depth + 1)
        elif isinstance(item, str):
            if _is_manual_list_marker(item):
                warns.append(f"{iloc}: 疑似手写序号「{item[:12]}」—— 序号由引擎自动生成，请删除")
        else:
            errors.append(f"{iloc}: 列表项应为对象或字符串，实际为 {type(item).__name__}")


def validate(data, base_dir="."):
    """校验入口。返回 (errors, warns)，均为字符串列表。"""
    errors, warns = [], []

    if not isinstance(data, dict):
        errors.append("顶层应为 JSON 对象 {meta, body}")
        return errors, warns

    meta = data.get("meta", {})
    if meta is not None and not isinstance(meta, dict):
        errors.append("meta 应为对象")

    body = data.get("body")
    if body is None:
        errors.append("缺少 body")
        return errors, warns
    if not isinstance(body, list):
        errors.append("body 应为数组")
        return errors, warns
    if len(body) == 0:
        errors.append("body 为空，没有任何内容块")
        return errors, warns

    prev_level = 0          # 上一个标题层级，用于跳级检测
    seen_h1 = False
    sib_seen = {}           # level -> 当前父标题下该级已出现的子标题文本集合（查同父重复）
    hnum_seen = set()       # 当前父标题下已出现的序号标题文本（查降级块重复）
    for idx, block in enumerate(body):
        loc = f"body[{idx}]"
        if not isinstance(block, dict):
            errors.append(f"{loc}: 内容块应为对象，实际为 {type(block).__name__}")
            continue
        btype = block.get("type")
        if btype not in VALID_TYPES:
            errors.append(f"{loc}: 非法 type「{btype}」，允许：{sorted(VALID_TYPES)}")
            continue
        loc = f"{loc}({btype})"

        # ---- 标题 ----
        if btype in HEADING_TYPES:
            level = int(btype[1])
            text = str(block.get("text", ""))
            if not text.strip():
                errors.append(f"{loc}: 标题文本为空")
            if _is_manual_number(text):
                warns.append(f"{loc}: 疑似手写编号「{text[:12]}」—— 编号由引擎自动生成，请删除")
            if level == 1:
                seen_h1 = True
            if prev_level and level > prev_level + 1:
                warns.append(f"{loc}: 标题跳级 (h{prev_level}→h{level})，建议逐级递进")
            if level > 1 and not seen_h1 and prev_level == 0:
                warns.append(f"{loc}: 正文以 h{level} 开头，缺少 h1 一级标题")
            # 同父重复子标题检测：新标题会打开更深层子树，先清掉更深级别的记录，
            # 再在本级集合里查重（本级集合即"当前父标题下的兄弟标题"）。
            for L in [L for L in sib_seen if L > level]:
                sib_seen.pop(L)
            hnum_seen.clear()      # 标题一变，序号标题的父作用域也随之重置
            norm = text.strip()
            bucket = sib_seen.setdefault(level, set())
            if norm and norm in bucket:
                warns.append(f"{loc}: 同一父标题下出现重复子标题「{norm[:16]}」"
                             f"—— 可能是分块续写重号或结构分解混乱，请核对")
            bucket.add(norm)
            prev_level = level

        # ---- 正文段落 ----
        elif btype == "p":
            text = str(block.get("text", ""))
            if not text.strip():
                errors.append(f"{loc}: 段落文本为空")
            else:
                if "\n" in text:
                    warns.append(f"{loc}: 段落含换行符，应拆成多个 p 块")
                if _is_manual_number(text) or _is_manual_list_marker(text):
                    warns.append(f"{loc}: 段落以编号/序号开头「{text[:12]}」—— 编号交给引擎或改用 list 块")
                if _is_fragment_pile(text):
                    warns.append(f"{loc}: 疑似短语碎片堆砌「{text[:20]}…」—— 请展开成完整句子 (见 content_guide 第五节)")
                if RE_SELF_REF.search(text):
                    warns.append(f"{loc}: 出现投标人自称「{RE_SELF_REF.search(text).group(0)}」"
                                 f"—— 应改为客观陈述，宾格位请人工改写")
                if _zh_len(text) > PARA_MAX_CHARS:
                    warns.append(f"{loc}: 段落约 {_zh_len(text)} 字，超过 {PARA_MAX_CHARS} 字上限"
                                 f"「{text[:16]}…」—— 引擎会自动按句拆分，建议内容上分层次组织")

        # ---- 序号标题（引擎内部块）----
        elif btype == "hnum":
            text = str(block.get("text", ""))
            if not text.strip():
                errors.append(f"{loc}: 序号标题文本为空")
            if _is_manual_number(text) or _is_manual_list_marker(text):
                warns.append(f"{loc}: 序号标题以编号开头「{text[:12]}」—— 序号由引擎自动生成，请删除")
            if RE_SELF_REF.search(text):
                warns.append(f"{loc}: 序号标题出现投标人自称「{RE_SELF_REF.search(text).group(0)}」——应改为客观陈述")
            lvl = int(block.get("level", 0) or 0)
            norm = text.strip()
            if norm and (lvl, norm) in hnum_seen:
                warns.append(f"{loc}: 同一父标题下出现重复序号标题「{norm[:16]}」"
                             f"—— 可能是分块续写重号或结构分解混乱，请核对")
            hnum_seen.add((lvl, norm))

        # ---- 列表 ----
        elif btype == "list":
            _walk_list(block.get("items"), errors, warns, loc)

        # ---- 表格 ----
        elif btype == "table":
            header = block.get("header")
            rows = block.get("rows")
            if not isinstance(header, list) or len(header) == 0:
                errors.append(f"{loc}: table.header 缺失或为空")
                continue
            ncols = len(header)
            if not str(block.get("title", "")).strip():
                warns.append(f"{loc}: 表格缺少 title")
            elif RE_TBL_CAP.match(str(block.get("title", ""))):
                warns.append(f"{loc}: 表题含手写编号「表X-」—— 引擎会自动加前缀，请删除")
            if rows is None or not isinstance(rows, list):
                errors.append(f"{loc}: table.rows 缺失或不是数组")
                continue
            if len(rows) == 0:
                warns.append(f"{loc}: 表格没有数据行")
            for r, row in enumerate(rows):
                if not isinstance(row, list):
                    errors.append(f"{loc}.rows[{r}]: 行应为数组，实际为 {type(row).__name__}")
                elif len(row) != ncols:
                    errors.append(f"{loc}.rows[{r}]: 列数 {len(row)} 与表头 {ncols} 不一致")

        # ---- 图片 ----
        elif btype == "figure":
            if not str(block.get("title", "")).strip():
                warns.append(f"{loc}: figure 缺少 title (图题)")
            elif RE_FIG_CAP.match(str(block.get("title", ""))):
                warns.append(f"{loc}: 图题含手写编号「图X-」—— 引擎会自动加前缀，请删除")
            w = block.get("width_cm", 12.0)
            try:
                wf = float(w)
                if wf <= 0:
                    errors.append(f"{loc}: width_cm 应为正数，实际 {w}")
                elif wf > MAX_WIDTH_CM:
                    warns.append(f"{loc}: width_cm={wf} 超过版心 {MAX_WIDTH_CM}cm，引擎会自动限到 {MAX_WIDTH_CM}cm")
            except (TypeError, ValueError):
                errors.append(f"{loc}: width_cm 应为数字，实际「{w}」")
            img = block.get("img")
            if img:
                p = img if os.path.isabs(img) else os.path.join(base_dir, img)
                if not os.path.exists(p):
                    warns.append(f"{loc}: 配图文件不存在「{img}」—— 引擎将插入文字占位框")

    return errors, warns


def main():
    if len(sys.argv) != 2:
        print("用法: python validate_content.py content.json")
        return 1
    path = sys.argv[1]
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"[错误] 文件不存在: {path}")
        return 1
    except json.JSONDecodeError as e:
        print(f"[错误] JSON 解析失败: 第{e.lineno}行第{e.colno}列 — {e.msg}")
        return 1

    errors, warns = validate(data, os.path.dirname(os.path.abspath(path)))

    for w in warns:
        print(f"[警告] {w}")
    for e in errors:
        print(f"[错误] {e}")

    print(f"\n校验完成：{len(errors)} 个错误，{len(warns)} 个警告。", end="")
    if errors:
        print(" 存在错误，应修正后再生成。")
        return 1
    print(" 可以生成。" if not warns else " 无阻断性错误，建议处理警告后生成。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
