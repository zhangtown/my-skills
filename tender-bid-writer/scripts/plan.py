#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
plan.py — 规划阶段：用户大纲 + 评分标准 → plan.json

分工：
  - deepseek-v4-pro 负责"理解"：抽数据字典(指标/术语/选型)、给每个一级章节判技术分、
    给每个叶子写 brief / 必含关键词 / 内容轻重 weight / 模板 / 是否出表图。
  - Python(page_plan) 负责"算术"：B、章节页、10页兜底+重归一、章内按 weight 分页、字数预算。

**永久规则**：绝不改用户大纲结构。v4-pro 只能按节点 id 回填字段，
标题文本/层级/顺序/父子关系一律由 Python 从用户输入保留，模型无权改动。

用户输入 outline.json：
  { "meta": {...},
    "outline": [ {"title":"...","note":"(可选,本节要写什么)","chapter_score":(可选),
                  "children":[ {"title":"..."} ]} ] }

用法：
  python plan.py --outline outline.json --pages 80 --out plan.json \
      [--scoring scoring.txt] [--requirements req.txt] [--min-pages 10] \
      [--model deepseek-v4-pro] [--mock]
"""

import sys
import os
import re
import json
import argparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from page_plan import apply_page_plan, plan_summary, is_leaf, words_per_page  # noqa: E402

PLAN_MODEL = os.environ.get("DEEPSEEK_PLAN_MODEL", "deepseek-v4-pro")

SYSTEM = """你是中国招标投标技术标的规划专家。给你"采购需求 + 评分标准 + 投标大纲(树)"，
你只做规划，不写正文，且【绝对不能改动大纲的标题文本、层级、顺序、父子结构】。
你的输出只按节点 id 回填字段。请输出一个 JSON 对象：
{
 "dictionary": {
   "metrics":[{"name":"并发数","value":"≥1000","keywords":["并发"]}],
   "terms":[{"canonical":"一张图","forbidden":["一张图平台"]}],
   "stack":[{"role":"CPU","value":"鲲鹏/飞腾"},{"role":"数据库","value":"达梦/人大金仓"}],
   "fixed":{"项目工期":"..."}
 },
 "chapters":[{"id":"0","chapter_score":10}],     // 仅一级章节：把评分标准里技术部分的分数映射并汇总到该章
 "leaves":[{"id":"0.0","brief":"本节要写什么内容——具体交代这一节要论述/说明/证明什么，贴评分点，不要泛泛",
            "aspects":["从哪个方面/角度展开1","方面2","方面3","方面4"],
            "min_words":800,
            "scoring_points":["..."],
            "must_keywords":["评分原词，原样命中"],"weight":2,"template":null,
            "elements":{"table":false,"figure":false}}]
}
要求：
- chapters 只填评分标准中【技术部分】的分数，商务/价格分不计入；分数之和即技术总分 A。
- 每个叶子给 weight(内容轻重，正数，用于章内分配页数)、must_keywords(尽量用评分表原话)。
- 【brief】说清本节要写什么内容（这一节承担什么论述任务、要交代清楚哪些事）。
- 【aspects】给出本节正文应当从哪些方面/维度逐一展开，每条是一个**具体的撰写角度**
  （例如"当前业务痛点与数据现状""与一张图平台的对接方式""指标如何量化达成""风险与应对"），
  不要写成空泛的口号；一般 3~8 条，内容越重要、字数越多的叶子给的方面越多、越细。
- 【min_words】给出本节至少应写多少中文字（正整数）。这是内容颗粒度的下限参考；
  最终字数预算仍由页数规划统一核算，但 min_words 要与本节分量相称，不要低于 500。
- 【依据用户备注细化】若某叶子在大纲里带有 [备注]（用户对本节的写作要求），
  必须据此细化 brief 与 aspects——把用户要求拆成具体的撰写角度；
  若备注里写明了"从哪些方面写""至少多少字"之类要求，须原样体现到 aspects 与 min_words。
- brief 要具体到"写哪些点"，不要泛泛。dictionary 把关键指标/术语/信创选型一次定死。
- 大纲可能分多批回填：每次只回填用户指定 id 的叶子，一个都不能漏；
  未要求输出 dictionary/chapters 时不要输出。
- 只输出 JSON，不要解释、不要 markdown 围栏。id 必须与我给的完全一致。"""


# ---------------- 数据字典独立抽取（保险层）----------------
DICT_SYSTEM = """你是中国招标投标技术标的规划专家，专职从"采购需求 + 评分标准"里
穷尽抽取【数据字典】——它是全篇唯一事实源。你只输出字典，不写正文、不碰大纲。

