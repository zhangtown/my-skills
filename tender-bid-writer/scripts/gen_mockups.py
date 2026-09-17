#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gen_mockups.py — 调 DeepSeek 为界面类 figure 批量生成静态 HTML 界面稿

流水线位置：generate.py 产出 content.json（含 figure 占位）之后：
  python scripts/gen_mockups.py content.json plan.json --dir mockups
  python scripts/render_mockups.py mockups/ --attach content.json   # 截图+回填

做法：扫描 content.json 里图题匹配 --pattern（默认"界面"）的 figure，
为每个 figure 收集业务上下文（标题路径、同章模块名做侧栏菜单、前文段落、
数据字典业务词），调 DeepSeek 生成单文件 HTML，存 mockups/<图题>.html
（文件名=图题，与 render_mockups.py 的回填约定一致）。

模型：默认 DEEPSEEK_MOCKUP_MODEL 或 deepseek-v4-flash，--model 覆盖。
"""

import sys
import os
import re
import json
import argparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from render_mockups import sanitize  # noqa: E402  文件名约定唯一来源

MOCKUP_MODEL = os.environ.get("DEEPSEEK_MOCKUP_MODEL", "deepseek-v4-flash")

SYSTEM = """你是政企信息系统的资深前端，为投标文件绘制高保真界面效果图。
输出一个**单文件静态 HTML**（截图用，非交互），要求：
- 画布 1440×900：body{margin:0;width:1440px;height:900px;overflow:hidden}，内容撑满无滚动条。
- 政企后台骨架：顶栏(左侧系统全称、右侧当前用户/退出) + 左侧深色菜单(190px，给出的同级
  模块名做菜单项，当前页高亮) + 面包屑 + 内容区(筛选栏/工具栏 + 主体)。
- 主体按界面用途设计：列表页出全框线表格(表头灰底，6~8行真实可信的中文示例数据，
  状态列用彩色小标签)；表单页出分组表单；地图/大屏类用 CSS 色块+图例示意。
- 所有文字用给定项目的真实业务词，严禁 Lorem/英文假词/emoji 图标（图标用 CSS 画或省略）。
- 视觉仿 Element Plus：主色 #1868d3，页面底 #f5f7fa，白色卡片，1px #e4e7ed 边框，
  4px 小圆角，字体 "Microsoft YaHei"。忌紫色渐变、过度居中、大圆角、花哨阴影。
