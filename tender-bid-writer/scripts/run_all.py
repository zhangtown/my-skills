#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
run_all.py — 一键编排整条标书流水线

  outline.json → [plan] → (人工闸口①: 审核 plan.json) → [generate]
  → [check_consistency] (人工闸口②: 有问题则修复重检) → [界面图: gen+render]
  → [build_docx] → 提示 PDF 抽查

用法：
  python scripts/run_all.py --outline outline.json --pages 80 \
      --scoring scoring.txt --requirements req.txt \
      --font-size 小四 --line-spacing 1.5倍 --docx 投标文件.docx
  可选：--workdir 输出目录(默认当前目录)  --mock 全程离线试跑
        --yes 跳过人工闸口(不建议正式使用)  --no-mockups 跳过界面图
        --split-threshold/--chunk 透传对应脚本

大纲转写请先单独完成并校验（outline_from_docx.py --check），本脚本从 outline.json 起步。
中断后直接重跑同一命令：generate 有断点续跑，plan/图/文档已存在的产物用 --fresh 语义
由各脚本自行处理（plan 会重算覆盖，界面图默认跳过已有 html/png）。
"""

import sys
import os
import argparse
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))


def run(script, *args, cwd=None):
    cmd = [sys.executable, os.path.join(HERE, script), *[str(a) for a in args]]
    print(f"\n===== 执行：{script} {' '.join(str(a) for a in args)} =====", flush=True)
    return subprocess.run(cmd, cwd=cwd).returncode


def gate(msg, auto):
    if auto:
        print(f"[闸口] {msg} —— --yes 已跳过")
        return "c"
    while True:
        ans = input(f"\n[闸口] {msg}\n  回车=继续  q=退出  > ").strip().lower()
        if ans in ("", "c", "y"):
            return "c"
        if ans == "q":
            return "q"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--outline", required=True)
    ap.add_argument("--pages", type=float, required=True)
    ap.add_argument("--docx", default="投标文件.docx")
    ap.add_argument("--scoring", default=None)
    ap.add_argument("--requirements", default=None)
    ap.add_argument("--font-size", default=None, dest="font_size")
    ap.add_argument("--line-spacing", default=None, dest="line_spacing")
    ap.add_argument("--words-per-page", type=int, default=None, dest="wpp")
    ap.add_argument("--min-pages", type=float, default=None, dest="min_pages")
    ap.add_argument("--split-threshold", type=int, default=None, dest="split")
    ap.add_argument("--chunk", type=int, default=None)
    ap.add_argument("--workdir", default=".")
    ap.add_argument("--format-config", default=None, dest="format_config",
                    help="排版配置 JSON 路径；不指定则 build_docx 自动在大纲同目录/脚本同目录查找 format_config.json")
    ap.add_argument("--mock", action="store_true")
    ap.add_argument("--yes", action="store_true", help="跳过人工闸口")
    ap.add_argument("--no-mockups", action="store_true", dest="no_mockups")
    ap.add_argument("--references", default=None,
                    help="参考资料文件（逗号分隔，md/规范docx优先，pdf降级需确认）；"
                         "提供则在规划前进入交互绑定，未提供则完全不启用参考资料")
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--blind-bid", action="store_true", dest="blind_bid",
                   help="暗标：全文不得出现任何可识别投标人身份的信息")
    g.add_argument("--open-bid", action="store_true", dest="open_bid",
                   help="明标（默认）：允许出现投标人信息")
    args = ap.parse_args()

    # ⓪-0 明标/暗标：编写前必须明确。命令行未指定且非 --yes 时交互询问。
    blind = args.blind_bid
    if not args.blind_bid and not args.open_bid and not args.yes:
        while True:
            ans = input("\n[必答] 本次编写的是明标还是暗标？"
                        "\n  1=明标（默认，可出现投标人信息）"
                        "\n  2=暗标（全文不得出现公司/项目/人名/logo 等可识别投标人的信息）"
                        "\n  > ").strip()
            if ans in ("", "1", "明标"):
                blind = False
                break
            if ans in ("2", "暗标"):
                blind = True
                break
    if blind:
        print("[run_all] 已按【暗标】编写：全程强制匿名，成稿会做暗标查漏。")

    outline = os.path.abspath(args.outline)
    # 产物目录：未显式指定 --workdir 时，默认落在投标大纲所在目录，
    # 使 plan/content/docx/界面图都与大纲同处一处；显式给了 --workdir 才以其为准。
    wd = os.path.dirname(outline) if args.workdir == "." else os.path.abspath(args.workdir)
    os.makedirs(wd, exist_ok=True)
    plan_p = os.path.join(wd, "plan.json")
    content_p = os.path.join(wd, "content.json")
    mock = ["--mock"] if args.mock else []

    # ⓪ 参考资料绑定（可选）：提供 --references 才启用；把绑定写回 outline.bound.json 供规划使用。
    #    未提供时 outline 原样进入规划，参考资料功能完全不介入（零回归）。
    if args.references:
        bound = os.path.join(wd, "outline.bound.json")
        bind_args = ["bind", "--outline", outline, "--refs", args.references, "--out", bound]
        if args.yes:
            bind_args.append("--yes")   # --yes 只解析预览、不交互绑定
        if run("references.py", *bind_args, cwd=wd):
            sys.exit("[run_all] 参考资料绑定失败，中止。")
        if not args.yes and gate(f"请确认 {bound} 的参考资料绑定（章节→参考节、排除项），"
                                 f"确认后进入规划。", args.yes) == "q":
            sys.exit(0)
        outline = bound   # 后续规划以带 ref 的大纲为准

    # ① 规划
    pa = ["--outline", outline, "--pages", args.pages, "--out", plan_p]
    for flag, val in (("--scoring", args.scoring), ("--requirements", args.requirements),
                      ("--font-size", args.font_size), ("--line-spacing", args.line_spacing),
                      ("--words-per-page", args.wpp), ("--min-pages", args.min_pages),
                      ("--split-threshold", args.split)):
        if val is not None:
            pa += [flag, val]
    if blind:
        pa.append("--blind-bid")   # 暗标标记落到 plan.meta，贯穿生成/查漏/界面图
    if run("plan.py", *pa, *mock, cwd=wd):
        sys.exit("[run_all] plan 失败，中止。")
    if gate(f"请审核 {plan_p}（数据字典、各章页数、拆分结果），确认冻结后继续。",
            args.yes) == "q":
        sys.exit(0)

    # ② 逐叶生成（自带断点续跑）
    ga = [plan_p, content_p] + (["--chunk", args.chunk] if args.chunk else [])
    if run("generate.py", *ga, *mock, cwd=wd):
        sys.exit("[run_all] generate 失败，中止（重跑本命令可断点续上）。")

    # ③ 一致性检查（有问题→修复→重检循环）
    while True:
        rc = run("check_consistency.py", content_p, plan_p, cwd=wd)
        if rc == 0:
            break
        if args.yes:
            print("[run_all] 一致性检查未通过（--yes 模式仍继续，请事后处理）。")
            break
        ans = input("\n[闸口] 一致性检查未通过。修复 content.json 后：回车=重检  "
                    "s=带问题继续  q=退出  > ").strip().lower()
        if ans == "s":
            break
        if ans == "q":
            sys.exit(0)

    # ③b 参考资料审查闸口（仅当启用了参考资料时）：
    #     一致性检查里的“参考资料审查报告”只发 warning（不阻断 rc），
    #     所以此处显式停一次，强制人工过一遍用到参考资料的章节与疑似指标告警。
    if args.references and not args.yes:
        if gate("上面若打印了『参考资料审查报告』，请逐条核对：用了参考资料的章节是否贴题、"
                "有无疑似越权指标数值需回改数据字典。确认后进入出稿。", args.yes) == "q":
            sys.exit(0)

    # ④ 界面效果图（无匹配图题时自动无事可做）
    if not args.no_mockups:
        mdir = os.path.join(wd, "mockups")
        if run("gen_mockups.py", content_p, plan_p, "--dir", mdir, *mock, cwd=wd):
            print("[run_all] 部分界面稿生成失败（详见 .raw.txt），可修复后单独重跑，"
                  "先继续主流程。")
        if os.path.isdir(mdir) and any(f.endswith(".html") for f in os.listdir(mdir)):
            if not args.mock and run("render_mockups.py", mdir, "--attach", content_p, cwd=wd):
                print("[run_all] 部分截图失败，对应图保持占位框。")

    # ⑤ 排版出稿（排版参数来自 format_config.json；--format-config 显式指定优先，
    #    否则 build_docx 自动在大纲同目录/脚本同目录查找）
    docx_p = os.path.join(wd, args.docx)
    ba = [content_p, docx_p]
    if args.format_config:
        ba += ["--format-config", os.path.abspath(args.format_config)]
    if run("build_docx.py", *ba, cwd=wd):
        sys.exit("[run_all] build_docx 失败，中止。")

    print(f"\n===== 完成：{docx_p} =====")
    print("务必执行阶段四验证：转 PDF 抽查排版；Word 打开后 Ctrl+A → F9 更新目录页码。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