必须逐类系统扫描，宁多勿漏（每一类都要过一遍，有就抽、没有留空数组/空对象）：
1. 量化指标 metrics：并发数、准确率、响应时间、可用性、吞吐、工期、质保期、
   培训人次、验收合格率等一切带数值或比较符(≥ ≤ % 倍 次 人 天 小时)的硬性要求。
2. 人员要求（放 metrics 或 fixed）：项目团队总人数、各角色人数、职称/资格证书、
   "关键人员不得更换"、驻场人数、负责人指定等——招标最常考、最易漏，务必逐条抽。
3. 信创/国产化选型 stack：CPU、操作系统、数据库、中间件等指定或默认的国产选型。
4. 统一术语 terms：招标高频专有名词及其易混同义词（同义词写进 forbidden，防全篇串味）。
5. 固定事实 fixed：工期起算口径、质保年限、服务响应方式、部署方式等一次定死的非数值事实。
6. ★/▲/☆ 标注的条款：通常是废标项或关键评分项，必须优先、完整纳入。

我会附一份【候选清单】（从原文确定性捞取、可能含指标的行）。你必须逐条判断：
属于字典的归类抽取，确实不是指标的才忽略——不得整条跳过不看。

只输出 JSON（不要解释、不要 markdown 围栏）：
{
 "metrics":[{"name":"驻场人数","value":"≥3人（软件开发≥2、软件维护≥1）","keywords":["驻场"]}],
 "terms":[{"canonical":"一张图","forbidden":["一张图平台"]}],
 "stack":[{"role":"CPU","value":"鲲鹏/飞腾"}],
 "fixed":{"项目工期":"合同签订之日起一年"}
}
- value 要带上原文约束（数量、比较符、范围、附加条件），不要只写个词。
- keywords 放该指标在正文里会出现的检索词，供一致性检查命中。
- 招标文件没提到的绝不编造；但凡原文出现的硬要求，一条都不能漏。"""


# 确定性候选捞取：从原文扫出"可能是指标"的行，喂模型甄别并做覆盖率兜底
_STAR_RE = re.compile(r"[★▲☆]")
_NUM_RE = re.compile(
    r"(?:≥|≤|≧|≦|＞|＜|>|<|不少于|不低于|不超过|不得少于|不得低于|至少|最多|"
    r"\d+\s*(?:%|％|人|名|年|个月|月|天|日|小时|分钟|秒|次|万|亿|元|个|台|套|路|"
    r"条|项|级|类|G[Bb]?|T[Bb]?|M[Bb]?|core|核))")


def harvest_candidates(*texts):
    """确定性地从采购需求/评分标准原文捞取候选指标行（含 ★/▲ 或 数值+单位/比较符）。
    仅做"有没有、大概几条"的粗筛，真正归类交给模型；返回去重短句列表。"""
    cands, seen = [], set()
    for t in texts:
        if not t or t == "（未提供）":
            continue
        for raw in re.split(r"[\n\r]+", t):
            line = raw.strip(" \t　")
            if len(line) < 4:
                continue
            if _STAR_RE.search(line) or _NUM_RE.search(line):
                seg = line[:80]
                if seg not in seen:
                    seen.add(seg)
                    cands.append(seg)
    return cands


def _norm_dict(obj):
    obj = obj if isinstance(obj, dict) else {}
    return {"metrics": obj.get("metrics") or [],
            "terms": obj.get("terms") or [],
            "stack": obj.get("stack") or [],
            "fixed": obj.get("fixed") or {}}


def _dict_size(d):
    return (len(d.get("metrics") or []) + len(d.get("stack") or [])
            + len(d.get("terms") or []) + len(d.get("fixed") or {}))


def _merge_dicts(a, b):
    """并集去重合并两次抽取结果，保住任一次抽到的条目（去重键：name/canonical/role）。"""
    out, b = _norm_dict(a), _norm_dict(b)

    def add(key, kfield):
        seen = {(x.get(kfield) or "").strip() for x in out[key]}
        for x in b[key]:
            k = (x.get(kfield) or "").strip()
            if k and k not in seen:
                out[key].append(x)
                seen.add(k)

    add("metrics", "name")
    add("terms", "canonical")
    add("stack", "role")
    merged = dict(out["fixed"])
    merged.update(b["fixed"])
    out["fixed"] = merged
    return out


def _dict_thin(d, cands):
    """判断字典是否明显偏薄、需要定向补抽。"""
    if not (d.get("metrics") or d.get("stack")):
        return True   # 指标和信创选型全空，几乎必漏
    n = len(cands)
    return n >= 6 and _dict_size(d) < max(4, int(n * 0.3))


def dict_coverage_warns(d, cands):
    """字典覆盖率告警，并入 plan 的 [警告] 一起打印，供人工冻结前处理。"""
    warns = []
    if cands and not (d.get("metrics") or d.get("stack")):
        warns.append(
            f"数据字典的 metrics/stack 为空，但原文捞到 {len(cands)} 条疑似指标行——"
            f"几乎可以确定有遗漏，冻结前务必逐条核对采购需求（尤其 ★条款与量化要求）！")
    elif cands and _dict_size(d) < max(4, int(len(cands) * 0.3)):
        warns.append(
            f"数据字典仅 {_dict_size(d)} 条，明显少于原文 {len(cands)} 条疑似指标行，"
            f"可能漏抽，冻结前请对照候选清单复核。")
    return warns


def extract_dictionary(client, model, scoring, req, max_tokens):
    """独立的数据字典抽取：一次调用只干这件事（不与叶子回填抢注意力/token），
    并用确定性候选清单甄别 + 覆盖率兜底重试。返回 (dictionary, candidates, warnings)。"""
    cands = harvest_candidates(scoring, req)
    cand_block = ""
    if cands:
        shown = cands[:60]
        cand_block = ("\n\n【候选清单（逐条判断是否为指标，勿整条跳过）】\n"
                      + "\n".join(f"- {c}" for c in shown))
        if len(cands) > 60:
            cand_block += f"\n…（另有 {len(cands) - 60} 条同类，请一并甄别）"
    base = f"【采购需求】\n{req}\n\n【评分标准】\n{scoring}{cand_block}"

    def call(extra=""):
        obj = client.chat_json(
            [{"role": "system", "content": DICT_SYSTEM},
             {"role": "user", "content": base + extra}],
            temperature=0.3, max_tokens=max_tokens, model=model)
        return _norm_dict(obj)

    print("[plan] 抽取数据字典（独立调用）…", flush=True)
    d = call()
    if _dict_thin(d, cands):
        print("[plan] 数据字典偏薄，定向补抽一次…", flush=True)
        d = _merge_dicts(d, call(
            "\n\n上一次抽取的字典条目偏少、疑似遗漏。请重新逐条核对候选清单与采购需求全文，"
            "把所有量化指标、人员要求（含数量/职称/不得更换/驻场/负责人）、★条款、信创选型"
            "补全后，重新完整输出字典。"))
    return d, cands, dict_coverage_warns(d, cands)


# ---------------- 大纲 id 编号 / 扁平化 ----------------
def assign_ids(outline):
    """给每个节点一个稳定 id（路径下标），返回 (chapters_flat, leaves_flat)。"""
    chapters, leaves = [], []

    def walk(nodes, prefix, depth):
        for i, nd in enumerate(nodes):
            nid = f"{prefix}{i}" if prefix == "" else f"{prefix}.{i}"
            nd["_id"] = nid
            if depth == 0:
                chapters.append(nd)
            if is_leaf(nd):
                leaves.append(nd)
            else:
                walk(nd["children"], nid, depth + 1)

    walk(outline, "", 0)
    return chapters, leaves


def flat_view(outline):
    """给模型看的扁平大纲文本（带 id、层级、用户备注）。"""
    lines = []

    def walk(nodes, depth):
        for nd in nodes:
            note = f"  [备注:{nd['note']}]" if nd.get("note") else ""
            leaf = "  <叶子,需写正文>" if is_leaf(nd) else ""
            lines.append(f"{'  '*depth}id={nd['_id']} L{depth+1} {nd['title']}{leaf}{note}")
            if not is_leaf(nd):
                walk(nd["children"], depth + 1)

    walk(outline, 0)
    return "\n".join(lines)


def strip_ids(outline):
    for nd in outline:
        nd.pop("_id", None)
        if nd.get("children"):
            strip_ids(nd["children"])


# ---------------- 合并 v4-pro 回填 ----------------
def merge_enrichment(chapters, leaves, enr):
    cmap = {c["_id"]: c for c in chapters}
    lmap = {lf["_id"]: lf for lf in leaves}
    for c in enr.get("chapters", []):
        nd = cmap.get(c.get("id"))
        if nd is not None:
            nd["chapter_score"] = c.get("chapter_score", nd.get("chapter_score", 0))
    for l in enr.get("leaves", []):
        nd = lmap.get(l.get("id"))
        if nd is not None:
            for k in ("brief", "aspects", "min_words", "scoring_points",
                      "must_keywords", "weight", "template", "elements"):
                if k in l:
                    nd[k] = l[k]


def mock_enrichment(chapters, leaves):
    """离线占位：不调模型，给等分技术分与默认权重，便于测试算术与流水线。"""
    enr = {"dictionary": {"metrics": [], "terms": [], "stack": [], "fixed": {}},
           "chapters": [], "leaves": []}
    for c in chapters:
        enr["chapters"].append({"id": c["_id"],
                                "chapter_score": c.get("chapter_score", 10)})
    for lf in leaves:
        enr["leaves"].append({"id": lf["_id"],
                              "brief": lf.get("note") or f"撰写「{lf['title']}」相关内容。",
                              "aspects": [f"{lf['title']}的总体说明",
                                          f"{lf['title']}的具体做法",
                                          f"{lf['title']}的实现效果与保障"],
                              "min_words": 800,
                              "scoring_points": [], "must_keywords": [],
                              "weight": lf.get("weight", 1), "template": None,
                              "elements": {"table": False, "figure": False}})
    return enr


# ---------------- 分批调模型 ----------------
def enrich_batched(client, model, outline, chapters, leaves, scoring, req, pages,
                   batch_size, max_tokens):
    """把叶子分批回填，避免一次调用超 max_tokens 被截断后静默丢数据。
    第一批同时要 chapters；后续批只要 leaves。
    （dictionary 已由 extract_dictionary 独立抽取，这里不再产出，避免抢注意力/token。）"""
    base_ctx = (f"【采购需求】\n{req}\n\n【评分标准】\n{scoring}\n\n"
                f"【投标大纲（id 不可改，结构不可改）】\n{flat_view(outline)}\n\n"
                f"全书目标总页数：{pages} 页。")
    batches = [leaves[i:i + batch_size] for i in range(0, len(leaves), batch_size)]
    enr_all = {"chapters": [], "leaves": []}
    for bi, batch in enumerate(batches, 1):
        ids = "、".join(lf["_id"] for lf in batch)
        if bi == 1:
            ask = (f"本次输出 chapters（全部一级章节）以及 leaves——只含以下 "
                   f"{len(batch)} 个 id，一个都不能漏：{ids}"
                   f"（dictionary 已单独抽取完毕，本次【不要】输出它）")
        else:
            ask = (f"chapters 已在前一批确定，本次【不要】输出它，也不要输出 dictionary。"
                   f"只输出 {{\"leaves\":[...]}}——只含以下 {len(batch)} 个 id，"
                   f"一个都不能漏：{ids}")
        print(f"[plan] 规划批次 {bi}/{len(batches)}（{len(batch)} 个叶子）…", flush=True)
        enr = client.chat_json(
            [{"role": "system", "content": SYSTEM},
             {"role": "user", "content": base_ctx + "\n\n" + ask}],
            temperature=0.4, max_tokens=max_tokens, model=model)
        if bi == 1:
            enr_all["chapters"] = enr.get("chapters", [])
        enr_all["leaves"].extend(enr.get("leaves", []))
    return enr_all


SPLIT_SYSTEM = """你是中国招标投标技术标的规划专家。下面这些大纲叶子的篇幅预算过大，
不适合一次生成。请为每个叶子设计下一级子标题（在该叶子内部细化，这是允许的操作；
除此之外不得改动任何已有结构）。输出 JSON：
{"splits":[{"id":"与输入完全一致的id",
  "children":[{"title":"子标题(4~14字的正式标题短语，不带编号/序号词如'重点一')",
               "brief":"该子节要写什么(具体)",
               "aspects":["该子节应从哪些方面展开1","方面2","方面3"],
               "min_words":800,
               "must_keywords":["从父叶关键词中分配，不得遗漏，也可补充"],
               "weight":1,
               "elements":{"table":false,"figure":false}}]}]}