- 全部样式写在 <style> 内，**不引用任何外部资源**（离线截图）。
- 只输出 HTML 源码，从 <!DOCTYPE html> 开始，不要解释、不要 markdown 围栏。"""

FENCE_RE = re.compile(r"```(?:html)?\s*(.*?)```", re.S)


def extract_html(text):
    m = FENCE_RE.search(text)
    if m:
        text = m.group(1)
    s = text.find("<!DOCTYPE")
    if s == -1:
        s = text.find("<html")
    e = text.rfind("</html>")
    if s != -1 and e != -1:
        return text[s:e + len("</html>")].strip()
    return None


def salvage_html(text):
    """输出被截断（有开头无 </html>）时的抢救：截断多发生在正文尾部，
    补上收尾标签后通常仍可正常截图。"""
    body = text.split("```")[-1] if text.count("```") == 1 else text  # 去未闭合围栏
    s = body.find("<!DOCTYPE")
    if s == -1:
        s = body.find("<html")
    if s == -1:
        return None
    return body[s:].strip() + "\n</body></html>"


def collect_figures(content, pattern):
    """遍历 body，为每个匹配的 figure 收集上下文：
    (figure, 章标题, 标题路径, 同章 h2/h3 列表, 前文段落)。"""
    body = content.get("body", [])
    out = []
    hpath = {}           # level -> title
    chapter = None
    chapter_subs = {}    # 章标题 -> [h2/h3 标题]
    # 先收集每章的子标题（做侧栏菜单）
    cur = None
    for b in body:
        t = b.get("type", "")
        if t == "h1":
            cur = b.get("text", "")
            chapter_subs[cur] = []
        elif t in ("h2", "h3") and cur:
            chapter_subs[cur].append(b.get("text", ""))
    recent_p = []
    for b in body:
        t = b.get("type", "")
        if re.fullmatch(r"h[1-5]", t):
            lvl = int(t[1])
            hpath[lvl] = b.get("text", "")
            for k in [k for k in hpath if k > lvl]:
                hpath.pop(k)
            if lvl == 1:
                chapter = b.get("text", "")
            recent_p = []
        elif t == "p":
            recent_p.append(b.get("text", ""))
        elif t == "figure":
            title = (b.get("title") or "").strip()
            if title and re.search(pattern, title):
                path = " > ".join(hpath[k] for k in sorted(hpath))
                out.append((b, chapter or "", path,
                            (chapter_subs.get(chapter) or [])[:10],
                            "".join(recent_p)[-400:]))
    return out


def build_user_prompt(meta, dictionary, fig_title, chapter, path, subs, context):
    sysname = meta.get("project_name", "业务系统")
    terms = "、".join(t.get("canonical", "") for t in (dictionary.get("terms") or [])[:15]
                     if t.get("canonical"))
    blind = ("\n【暗标·必守】界面中严禁出现投标人任何标识：不得放公司 logo/图标标志、"
             "不得写公司/单位名称与承揽项目名；顶栏左侧只写本系统名称（不带单位前缀），"
             "右侧当前用户用「管理员」等通用角色而非真实人名；页脚/水印不得含任何单位信息。"
             if meta.get("blind_bid") else "")
    return (f"项目/系统名称：{sysname}\n"
            f"要绘制的界面：{fig_title}\n"
            f"所在章节路径：{path}\n"
            f"侧栏菜单项（本章相邻模块，当前界面对应项高亮）：{'、'.join(subs) or '按界面名自拟4~6项'}\n"
            f"统一业务术语：{terms or '—'}\n"
            f"该图前文（界面功能的正文描述，字段/流程从中提取）：\n{context or '—'}{blind}\n\n"
            f"请生成这个界面的高保真效果图 HTML。")


MOCK_HTML = """<!DOCTYPE html><html><head><meta charset="utf-8"><style>
body{{margin:0;width:1440px;height:900px;font-family:"Microsoft YaHei";background:#f5f7fa}}
.top{{background:#1868d3;color:#fff;padding:14px 24px;font-size:16px}}</style></head>
<body><div class="top">{sys} — {title}（mock）</div></body></html>"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("content", help="content.json（generate.py 产物）")
    ap.add_argument("plan", help="plan.json（取 meta/dictionary）")
    ap.add_argument("--dir", default="mockups", help="界面稿输出目录")
    ap.add_argument("--pattern", default="界面", help="图题匹配正则（默认：界面）")
    ap.add_argument("--model", default=None)
    ap.add_argument("--max-tokens", type=int, default=16000, dest="max_tokens")
    ap.add_argument("--force", action="store_true", help="已存在同名 html 也重新生成")
    ap.add_argument("--mock", action="store_true", help="不调 API，生成占位 html 测流水线")
    args = ap.parse_args()

    with open(args.content, "r", encoding="utf-8") as f:
        content = json.load(f)
    with open(args.plan, "r", encoding="utf-8") as f:
        plan = json.load(f)
    meta = plan.get("meta", {}) or content.get("meta", {})
    dictionary = plan.get("dictionary", {}) or {}

    figs = collect_figures(content, args.pattern)
    if not figs:
        print(f"[gen] content.json 中没有图题匹配 /{args.pattern}/ 的 figure，无事可做。")
        return 0
    os.makedirs(args.dir, exist_ok=True)
    model = args.model or MOCKUP_MODEL
    client = None
    if not args.mock:
        from deepseek_client import DeepSeekClient
        client = DeepSeekClient(model=model)

    ok = skip = fail = 0
    for i, (fig, chapter, path, subs, ctx) in enumerate(figs, 1):
        title = fig["title"].strip()
        dst = os.path.join(args.dir, sanitize(title) + ".html")
        if os.path.isfile(dst) and not args.force:
            skip += 1
            print(f"[{i}/{len(figs)}] 跳过（已存在）：{title}")
            continue
        if args.mock:
            html = MOCK_HTML.format(sys=meta.get("project_name", "系统"), title=title)
        else:
            print(f"[{i}/{len(figs)}] 生成：{title} …", flush=True)
            html, raw = None, None
            for attempt in (1, 2):
                raw = client.chat(
                    [{"role": "system", "content": SYSTEM},
                     {"role": "user", "content": build_user_prompt(
                         meta, dictionary, title, chapter, path, subs, ctx)}],
                    temperature=0.5, max_tokens=args.max_tokens, model=model)
                html = extract_html(raw)
                if html:
                    break
                print(f"    未找到完整 HTML（返回 {len(raw)} 字符），重试（{attempt}/2）…",
                      flush=True)
            if not html and raw:
                html = salvage_html(raw)
                if html:
                    print("    [警告] 输出疑似被截断，已补全收尾标签抢救，请检查该图。")
            if not html:
                fail += 1
                dbg = os.path.join(args.dir, sanitize(title) + ".raw.txt")
                with open(dbg, "w", encoding="utf-8") as f:
                    f.write(raw or "")
                print(f"    [失败] {title}：未得到 HTML，原始输出已存 {dbg} 供诊断。")
                continue
        with open(dst, "w", encoding="utf-8") as f:
            f.write(html)
        ok += 1
        print(f"    → {dst}")

    print(f"\n[gen] 完成：生成 {ok}，跳过 {skip}，失败 {fail}（共匹配 {len(figs)} 张）")
    if ok:
        print(f"下一步截图并回填：\n  python scripts/render_mockups.py {args.dir} "
              f"--attach {args.content}")
    return 1 if fail else 0


if __name__ == "__main__":
    sys.exit(main())
