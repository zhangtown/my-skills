#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
投标文件取证探针 —— 把 .docx / .xlsx 的"文本层看不到的东西"一次性抽成 JSON。

为什么需要它：纯文本审查会漏掉本项目最致命的一类问题——签章栏里填的是
打字打上去的公司名、而不是印章图片。文本层看起来"已经填了"，但盖没盖章
在字符层面完全看不出来。同理，文档属性里的真名、内部占位符、表格栏位
错序，也都藏在文件结构里。

用法：
    python probe_docx.py 投标文件.docx -o probe.json
    python probe_docx.py 跟踪表.xlsx -o xlsx_probe.json
    python probe_docx.py 投标文件.docx --print-summary

依赖：仅标准库（zipfile + xml.etree）。不需要 python-docx。
"""

import argparse
import json
import re
import sys
import zipfile
from xml.etree import ElementTree as ET

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
R = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
A = "{http://schemas.openxmlformats.org/drawingml/2006/main}"
WP = "{http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing}"
V = "{urn:schemas-microsoft-com:vml}"
PR = "{http://schemas.openxmlformats.org/package/2006/relationships}"
CP = "{http://schemas.openxmlformats.org/package/2006/metadata/core-properties}"
DC = "{http://purl.org/dc/elements/1.1/}"
DCTERMS = "{http://purl.org/dc/terms/}"

EMU_PER_CM = 360000

# 内部占位符：这些都是"还没填"的信号。
#
# 每条带一个基准置信度，因为**误报会毁掉整套判断的可信度**——实测过：
# 搜"待确认"命中 5 处，全是产品描述里的正常技术用语（"标记为待确认线索"、
# "待确认资产在风险清单中单独标注"），一处理均不是占位符。
# 报告里把"5 处占位符"当成结论说出去，整套审查结论就没人信了。
#
# 所以：**不抑制命中，但标注置信度**。低置信度的让审查人自己扫一眼就能排除。
PLACEHOLDER_PATTERNS = [
    (r"【[^】]*待填[^】]*】", "待填占位符", "高"),
    (r"【[^】]*响应位置[^】]*】", "响应位置占位符", "高"),
    (r"【[^】]*见批注[^】]*】", "见批注占位符", "高"),
    (r"【[^】]*】", "方括号占位符", "高"),
    (r"\[[A-Za-z\u4e00-\u9fff]{2,20}\]", "方括号占位符(英文)", "中"),
    (r"[×xX]{3,}", "连续叉号占位", "高"),
    (r"＿{3,}|_{5,}", "下划线占位", "高"),
    # ↓ 以下三个是"裸中文词"，最容易误报，置信度交给 _bare_word_confidence 判
    (r"需\s*补\s*充", "需补充标记", None),
    (r"待\s*定|待\s*确认|TBD", "待定标记", None),
    (r"\(?\s*请填[写写]?[^)）]*[)）]?", "请填写提示", None),
]

_PUNCT = " \t\r\n:：,，.。;；、()（）[]【】<>《》\"'“”‘’-_—/\\|*#"


def _bare_word_confidence(text, match):
    """裸中文词命中到底是占位符还是正文？

    真正的占位符有两个特征：**位置**上它单独占据一格或跟在字段名冒号后面
    （"供应商名称：待确认"），**内容**上周围没别的字。
    正文里的"待确认"恰好相反——嵌在一长串技术描述里，例如
    "标记为待确认线索"、"待确认资产在风险清单中单独标注……"。

    所以判据 = 位置 + 剩余实质字符数。宁可判低置信度让人眼扫一遍，
    也不能把正文词当占位符报出去。
    """
    rest = text[:match.start()] + text[match.end():]
    rest = "".join(ch for ch in rest if ch not in _PUNCT).strip()
    head = text[:match.start()].rstrip()
    at_standalone_pos = (not head) or head[-1:] in "：:（(【"
    if at_standalone_pos and len(rest) <= 6:
        return "中"          # 字段名冒号后或独立成行，很可能是真占位符
    if len(rest) <= 30:
        return "低"           # 短句里出现，值得看一眼
    return None              # 嵌在长句里，判为正文，不报


def _placeholder_confidence(text, match, base):
    return _bare_word_confidence(text, match) if base is None else base


# 签章栏位：出现这些字样说明这一段需要一个章或一个签名
SEAL_HINTS = ["（公章）", "(公章)", "（盖章）", "(盖章)", "（单位公章）",
              "供应商公章", "公司公章", "（签章）", "(签章)"]
SIGN_HINTS = ["（签字）", "(签字)", "签字：", "签名", "法定代表人（签字）",
              "授权代表（签字）", "委托代理人（签字）", "代表签字"]
DATE_HINTS = ["日期：", "年", "月", "日"]


def _text(el):
    return "".join(t.text or "" for t in el.iter(W + "t"))


def load_rels(zf, part="word/document.xml"):
    """返回 {rId: (Target, Type)}"""
    rels_path = part.rsplit("/", 1)[0] + "/_rels/" + part.rsplit("/", 1)[1] + ".rels"
    out = {}
    try:
        root = ET.fromstring(zf.read(rels_path))
    except KeyError:
        return out
    for rel in root:
        out[rel.get("Id")] = (rel.get("Target", ""), rel.get("Type", ""))
    return out


def para_image_info(p, rels):
    """这一段里有哪些图？返回 [(rId, 目标文件, 显示宽cm, 显示高cm, 是否emf/wmf)]"""
    found = []
    for blip in p.iter(A + "blip"):
        rid = blip.get(R + "embed")
        if rid:
            found.append(rid)
    # VML 里的 v:imagedata（老式粘贴的图，常见于扫描件）
    for img in p.iter(V + "imagedata"):
        rid = img.get(R + "id")
        if rid:
            found.append(rid)
    exts = []
    for ex in p.iter(WP + "extent"):
        try:
            cx = int(ex.get("cx", "0"))
            cy = int(ex.get("cy", "0"))
            if cx:
                exts.append((round(cx / EMU_PER_CM, 2), round(cy / EMU_PER_CM, 2)))
        except (TypeError, ValueError):
            continue
    for sh in p.iter(V + "shape"):
        st = sh.get("style", "") or ""
        m = re.search(r"width:([\d.]+)pt;height:([\d.]+)pt", st)
        if m:
            exts.append((round(float(m.group(1)) / 72 * 2.54, 2),
                         round(float(m.group(2)) / 72 * 2.54, 2)))

    out = []
    for i, rid in enumerate(found):
        target = rels.get(rid, ("", ""))[0]
        size = exts[i] if i < len(exts) else (exts[0] if exts else (None, None))
        out.append({
            "rId": rid,
            "target": target,
            "display_cm": size,
            "is_vector": bool(re.search(r"\.(emf|wmf)$", target or "", re.I)),
        })
    return out


def probe_docx(path):
    zf = zipfile.ZipFile(path)
    rels = load_rels(zf)
    doc = ET.fromstring(zf.read("word/document.xml"))

    paragraphs = []
    tables = []
    p_index = 0
    t_index = 0

    # 按文档顺序遍历段落与表格（w:tbl 是 w:body 的直接子元素）
    body = doc.find(W + "body")
    if body is None:
        body = doc

    def walk(node):
        nonlocal p_index, t_index
        for child in node:
            tag = child.tag
            if tag == W + "p":
                txt = _text(child).strip()
                imgs = para_image_info(child, rels)
                style_el = child.find(W + "pPr/" + W + "pStyle")
                style = style_el.get(W + "val") if style_el is not None else ""
                paragraphs.append({
                    "i": p_index,
                    "style": style,
                    "text": txt,
                    "images": imgs,
                })
                p_index += 1
            elif tag == W + "tbl":
                rows = []
                for tr in child.findall(W + "tr"):
                    cells = []
                    for tc in tr.findall(W + "tc"):
                        cells.append(_text(tc).strip())
                    rows.append(cells)
                tables.append({"i": t_index, "rows": rows})
                t_index += 1
                # 表格里的段落也要进来（图常常在表格单元格里）
                walk(child)
            elif tag in (W + "sdt", W + "sdtContent", W + "tc", W + "txbxContent"):
                walk(child)
            else:
                # 兜底：递归找嵌套内容
                if child.find(W + "p") is not None or child.find(W + "tbl") is not None:
                    walk(child)

    walk(body)

    # ---- 元数据 ----
    meta = {}
    for part, keys in (("docProps/core.xml",
                        {"creator": DC + "creator", "lastModifiedBy": CP + "lastModifiedBy",
                         "revision": CP + "revision", "created": DCTERMS + "created",
                         "modified": DCTERMS + "modified"}),
                       ("docProps/app.xml", {})):
        try:
            root = ET.fromstring(zf.read(part))
        except (KeyError, ET.ParseError):
            continue
        for k, tag in keys.items():
            el = root.find(tag)
            if el is not None and el.text:
                meta[k] = el.text
        if part.endswith("app.xml"):
            for el in root:
                tag = el.tag.split("}")[-1]
                if tag in ("Company", "Manager", "TotalTime", "Application",
                           "AppVersion", "Pages", "Words", "Characters"):
                    meta[tag.lower()] = el.text
            # 模板名/标题里的路径
            for el in root.iter():
                t = el.tag.split("}")[-1]
                if t in ("Template", "HyperlinkBase") and el.text:
                    meta.setdefault("paths", []).append(el.text)

    # ---- 编辑会话指纹 ----
    rsids = []
    try:
        sroot = ET.fromstring(zf.read("word/settings.xml"))
        for el in sroot.iter(W + "rsid"):
            v = el.get(W + "val")
            if v:
                rsids.append(v)
    except (KeyError, ET.ParseError):
        pass

    # ---- 批注作者 ----
    comment_authors = []
    try:
        croot = ET.fromstring(zf.read("word/comments.xml"))
        for c in croot:
            a = c.get(W + "author")
            if a:
                comment_authors.append(a)
    except (KeyError, ET.ParseError):
        pass

    # ---- 修订记录 ----
    revisions = []
    for el in doc.iter():
        tag = el.tag.split("}")[-1]
        if tag in ("ins", "del"):
            who = el.get(W + "author")
            if who:
                revisions.append({"type": tag, "author": who})

    # ---- 媒体清单 ----
    media = []
    for name in zf.namelist():
        if name.startswith("word/media/") or name.startswith("word/embeddings/"):
            media.append({"name": name, "bytes": zf.getinfo(name).file_size})

    # ---- 占位符扫描 ----
    placeholders = []
    for p in paragraphs:
        for pat, label, base in PLACEHOLDER_PATTERNS:
            for m in re.finditer(pat, p["text"]):
                conf = _placeholder_confidence(p["text"], m, base)
                if conf is None:
                    continue
                placeholders.append({
                    "i": p["i"], "kind": label, "confidence": conf,
                    "hit": m.group(0)[:60],
                    "context": p["text"][:90],
                })
    # 高置信度排前面——审查人从上往下看，看到第一个"低"就可以停了
    _order = {"高": 0, "中": 1, "低": 2}
    placeholders.sort(key=lambda h: _order[h["confidence"]])

    return {
        "file": path,
        "kind": "docx",
        "stats": {
            "paragraphs": len(paragraphs),
            "tables": len(tables),
            "images_referenced": sum(len(p["images"]) for p in paragraphs),
            "media_files": len(media),
            "media_bytes": sum(m["bytes"] for m in media),
            "rsid_count": len(rsids),
            "comments": len(comment_authors),
        },
        "metadata": meta,
        "comment_authors": sorted(set(comment_authors)),
        "revision_authors": sorted({r["author"] for r in revisions}),
        "paragraphs": paragraphs,
        "tables": tables,
        "media": media,
        "placeholders": placeholders,
    }


def probe_xlsx(path):
    """.xlsx 的痕迹体检——投标过程里的进度表/清单表同样会泄露个人信息。"""
    zf = zipfile.ZipFile(path)
    names = zf.namelist()
    out = {"file": path, "kind": "xlsx", "stats": {}, "metadata": {},
           "sheets": [], "comment_authors": [], "external_links": [],
           "hidden_sheets": [], "paths_in_formulas": []}

    # 工作表与隐藏状态
    try:
        wb = ET.fromstring(zf.read("xl/workbook.xml"))
        for sh in wb.iter():
            if sh.tag.split("}")[-1] == "sheet":
                state = sh.get("state") or "visible"
                out["sheets"].append({
                    "name": sh.get("name"),
                    "sheetId": sh.get("sheetId"),
                    "state": state,
                })
                if state != "visible":
                    out["hidden_sheets"].append(sh.get("name"))
    except (KeyError, ET.ParseError):
        pass

    # 批注作者
    for n in names:
        if re.match(r"xl/comments\d*\.xml", n) or re.match(r"xl/threadedComments/.*\.xml", n):
            try:
                root = ET.fromstring(zf.read(n))
            except ET.ParseError:
                continue
            for el in root.iter():
                for attr in ("author", "authorId", "personId"):
                    v = el.get(attr)
                    if v:
                        out["comment_authors"].append(v)
            # threadedComments 的作者表
            for el in root.iter():
                a = el.get("displayName") or el.get("name")
                if a and el.tag.split("}")[-1] in ("person", "author"):
                    out["comment_authors"].append(a)

    # 外部链接（别的文件路径 / 网址）
    for n in names:
        if n.startswith("xl/externalLinks/"):
            try:
                raw = zf.read(n).decode("utf-8", "ignore")
            except KeyError:
                continue
            for m in re.finditer(r"(file:///[^\"<]+|[A-Za-z]:\\\\?[^\"<]+)", raw):
                out["external_links"].append(m.group(0)[:200])

    # 元数据
    try:
        root = ET.fromstring(zf.read("docProps/core.xml"))
        for k, tag in (("creator", DC + "creator"),
                       ("lastModifiedBy", CP + "lastModifiedBy"),
                       ("revision", CP + "revision")):
            el = root.find(tag)
            if el is not None and el.text:
                out["metadata"][k] = el.text
    except (KeyError, ET.ParseError):
        pass
    try:
        root = ET.fromstring(zf.read("docProps/app.xml"))
        for el in root:
            tag = el.tag.split("}")[-1]
            if tag in ("Company", "Manager", "Application", "AppVersion"):
                out["metadata"][tag.lower()] = el.text
        for el in root.iter():
            if el.tag.split("}")[-1] == "lpstr" and el.text and re.search(r"[A-Za-z]:\\", el.text):
                out["metadata"].setdefault("paths", []).append(el.text)
    except (KeyError, ET.ParseError):
        pass

    # 自定义属性里也可能有路径
    for n in names:
        if n.startswith("docProps/custom.xml"):
            raw = zf.read(n).decode("utf-8", "ignore")
            for m in re.finditer(r"[A-Za-z]:\\\\[^\"<]{4,200}", raw):
                out["paths_in_formulas"].append(m.group(0)[:200])

    # 共享工作簿的修订记录
    out["stats"] = {
        "sheets": len(out["sheets"]),
        "hidden_sheets": len(out["hidden_sheets"]),
        "parts": len(names),
        "has_revision_log": any("revision" in n.lower() for n in names),
        "has_pivot_cache": any(n.startswith("xl/pivotCache/") for n in names),
    }
    out["comment_authors"] = sorted(set(filter(None, out["comment_authors"])))
    return out


def summarize(res):
    lines = []
    st = res["stats"]
    lines.append(f"文件: {res['file']}  ({res['kind']})")
    if res["kind"] == "docx":
        lines.append(f"段落 {st['paragraphs']} / 表格 {st['tables']} / 图片引用 {st['images_referenced']} / "
                     f"媒体文件 {st['media_files']} ({st['media_bytes']/1048576:.1f} MB)")
        md = res["metadata"]
        lines.append(f"作者={md.get('creator')!r} 最后修改者={md.get('lastModifiedBy')!r} "
                     f"公司={md.get('company')!r} 修订次数={md.get('revision')}")
        lines.append(f"rsid 条数={st['rsid_count']}（正常数十条；上千条说明历经长期改稿）")
        if res["comment_authors"]:
            lines.append(f"⚠️ 批注作者（会被评委看到）: {res['comment_authors']}")
        if res["revision_authors"]:
            lines.append(f"⚠️ 修订记录中出现的作者: {res['revision_authors']}")
        if res["placeholders"]:
            from collections import Counter
            hi = [p for p in res["placeholders"] if p["confidence"] == "高"]
            md = [p for p in res["placeholders"] if p["confidence"] == "中"]
            lo = [p for p in res["placeholders"] if p["confidence"] == "低"]
            c = Counter(p["kind"] for p in hi + md)
            lines.append(f"⚠️ 内部占位符 高{len(hi)} / 中{len(md)} / 低{len(lo)} 处: {dict(c)}")
            for p in res["placeholders"][:8]:
                lines.append(f"    [{p['confidence']}][{p['kind']}] P{p['i']} {p.get('hit')!r}")
            if lo:
                lines.append(f"    （另有 {len(lo)} 处低置信度命中，多为正文里的'待确认/需补充'等词，"
                             f"需人眼扫一遍——**不要把低置信度当占位符报出去**）")
                lines.append(f"    P{p['i']} [{p['kind']}] {p['hit']}")
        else:
            lines.append("占位符: 未发现（高/中置信度均为 0）")
    else:
        lines.append(f"工作表 {st['sheets']} / 隐藏表 {st['hidden_sheets']} / 部件 {st['parts']}")
        # 电子表的 metadata 必须打出来——真人名最常见的藏身处就是这里，
        # 而它只占一个 XML 字段，不主动拿就永远看不见。
        md = res["metadata"]
        lines.append(f"作者={md.get('creator')!r} 最后修改者={md.get('lastModifiedBy')!r} "
                     f"程序={md.get('application')!r} 公司={md.get('company')!r}")
        lines.append(f"共享修订记录={st['has_revision_log']} 透视缓存={st['has_pivot_cache']}")
        if res["comment_authors"]:
            lines.append(f"⚠️ 批注作者（会被评委看到）: {res['comment_authors']}")
        if res["hidden_sheets"]:
            lines.append(f"⚠️ 隐藏工作表: {res['hidden_sheets']}")
        if res["external_links"]:
            lines.append(f"⚠️ 外部链接: {res['external_links'][:5]}")
        if res.get("paths_in_formulas"):
            lines.append(f"⚠️ 公式里的本地/网络路径: {res['paths_in_formulas'][:5]}")
        if md.get("paths"):
            lines.append(f"⚠️ 元数据里的本地路径: {md['paths'][:5]}")
        danger = (md.get("creator"), md.get("lastModifiedBy"))
        if any(danger) or res["comment_authors"] or res["hidden_sheets"]:
            lines.append("→ 交付前重出：用“复制数值到新工作簿”另存，比删痕迹彻底；隐藏表要么删要么取消隐藏后重存。")
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser(description="投标文件痕迹探针（docx / xlsx）")
    ap.add_argument("path")
    ap.add_argument("-o", "--out", help="输出 JSON 路径（默认 <输入名>.probe.json）")
    ap.add_argument("--only", choices=["meta", "placeholders", "images", "tables", "seal"],
                    help="只输出某一类（仍会写全量 JSON）")
    ap.add_argument("--print-summary", action="store_true", help="在终端打印摘要")
    args = ap.parse_args()

    low = args.path.lower()
    if low.endswith(".docx"):
        res = probe_docx(args.path)
    elif low.endswith(".xlsx") or low.endswith(".xlsm"):
        res = probe_xlsx(args.path)
    elif low.endswith(".doc") or low.endswith(".xls"):
        print("❌ 老格式 (.doc/.xls) 请先用 WPS COM 转成 .docx/.xlsx 再跑。"
              "antiword 对中文 GB 文档经常直接失败。", file=sys.stderr)
        sys.exit(2)
    else:
        print(f"❌ 不支持的文件类型: {args.path}", file=sys.stderr)
        sys.exit(2)

    out = args.out or (args.path + ".probe.json")
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(res, fh, ensure_ascii=False, indent=1)

    if args.only:
        payload = {"file": res["file"], "stats": res["stats"]}
        if args.only == "meta":
            payload.update(metadata=res.get("metadata"),
                           comment_authors=res.get("comment_authors"),
                           revision_authors=res.get("revision_authors"))
        elif args.only == "placeholders":
            payload.update(placeholders=res.get("placeholders", []))
        elif args.only == "images":
            payload.update(images=[{"i": p["i"], "text": p["text"][:40], "images": p["images"]}
                                   for p in res.get("paragraphs", []) if p["images"]])
        elif args.only == "tables":
            payload.update(tables=res.get("tables", []))
        elif args.only == "seal":
            hits = []
            for p in res.get("paragraphs", []):
                t = p["text"]
                if any(h in t for h in SEAL_HINTS + SIGN_HINTS):
                    hits.append({"i": p["i"], "text": t[:100],
                                 "has_image": bool(p["images"]),
                                 "images": p["images"]})
            payload.update(seal_fields=hits)
        print(json.dumps(payload, ensure_ascii=False, indent=1))
    else:
        print(summarize(res))
        print(f"\n→ 全量 JSON 已写入 {out}")


if __name__ == "__main__":
    main()
