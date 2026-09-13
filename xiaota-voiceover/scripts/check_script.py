# -*- coding: utf-8 -*-
"""口播稿机械自检。

它检查的都是"听起来像不像小踏"里可以量化的部分：字数/时长、句长节奏、
书面语嫌疑词、长行。指标不合格不等于稿子差，但值得回头看一眼。

用法：
    python check_script.py <稿子文件> [--speed 323] [--target-minutes 3]
    python check_script.py --text "直接传一段文字"
"""
from __future__ import annotations

import argparse
import re
import sys

DEFAULT_SPEED = 323  # 字/分，来自案例2真实SRT（1172字 / 3分38秒）

# 书面语 / AI腔 / 中立化嫌疑词（命中即提示，不是硬错误）
SUSPECT_WORDS = [
    "该事件", "反映出", "折射出", "值得深思", "据悉", "相关人士", "对此",
    "与此同时", "综上所述", "不可否认", "毋庸置疑", "从某种意义上说",
    "具有重要的现实意义", "值得注意的是", "不仅仅是", "在当今社会",
    "随着", "让我们一起", "总而言之", "首先", "其次", "最后",
    "各方看法不一", "理性看待", "有待进一步调查", "看法不一",
    "绝绝子", "yyds", "破防了", "蚌埠住了", "家人们谁懂",
    "必须严惩", "天理难容", "触目惊心", "令人发指", "骇人听闻",
]

# 小踏的语言签名
SIGNATURES = {
    "身份句": r"我是小踏",
    "收尾公式": r"这期视频就聊到",
    "互动话术": r"一键三连",
    "关注话术": r"点点?关注|喜欢的老铁|喜欢的朋友",
    "你品/你猜/你想想": r"你品|你猜|你想想|你注意到没有",
    "先看一张": r"先给大家看|再来看一张|看一张",
    "自我应答(可选)": r"至于吗|至于。",
    "借他人之口": r"有位网友|有个网友|有位父亲|网友说",
    "咱们": r"咱们",
    "据说/有人说": r"有人说|有人说就",
}


def srt_text(raw: str) -> str:
    """若是 SRT，去掉序号与时间码。"""
    out = []
    for line in raw.splitlines():
        s = line.strip()
        if not s or re.match(r"^\d+$", s) or re.match(r"^\d{2}:\d{2}:\d{2}[,.]\d{2,3}\s*-->", s):
            continue
        out.append(s)
    return "\n".join(out)


def split_units(text: str) -> list[str]:
    """切出"一句"级别的单位。

    口播稿一行一句，而 SRT 稿往往整行没有标点——所以先按行，再按句末标点切，
    两边的信息都不丢。没有标点的行本身就是一句（这正是断行的用意）。
    """
    units: list[str] = []
    for line in text.splitlines():
        line = re.sub(r'[“”"\'’‘]', "", line).strip()
        if not line:
            continue
        parts = [p.strip() for p in re.split(r"[。！？!?]+", line)]
        units.extend([p for p in parts if p])
    return units


