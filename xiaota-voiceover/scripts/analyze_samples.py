# -*- coding: utf-8 -*-
"""量化分析小踏口播案例，提取句长/段长/用词分布。

用途：给 SKILL.md 里的"节奏指标"提供可复现的依据，也用于回归
（以后新增案例时重新跑一遍，看风格指标有没有漂移）。

用法：
    python analyze_samples.py <案例文件或目录> [...]
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

SENT_SPLIT = re.compile(r"[。！？!?]+")
# SRT 时间码与序号行
SRT_TIME = re.compile(r"^\d{2}:\d{2}:\d{2}[,.]\d{2,3}\s*-->")
SRT_INDEX = re.compile(r"^\d+$")
# 段落/行数对 SRT 无意义（一行一句），报告时标注
SRT_MARK = "[SRT 逐行稿]"

# 小踏的标志性语言签名，用于统计密度
SIGNATURES = {
    "身份句": r"我是小踏",
    "收尾公式": r"这期视频就聊到",
    "互动话术": r"一键三连",
    "关注话术": r"点点?关注|喜欢的老铁|喜欢的朋友",
    "反问句": r"[吗呢吧？]$|[？]",
    "至于吗公式": r"至于",
    "你品": r"你品|你猜|你想想|你注意到没有",
    "看一张/先看": r"先给大家看|再来看|看一张",
    "有人说": r"有人说|有人说就",
    "咱们": r"咱们",
    "各位/老铁": r"各位|老铁",
    "不是A是B": r"这不是.*这是|不是.*而是",
    "反过来想": r"反过来想|反过来",
    "答案就/问题在": r"问题在|答案就|答案是什么",
}


def strip_srt(text: str) -> str:
    out = []
    for line in text.splitlines():
        s = line.strip()
        if not s or SRT_TIME.match(s) or SRT_INDEX.match(s):
            continue
        if s.startswith("WEBVTT"):
            continue
        out.append(s)
    return "\n".join(out)


def paragraphs(text: str) -> list[str]:
    return [p for p in (l.strip() for l in text.splitlines()) if p]


def sentences(text: str) -> list[str]:
    """按中文句末标点切句；口播稿大量以空行断句，逗号也常作停顿，故分开统计。"""
    parts = []
    for p in paragraphs(text):
        for s in SENT_SPLIT.split(p):
            s = re.sub(r'[“”"\'’‘]', "", s).strip()
            if s:
                parts.append(s)
    return parts


def clauses(text: str) -> list[str]:
    """更细的停顿单位：连逗号、顿号也切，对应口播换气点。"""
    parts = []
    for p in paragraphs(text):
        for s in re.split(r"[。！？!?，,、；;：:]+", p):
            s = re.sub(r'[“”"\'’‘]', "", s).strip()
            if s:
                parts.append(s)
    return parts


def srt_duration(text: str) -> float | None:
    """SRT 首尾时间码之差（秒），用于校准真实语速。"""
    stamps = []
    for m in re.finditer(r"(\d{2}):(\d{2}):(\d{2})[,.](\d{2,3})", text):
        h, mi, s, ms = (int(x) for x in m.groups())
        stamps.append(h * 3600 + mi * 60 + s + ms / (1000 if len(m.group(4)) == 3 else 100))
    return (max(stamps) - min(stamps)) if len(stamps) >= 2 else None


def stats(path: Path) -> dict:
    raw = path.read_text(encoding="utf-8")
    is_srt = re.search(r"^\d{2}:\d{2}:\d{2}[,.]\d{2,3}\s*-->", raw, re.M) is not None
    text = strip_srt(raw) if is_srt else raw
    sents, cls, paras = sentences(text), clauses(text), paragraphs(text)
    total_chars = len(re.sub(r"\s", "", text))
    hanzi = len(re.findall(r"[\u4e00-\u9fff]", text))
    out = {
        "file": path.name,
        "稿型": "SRT 逐行稿" if is_srt else "文字稿",
        "总字数(去空白)": total_chars,
        "汉字数": hanzi,
        "句数": len(sents),
        "平均句长": round(sum(len(s) for s in sents) / max(len(sents), 1), 1),
        "平均停顿单位长": round(sum(len(c) for c in cls) / max(len(cls), 1), 1),
        "最长句": max((len(s) for s in sents), default=0),
        "短句占比(≤10字)": f"{sum(1 for s in sents if len(s) <= 10) / max(len(sents), 1):.0%}",
    }
    dur = srt_duration(raw) if is_srt else None
    if dur:
        out["真实时长(分:秒)"] = "%d:%02d" % divmod(round(dur), 60)
        out["真实语速(字/分)"] = round(total_chars / (dur / 60))
    else:
        out["预估时长(分:秒, 330字/分)"] = "%d:%02d" % divmod(round(total_chars / 330 * 60), 60)
    out["签名命中"] = {k: len(re.findall(v, text)) for k, v in SIGNATURES.items()
                       if re.search(v, text)}
    return out


def main() -> int:
    targets: list[Path] = []
    for arg in sys.argv[1:]:
        p = Path(arg)
        targets.extend(sorted(p.glob("*.txt")) if p.is_dir() else [p])
    if not targets:
        print(__doc__)
        return 1
    for p in targets:
        s = stats(p)
        print(f"\n=== {s['file']} ===")
        for k, v in s.items():
            if k != "file":
                print(f"  {k}: {v}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