要求：
- 每个叶子拆 2~5 个子标题，合起来完整覆盖父叶 brief 的内容，不重叠。
- 每个子标题都要给 aspects（本子节应从哪些方面/角度逐一展开，3~8 条具体角度）
  与 min_words（本子节至少多少中文字，正整数，不低于 500）。
- 子标题必须是父叶标题语义范围内的细分：不得越界覆盖大纲中其他章节/兄弟节的内容
  （完整大纲随后给出，仅供定位参照），不得与父叶标题同名，子标题之间不得重名。
- 父叶的每个必含关键词都必须分配到恰好一个子标题的 must_keywords 里。
- weight 为正数，表示子节内容轻重。只输出 JSON，不要解释。"""


def iter_leaves_with_depth(outline):
    out = []

    def walk(nodes, depth):
        for nd in nodes:
            if is_leaf(nd):
                out.append((nd, depth))
            else:
                walk(nd["children"], depth + 1)

    walk(outline, 0)
    return out


_CN_DIGITS = {"零": 0, "一": 1, "二": 2, "三": 3, "四": 4, "五": 5,
              "六": 6, "七": 7, "八": 8, "九": 9, "十": 10}
_CIRCLED = "①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯⑰⑱⑲⑳"


def _cn2int(s):
    """把'一'..'十九'..'二十'等简单中文数字转 int；识别不了返回 0。"""
    if s in _CN_DIGITS:
        return _CN_DIGITS[s]
    if "十" in s:
        left, _, right = s.partition("十")
        tens = _CN_DIGITS.get(left, 1) if left else 1
        ones = _CN_DIGITS.get(right, 0) if right else 0
        return tens * 10 + ones
    return 0


def detect_enum_items(text):
    """在 note 里识别形如（1）…（N）、①②③、一、二、、1、2、的**顺序**枚举，
    返回按序的条目短描述列表；不足 3 项或不成 1..N 连续序列时返回 []。
    只解析'有没有枚举、有几项'，真正的子标题措辞仍交给 SPLIT_SYSTEM。"""
    if not text:
        return []
    seqs = []
    # （1）(1) 全/半角括号数字
    seqs.append([(int(m.group(1)), m.start(), m.end())
                 for m in re.finditer(r"[（(]\s*(\d{1,2})\s*[)）]", text)])
    # ①-⑳
    seqs.append([(_CIRCLED.index(m.group(1)) + 1, m.start(), m.end())
                 for m in re.finditer(r"([①-⑳])", text)])
    # 一、二、（中文数字 + 顿号/逗号）
    seqs.append([(_cn2int(m.group(1)), m.start(), m.end())
                 for m in re.finditer(r"([一二三四五六七八九十]{1,3})\s*[、，]", text)])
    # 1、 / 1. （阿拉伯数字 + 顿号/点，前有句读或行首）
    seqs.append([(int(m.group(1)), m.start(1), m.end())
                 for m in re.finditer(r"(?:^|[；;。：\n])\s*(\d{1,2})\s*[、．.]", text)])
    best = []
    for seq in seqs:
        run = []
        for n, s, e in seq:
            if n == len(run) + 1:
                run.append((n, s, e))
            elif n == 1:
                run = [(1, s, e)]
        if len(run) > len(best):
            best = run
    if len(best) < 3:
        return []
    items = []
    for i, (n, s, e) in enumerate(best):
        end = best[i + 1][1] if i + 1 < len(best) else len(text)
        seg = text[e:end].strip(" ：:，,、；;。\n\t")
        seg = re.split(r"[。；;\n]", seg)[0].strip()
        items.append(seg or f"部分{n}")
    return items


def _own_ref_binds(rf):
    """该节点是否带"自己的"参考绑定（区别于从父章继承）：dict 含 file，或 list 里有含 file 的项。
    exclude=True 不算绑定。带此绑定的叶子不参与拆分，避免拆分剥离 ref 后退化为弱借鉴。"""
    if isinstance(rf, dict):
        return bool(rf.get("file")) and not rf.get("exclude")
    if isinstance(rf, list):
        return any(isinstance(x, dict) and x.get("file") for x in rf)
    return False


def split_big_leaves(plan, client, model, args):
    """word_budget 超过 --split-threshold 的叶子，调 v4-pro 在其内部细化下一级子标题，
    变成多个更小的叶子（各自独立一次生成，从机制上替代脆弱的分块续写）。
    另：note 里明确列出了「（1）…（N）」等 ≥3 项枚举的叶子，无论预算大小都在此固化为
    对应的 N 个子节，避免把结构分解甩给非确定性的写作模型（否则会出现"任务一/任务二"
    重复混乱）。返回 (warnings, 是否发生了拆分)。需在 apply_page_plan 之后、strip_ids 之前调用。"""
    warns, changed = [], False
    thr = args.split
    # 枚举叶子（按 note 识别）无条件纳入候选；超阈值叶子在 thr>0 时纳入
    enum_map = {}
    cands = []
    for nd, d in iter_leaves_with_depth(plan["outline"]):
        # 本叶自己精准绑定了参考文件（dict 单绑定或 list 多绑定）→ 一律不拆分。
        # 拆分会把 ref 留在父节点、子叶不带 ref，生成期子叶只能"继承·弱借鉴"（auto=True），
        # 触发 generate.py 的弱参考分支并被迫按大字数从窄切片扩写 → 与参考相差过大。
        # 整叶保留、交由 generate.py 的强绑定分支照参考写；预算过大时由 generate 的 --chunk 兜底。
        if _own_ref_binds(nd.get("ref")):
            continue
        items = detect_enum_items(nd.get("note") or "")
        is_enum = len(items) >= 3
        is_big = thr > 0 and (nd.get("word_budget", 0) or 0) > thr
        if is_enum:
            enum_map[nd["_id"]] = items
        if is_enum or is_big:
            cands.append((nd, d))
    for nd, d in [(nd, d) for nd, d in cands if d + 2 > 5]:
        why = "note 已列明多部分" if nd["_id"] in enum_map else f"预算超 {thr} 字"
        warns.append(f"叶子「{nd['title']}」{why}但标题已是第5级，无法细化子标题，"
                     f"将回退分块续写。")
    cands = [(nd, d) for nd, d in cands if d + 2 <= 5]
    if not cands:
        return warns, changed
    print(f"[plan] {len(cands)} 个叶子需细化下一级子标题"
          f"（枚举 {sum(1 for nd, _ in cands if nd['_id'] in enum_map)} / "
          f"超预算 {sum(1 for nd, _ in cands if nd['_id'] not in enum_map)}）…", flush=True)

    if args.mock:
        splits = {}
        for nd, _d in cands:
            items = enum_map.get(nd["_id"])
            if items:   # 枚举叶子：按 note 列出的部分逐一造子节，验证结构固化
                kws = nd.get("must_keywords") or []
                splits[nd["_id"]] = [
                    {"title": (it[:14] or f"部分{i+1}"),
                     "brief": f"「{nd['title']}」第{i+1}部分：{it}。",
                     "must_keywords": kws[i::len(items)], "weight": 1}
                    for i, it in enumerate(items)]
                continue
            kws = nd.get("must_keywords") or []
            half = max(1, len(kws) // 2) if kws else 0
            t1, t2 = "设计方案", "实施与保障"
            if nd["title"] in (t1, t2):   # 避免 mock 固定标题撞父叶名，保证可测迭代拆分
                t1, t2 = f"{nd['title']}（上）", f"{nd['title']}（下）"
            splits[nd["_id"]] = [
                {"title": t1, "brief": f"「{nd['title']}」的设计要点。",
                 "must_keywords": kws[:half], "weight": 1},
                {"title": t2, "brief": f"「{nd['title']}」的实施与保障要点。",
                 "must_keywords": kws[half:], "weight": 1},
            ]
    else:
        desc = []
        for nd, _d in cands:
            line = (f"id={nd['_id']} 标题「{nd['title']}」预算约{int(nd.get('word_budget', 0))}字；"
                    f"brief：{nd.get('brief', '') or '—'}；"
                    f"必含关键词：{'、'.join(nd.get('must_keywords') or []) or '—'}")
            items = enum_map.get(nd["_id"])
            if items:
                line += (f"；【该叶 note 已明确列出 {len(items)} 个部分，必须严格拆成对应的"
                         f" {len(items)} 个子标题，不多不少、次序一致】：" +
                         "；".join(f"{i+1}.{it}" for i, it in enumerate(items)))
            desc.append(line)
        ctx = (f"【完整大纲（供定位参照，不可改动）】\n{flat_view(plan['outline'])}\n\n"
               f"需要拆分的叶子：\n" + "\n".join(desc))
        obj = client.chat_json(
            [{"role": "system", "content": SPLIT_SYSTEM},
             {"role": "user", "content": ctx}],
            temperature=0.4, max_tokens=args.max_tokens, model=model)
        splits = {s.get("id"): s.get("children") or [] for s in obj.get("splits", [])}

    for nd, _d in cands:
        ch = [c for c in (splits.get(nd["_id"]) or [])
              if isinstance(c, dict) and (c.get("title") or "").strip()]
        # 枚举叶子按 note 项数放宽上限；普通超预算叶子仍限 2~6
        upper = max(6, len(enum_map[nd["_id"]])) if nd["_id"] in enum_map else 6
        if not (2 <= len(ch) <= upper):
            warns.append(f"叶子「{nd['title']}」未获得有效子标题拆分，保持原样，回退分块续写。")
            continue
        titles = [c["title"].strip() for c in ch]
        if nd["title"] in titles or len(set(titles)) != len(titles):
            warns.append(f"叶子「{nd['title']}」拆分结果标题与父叶同名或互相重名（{'、'.join(titles)}），"
                         f"放弃拆分，回退分块续写。")
            continue
        pw = float(nd.get("weight", 1) or 1)
        csum = sum(float(c.get("weight", 1) or 1) for c in ch) or len(ch)
        kids = [{
            "_id": f"{nd['_id']}.{ci}",   # 新子叶补 id，供后续拆分轮次使用
            "title": c["title"].strip(),
            "brief": c.get("brief", ""),
            "aspects": c.get("aspects", []) or [],
            "min_words": c.get("min_words", 0) or 0,
            "scoring_points": nd.get("scoring_points", []) or [],
            "must_keywords": c.get("must_keywords", []) or [],
            "template": nd.get("template"),
            # 子叶权重按父叶权重等比缩放，保证拆分不改变父叶在章内的页数份额
            "weight": round(pw * float(c.get("weight", 1) or 1) / csum, 3),
            "elements": c.get("elements") or {"table": False, "figure": False},
        } for ci, c in enumerate(ch)]
        # 枚举叶子：其父预算本就不大，把每个子节的 min_words 压到 ≈父预算/份数，
        # 防止 SPLIT_SYSTEM 的"每节≥500字"把一个概述型枚举节撑成好几倍。
        if nd["_id"] in enum_map:
            parent_wb = int(nd.get("word_budget", 0) or 0)
            if parent_wb:
                cap = max(1, parent_wb // len(kids))
                for kid in kids:
                    if kid["min_words"] > cap:
                        kid["min_words"] = cap
        # 关键词不许丢：父叶关键词若未分配到任何子叶，补到最后一个子叶
        union = {k for kid in kids for k in kid["must_keywords"]}
        lost = [kw for kw in (nd.get("must_keywords") or []) if kw and kw not in union]
        if lost:
            kids[-1]["must_keywords"] = list(kids[-1]["must_keywords"]) + lost
        nd["children"] = kids
        for f in ("brief", "aspects", "min_words", "scoring_points", "must_keywords",
                  "template", "weight", "elements", "page_budget", "word_budget"):
            nd.pop(f, None)   # 父节点变非叶子，清掉写作字段
        changed = True
        print(f"  拆分「{nd['title']}」→ {'、'.join(k['title'] for k in kids)}", flush=True)
    return warns, changed


def find_missing(chapters, leaves):
    """规划覆盖率校验：返回 (缺 enrichment 的叶子列表, 缺分数的一级章节列表)。"""
    miss_leaves = [lf for lf in leaves
                   if not lf.get("brief") or lf.get("must_keywords") is None]
    miss_chapters = [c for c in chapters if c.get("chapter_score") in (None, 0)]
    return miss_leaves, miss_chapters


# ---------------- 主流程 ----------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--outline", required=True)
    ap.add_argument("--pages", type=float, required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--scoring", default=None)
    ap.add_argument("--requirements", default=None)
    ap.add_argument("--min-pages", type=float, default=10, dest="min_pages")
    ap.add_argument("--font-size", default=None, choices=["四号", "小四"],
                    help="正文字号（默认小四），用于查每页字数")
    ap.add_argument("--line-spacing", default=None, choices=["固定值22", "1.5倍", "单倍"],
                    help="正文行距（默认1.5倍），用于查每页字数")
    ap.add_argument("--words-per-page", type=int, default=None, dest="wpp",
                    help="直接指定每页字数（覆盖字号/行距查表）")
    ap.add_argument("--model", default=None)
    ap.add_argument("--split-threshold", type=int, default=6000, dest="split",
                    help="叶子字数预算超过该值时调 v4-pro 在其内部细化下一级子标题，"
                         "变成多个小叶子独立生成（0=禁用，超长叶子回退 generate 分块续写）")
    ap.add_argument("--batch", type=int, default=25, help="每次调用回填的叶子数上限")
    ap.add_argument("--max-tokens", type=int, default=20000, dest="max_tokens")
    ap.add_argument("--mock", action="store_true")
    ap.add_argument("--blind-bid", action="store_true", dest="blind_bid",
                    help="暗标：全文不得出现任何可识别投标人的信息（公司名/承揽项目/人名/logo）")
    args = ap.parse_args()

    with open(args.outline, "r", encoding="utf-8") as f:
        src = json.load(f)
    outline = src.get("outline", [])
    meta = src.get("meta", {})
    # 暗标标记落到 plan.meta，供 generate 护栏、check_consistency 查漏、gen_mockups 去标识读取。
    # 命令行 --blind-bid 或 outline.meta.blind_bid 任一为真即暗标。
    meta["blind_bid"] = bool(args.blind_bid or meta.get("blind_bid"))
    chapters, leaves = assign_ids(outline)
    model = args.model or PLAN_MODEL
    client = None

    dict_warns = []
    if args.mock:
        enr = mock_enrichment(chapters, leaves)
        merge_enrichment(chapters, leaves, enr)
        merge_dict = {"metrics": [], "terms": [], "stack": [], "fixed": {}}
    else:
        from deepseek_client import DeepSeekClient
        client = DeepSeekClient(model=model)
        scoring = _read(args.scoring)
        req = _read(args.requirements)
        # —— 数据字典独立抽取（候选甄别 + 覆盖率兜底重试），不再与叶子回填抢注意力/token ——
        merge_dict, _cands, dict_warns = extract_dictionary(
            client, model, scoring, req, args.max_tokens)
        enr = enrich_batched(client, model, outline, chapters, leaves,
                             scoring, req, args.pages, args.batch, args.max_tokens)
        merge_enrichment(chapters, leaves, enr)
        # —— 覆盖率校验 + 一次定向补漏（防止截断/漏答导致叶子静默无 brief）——
        miss_leaves, _ = find_missing(chapters, leaves)
        if miss_leaves:
            print(f"[plan] {len(miss_leaves)} 个叶子未拿到规划，定向补漏一次…", flush=True)
            base_ctx = (f"【采购需求】\n{req}\n\n【评分标准】\n{scoring}\n\n"
                        f"【投标大纲（id 不可改，结构不可改）】\n{flat_view(outline)}\n\n"
                        f"全书目标总页数：{args.pages} 页。")
            for i in range(0, len(miss_leaves), args.batch):
                batch = miss_leaves[i:i + args.batch]
                ids = "、".join(lf["_id"] for lf in batch)
                retry = client.chat_json(
                    [{"role": "system", "content": SYSTEM},
                     {"role": "user", "content": base_ctx +
                      f"\n\n只输出 {{\"leaves\":[...]}}——只含以下 id，一个都不能漏：{ids}"}],
                    temperature=0.4, max_tokens=args.max_tokens, model=model)
                merge_enrichment(chapters, leaves, {"leaves": retry.get("leaves", [])})

    # —— 最终覆盖率报告：静默缺失是最危险的，必须显式打出来 ——
    miss_leaves, miss_chapters = find_missing(chapters, leaves)
    coverage_warns = []
    if miss_leaves:
        names = "、".join(f"[{lf['_id']}]{lf['title']}" for lf in miss_leaves[:10])
        coverage_warns.append(
            f"{len(miss_leaves)}/{len(leaves)} 个叶子仍缺 brief/must_keywords（{names}"
            + ("…" if len(miss_leaves) > 10 else "") + "）——这些叶子写作时无得分点约束，请人工补齐后再生成！")
    if miss_chapters:
        names = "、".join(c["title"] for c in miss_chapters)
        coverage_warns.append(f"一级章节缺技术分（视为0，将只拿兜底页数）：{names}")

    plan = {
        "meta": meta,
        "page_plan": {
            "total_pages": args.pages,
            "min_pages_per_chapter": args.min_pages,
            "words_per_page": words_per_page(args.font_size, args.line_spacing, args.wpp),
            "body_style": (f"每页{args.wpp}字(手动指定)" if args.wpp else
                           f"宋体{args.font_size or '小四'}·{args.line_spacing or '1.5倍'}行距"),
        },
        "dictionary": merge_dict,
        "templates": src.get("templates", {}),
        "outline": outline,
    }
    warns = apply_page_plan(plan)

    # —— 大叶子拆分：预算超阈值的叶子细化下一级子标题，再重算页数/字数。
    # 迭代进行：拆出的子叶若仍超阈值继续拆（最多3轮，第5级深度限制兜底）——
    split_warns = []
    for _round in range(3):
        s_warns, changed = split_big_leaves(plan, client, model, args)
        split_warns += s_warns
        if not changed:
            break
        warns = apply_page_plan(plan)
    warns = warns + split_warns

    strip_ids(outline)

    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(plan, f, ensure_ascii=False, indent=2)

    for w in dict_warns + coverage_warns + warns:
        print("[警告]", w)
    print(plan_summary(plan))
    print(f"\n已生成规划：{args.out}")
    print("请审核（尤其数据字典与各章页数），冻结后再：")
    print(f"  python scripts/generate.py {args.out} content.json")
    return 0


def _read(path):
    if not path:
        return "（未提供）"
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


if __name__ == "__main__":
    sys.exit(main())
