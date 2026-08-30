#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""批注一致性校验：docx 中每条批注 vs indicators.json 的指标原文（逐字，含XML反转义）。
用法: python verify_comments.py <工作目录> <输出.docx>
约定: 批注格式为 "【招标参数】<num> <tender>"；设备指标按数据顺序、服务指标按 build.js 中
      svc_order 指定的章节顺序插入。svc_order 需按实际 build.js 的章节顺序在下方配置。
"""
import sys, os, re, json, zipfile, html

SVC_ORDER_SPEC = [
    ("服务周期与商务要求", "服务周期"), ("服务周期与商务要求", "团队配置"),
    ("服务周期与商务要求", "保密要求"), ("服务周期与商务要求", "响应要求"),
    ("漏洞扫描服务", "服务目标"), ("漏洞扫描服务", "扫描范围"),
    ("渗透测试服务", "服务目标"), ("渗透测试服务", "服务内容"), ("渗透测试服务", "服务频率"),
    ("暴露面梳理服务", "服务目标"), ("暴露面梳理服务", "服务内容"),
    ("暴露面梳理服务", "服务频次"), ("暴露面梳理服务", "输出文档"),
    ("重保值守服务", "服务目标"), ("重保值守服务", "服务内容"),
    ("重保值守服务", "服务人天"), ("重保值守服务", "输出文档"),
    ("专项服务", "网络安全应急演练"),
]

def main():
    if len(sys.argv) < 3:
        sys.exit("用法: python verify_comments.py <工作目录> <输出.docx>")
    base, docx_path = sys.argv[1], sys.argv[2]
    with open(os.path.join(base, "data", "indicators.json"), encoding="utf-8") as fp:
        data = json.load(fp)

    def find(c1, c2):
        for d in data.get("SVC", []):
            if d.get("c1") == c1 and d.get("c2") == c2:
                return d
        return None

    svc_order = [find(c1, c2) for c1, c2 in SVC_ORDER_SPEC]
    expected = []
    for d in list(data.get("DEV", [])) + [x for x in svc_order if x]:
        expected.append(("【招标参数】" + d["num"] + " " + d["tender"]).replace("\n", "").strip())

    z = zipfile.ZipFile(docx_path)
    com = z.read("word/comments.xml").decode("utf-8")
    comments = re.findall(r'<w:comment [^>]*w:id="(\d+)"[^>]*>(.*?)</w:comment>', com, re.S)
    comments.sort(key=lambda x: int(x[0]))

    def clean(s):
        s = re.sub(r"<[^>]+>", "", s)
        s = html.unescape(s)
        return re.sub(r"\s+", "", s).strip()

    ok = 0
    errs = []
    for (cid, body), exp in zip(comments, expected):
        if clean(body) == re.sub(r"\s+", "", exp):
            ok += 1
        else:
            errs.append((cid, clean(body)[:70], re.sub(r"\s+", "", exp)[:70]))
    print(f"批注一致性: {ok}/{len(comments)}")
    if errs:
        print("不匹配:")
        for e in errs[:10]:
            print("  id", e[0], "\n   got:", e[1], "\n   exp:", e[2])
    # 附带检查：批注范围数/图片数/图注SEQ
    doc = z.read("word/document.xml").decode("utf-8")
    print(f"批注范围: {doc.count('commentRangeStart')} | 图片: {doc.count('<w:drawing>')} | SEQ图: {doc.count('SEQ 图')}")
    sys.exit(1 if errs else 0)

if __name__ == "__main__":
    main()