def analyze(text: str, speed: float, target_min: float, is_srt: bool) -> tuple[list[str], list[str]]:
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    body = re.sub(r"\s", "", text)
    chars = len(body)
    minutes = chars / speed

    sentences = split_units(text)
    q_count = text.count("？") + text.count("?")

    problems: list[str] = []
    notes: list[str] = []

    if is_srt:
        notes.append("输入是 SRT 稿：字幕通常不带标点，所以句长/问句密度这两项在这里不可靠，"
                     "请对照你在剪辑时用的文字稿判断")

    # --- 时长 ---
    lo, hi = int(speed * target_min * 0.9), int(speed * target_min * 1.2)
    dur = f"{int(minutes)}分{round((minutes % 1) * 60):02d}秒"
    line = f"字数 {chars} 字 ｜ 预估时长 {dur}（{speed:.0f}字/分）"
    if chars < lo:
        problems.append(f"{line} —— 偏短，目标 {target_min} 分钟需要 {lo}–{hi} 字；加事实，不要加形容词")
    elif chars > hi:
        problems.append(f"{line} —— 偏长，目标 {target_min} 分钟建议 {lo}–{hi} 字；口播念起来总比看起来长")
    else:
        notes.append(f"{line} —— 时长合适")

    # --- 节奏 ---
    if sentences and not is_srt:
        avg = sum(len(s) for s in sentences) / len(sentences)
        shortest = sum(1 for s in sentences if len(s) <= 10) / len(sentences)
        longest = max(len(s) for s in sentences)
        notes.append(
            f"平均句长 {avg:.1f} 字（案例 9.2–14.3）｜ 短句占比 {shortest:.0%}（目标≥40%）｜ 最长句 {longest} 字（≤33）"
        )
        if avg > 16:
            problems.append(f"平均句长 {avg:.1f} 字偏长 —— 把长句拆成短句，口播节奏靠短句撑")
        if shortest < 0.35:
            problems.append(f"短句占比仅 {shortest:.0%} —— 多加 10 字以内的短句，尤其是转折和结论处")

    # --- 长行 ---
    long_lines = [(i, l) for i, l in enumerate(lines, 1) if len(l) > 34]
    if long_lines:
        problems.append(f"有 {len(long_lines)} 行超过 34 字，建议断行：")
        for i, l in long_lines[:8]:
            problems.append(f"    第{i}行（{len(l)}字）：{l[:40]}{'…' if len(l) > 40 else ''}")

    # --- 问句密度 ---
    if not is_srt:
        if q_count < 8:
            problems.append(f"问句只有 {q_count} 处 —— 案例是 13–15 处；少了解说感会变平")
        else:
            notes.append(f"问句 {q_count} 处 —— 密度够")

    # --- 书面语嫌疑 ---
    hits = [w for w in SUSPECT_WORDS if w in text]
    if hits:
        problems.append("书面语/AI腔嫌疑词：" + "、".join(hits) + " —— 换成你会说出口的说法")

    # --- 签名 ---
    found = {k: len(re.findall(v, text)) for k, v in SIGNATURES.items() if re.search(v, text)}
    missing_core = [k for k in ("身份句", "收尾公式", "互动话术") if k not in found]
    if missing_core:
        problems.append("缺少固定部件：" + "、".join(missing_core)
                        + "（这三样是每期都有的，别漏）")
    if found:
        notes.append("命中签名：" + "、".join(f"{k}×{v}" for k, v in found.items()))

    # --- 硬事实密度 ---
    # 只数得出"数字 + 书名号/引号引用"，认不出人名和机构名（那需要实体识别，
    # 不该由这个脚本硬猜）。所以只作为提醒，不当问题报，免得误导。
    hard = len(re.findall(r"\d+|[《「\"“][^》」\"”]{2,}[》」\"”]", text))
    if chars:
        notes.append(f"数字/书名号引用共 {hard} 处（{hard / chars * 100:.1f} 每百字）"
                     "—— 这个只能粗看，人名机构名不在统计内，硬事实是否够还得自己数一遍")

    return problems, notes


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("path", nargs="?", help="稿子文件路径")
    ap.add_argument("--text", help="直接传文字")
    ap.add_argument("--speed", type=float, default=DEFAULT_SPEED, help="语速 字/分")
    ap.add_argument("--target-minutes", type=float, default=3.0)
    a = ap.parse_args()

    if a.text is not None:
        raw = a.text
    elif a.path:
        raw = open(a.path, encoding="utf-8").read()
    else:
        ap.print_help()
        return 1

    is_srt = re.search(r"^\d{2}:\d{2}:\d{2}[,.]\d{2,3}\s*-->", raw, re.M) is not None
    text = srt_text(raw) if is_srt else raw
    problems, notes = analyze(text, a.speed, a.target_minutes, is_srt)

    print("=== 小踏口播自检 ===\n")
    for n in notes:
        print(f"  [ok]   {n}")
    if problems:
        print()
        for p in problems:
            print(f"  [改]   {p}")
        print(f"\n共 {len(problems)} 处建议修改。")
    else:
        print("\n没有发现问题。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
