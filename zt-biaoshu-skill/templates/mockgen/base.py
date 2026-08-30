# -*- coding: utf-8 -*-
"""
网络入侵检测防御系统 产品功能截图生成器
生成 1920x1080 后台管理系统界面 HTML，用于招投标产品功能截图。
设计规范：中国企业级后台管理软件（深色侧边栏 + 浅色内容区 + 卡片化 + 数据表格 + SVG图表）
"""
import os
import json

BASE = os.path.dirname(os.path.abspath(__file__))
MOCKUP_DIR = os.path.join(BASE, "mockups")
os.makedirs(MOCKUP_DIR, exist_ok=True)

CSS = """
* { margin:0; padding:0; box-sizing:border-box; }
html,body { width:1920px; height:1080px; overflow:hidden; font-family:"Microsoft YaHei","PingFang SC","Helvetica Neue",Arial,sans-serif; background:#eef1f6; color:#2b3442; }
.app { display:flex; width:1920px; height:1080px; }
/* ---------- 侧边栏 ---------- */
.sidebar { width:230px; height:1080px; background:linear-gradient(180deg,#132743 0%,#0f1f38 100%); color:#b9c6d8; display:flex; flex-direction:column; flex-shrink:0; }
.logo { height:64px; display:flex; align-items:center; padding:0 18px; gap:10px; border-bottom:1px solid rgba(255,255,255,.08); }
.logo .logo-ic { width:34px; height:34px; border-radius:8px; background:linear-gradient(135deg,#2f7cf6,#16b3ac); display:flex; align-items:center; justify-content:center; color:#fff; font-weight:700; font-size:17px; flex-shrink:0; }
.logo .logo-tx { font-size:15px; color:#fff; font-weight:600; line-height:1.25; }
.logo .logo-tx small { display:block; font-size:10px; color:#7d8fa8; font-weight:400; }
.nav { flex:1; overflow:hidden; padding:10px 0; }
.nav .nav-group { padding:12px 18px 6px; font-size:11px; color:#5d708c; letter-spacing:1px; }
.nav .item { display:flex; align-items:center; gap:10px; height:42px; padding:0 18px; font-size:13.5px; color:#b9c6d8; cursor:default; }
.nav .item svg { width:17px; height:17px; flex-shrink:0; opacity:.85; }
.nav .item.active { background:linear-gradient(90deg,rgba(47,124,246,.25),rgba(47,124,246,.05)); color:#fff; border-left:3px solid #2f7cf6; }
.nav .item.active svg { opacity:1; }
.sidebar .s-foot { padding:14px 18px; border-top:1px solid rgba(255,255,255,.08); font-size:11px; color:#5d708c; }
/* ---------- 主区域 ---------- */
.main { flex:1; display:flex; flex-direction:column; height:1080px; overflow:hidden; }
.topbar { height:64px; background:#fff; border-bottom:1px solid #e4e9f0; display:flex; align-items:center; justify-content:space-between; padding:0 22px; flex-shrink:0; }
.crumb { font-size:14px; color:#8a94a6; }
.crumb b { color:#2b3442; font-weight:600; }
.top-right { display:flex; align-items:center; gap:18px; }
.search { width:240px; height:34px; border:1px solid #dfe5ee; border-radius:6px; display:flex; align-items:center; padding:0 12px; gap:8px; color:#aab4c4; font-size:13px; background:#f7f9fc; }
.notice { position:relative; width:34px; height:34px; display:flex; align-items:center; justify-content:center; color:#5b6b80; }
.user { display:flex; align-items:center; gap:10px; }
.avatar { width:34px; height:34px; border-radius:50%; background:linear-gradient(135deg,#2f7cf6,#16b3ac); color:#fff; display:flex; align-items:center; justify-content:center; font-size:14px; font-weight:600; }
.user .u-tx { font-size:13px; color:#3a4656; line-height:1.2; }
.user .u-tx small { display:block; font-size:11px; color:#9aa6b8; }
.content { flex:1; overflow:hidden; padding:20px 22px; }
.page-head { display:flex; align-items:flex-end; justify-content:space-between; margin-bottom:16px; }
.page-head h1 { font-size:21px; color:#1d2837; font-weight:700; }
.page-head p { font-size:13px; color:#8a94a6; margin-top:4px; }
/* ---------- 卡片 ---------- */
.cards { display:flex; gap:14px; margin-bottom:16px; }
.card { background:#fff; border:1px solid #e6ebf2; border-radius:10px; padding:16px 18px; flex:1; box-shadow:0 1px 3px rgba(20,40,80,.04); }
.card .c-label { font-size:12.5px; color:#8a94a6; display:flex; justify-content:space-between; align-items:center; }
.card .c-num { font-size:28px; font-weight:700; color:#1d2837; margin:8px 0 4px; font-family:"DIN Alternate","Arial"; }
.card .c-num em { font-style:normal; color:#16a34a; font-size:14px; font-weight:600; }
.card .c-num .down { color:#e11d48; }
.card .c-sub { font-size:12px; color:#aab4c4; }
.card .trend { display:flex; align-items:flex-end; gap:4px; height:34px; margin-top:8px; }
.card .trend i { width:10px; background:linear-gradient(180deg,#2f7cf6,#7fb2ff); border-radius:2px; display:block; }
/* ---------- 面板 ---------- */
.panel { background:#fff; border:1px solid #e6ebf2; border-radius:10px; margin-bottom:16px; box-shadow:0 1px 3px rgba(20,40,80,.04); }
.panel .p-head { display:flex; align-items:center; justify-content:space-between; padding:14px 18px; border-bottom:1px solid #eef1f6; }
.panel .p-title { font-size:15px; font-weight:600; color:#2b3442; display:flex; align-items:center; gap:8px; }
.panel .p-title::before { content:""; width:4px; height:16px; background:#2f7cf6; border-radius:2px; }
.panel .p-tools { display:flex; align-items:center; gap:10px; }
.panel .p-body { padding:16px 18px; }
/* ---------- 工具条 ---------- */
.toolbar { display:flex; align-items:center; gap:10px; padding:14px 18px; flex-wrap:wrap; }
.inp { height:32px; border:1px solid #dde4ee; border-radius:6px; padding:0 10px; font-size:13px; color:#3a4656; background:#fff; display:flex; align-items:center; gap:6px; min-width:130px; }
.inp.select::after { content:"▾"; color:#aab4c4; font-size:11px; margin-left:auto; }
.btn { height:32px; padding:0 16px; border-radius:6px; font-size:13px; display:inline-flex; align-items:center; gap:6px; cursor:default; border:1px solid #dde4ee; background:#fff; color:#3a4656; }
.btn.primary { background:#2f7cf6; color:#fff; border-color:#2f7cf6; }
.btn.success { background:#16a34a; color:#fff; border-color:#16a34a; }
.btn.warn { background:#f59e0b; color:#fff; border-color:#f59e0b; }
.btn.danger { background:#e11d48; color:#fff; border-color:#e11d48; }
/* ---------- 表格 ---------- */
table.tbl { width:100%; border-collapse:collapse; font-size:13px; }
table.tbl th { background:#f5f8fc; color:#5b6b80; font-weight:600; text-align:left; padding:11px 12px; border-bottom:1px solid #e6ebf2; white-space:nowrap; }
table.tbl td { padding:11px 12px; border-bottom:1px solid #f0f3f8; color:#3a4656; }
table.tbl tr:nth-child(even) td { background:#fafcff; }
table.tbl td .mono { font-family:"Consolas","Courier New"; color:#2f5aa8; }
table.tbl .tag { display:inline-block; padding:2px 9px; border-radius:10px; font-size:12px; }
.tag.green { background:#e6f7ee; color:#16a34a; }
.tag.red { background:#fdeaf0; color:#e11d48; }
.tag.orange { background:#fef4e6; color:#d97706; }
.tag.blue { background:#e8f1fe; color:#2f7cf6; }
.tag.gray { background:#f0f2f6; color:#6b7686; }
.tag.purple { background:#f1eafd; color:#7c3aed; }
.tag.cyan { background:#e0f7fa; color:#0891b2; }
/* 分页 */
.pager { display:flex; align-items:center; justify-content:flex-end; gap:8px; padding:12px 18px; font-size:13px; color:#5b6b80; }
.pager .pg { width:30px; height:30px; border:1px solid #dde4ee; border-radius:6px; display:flex; align-items:center; justify-content:center; background:#fff; }
.pager .pg.on { background:#2f7cf6; color:#fff; border-color:#2f7cf6; }
/* ---------- 图表 ---------- */
.chart-row { display:flex; gap:16px; }
.chart-box { flex:1; background:#fff; border:1px solid #e6ebf2; border-radius:10px; padding:16px; }
.chart-box h4 { font-size:14px; color:#2b3442; margin-bottom:12px; display:flex; align-items:center; gap:8px; }
.chart-box h4::before { content:""; width:4px; height:14px; background:#2f7cf6; border-radius:2px; }
.legend { display:flex; gap:16px; font-size:12px; color:#8a94a6; }
.legend i { display:inline-block; width:10px; height:10px; border-radius:2px; margin-right:5px; }
/* ---------- 表单 ---------- */
.form-grid { display:grid; grid-template-columns:1fr 1fr; gap:16px 24px; padding:6px 2px; }
.f-item label { display:block; font-size:13px; color:#5b6b80; margin-bottom:7px; }
.f-item .f-inp { height:36px; border:1px solid #dde4ee; border-radius:6px; padding:0 12px; font-size:13px; background:#fff; display:flex; align-items:center; color:#3a4656; }
.f-item .f-inp span { color:#aab4c4; }
.f-item .radio-row { display:flex; gap:20px; font-size:13px; color:#3a4656; height:36px; align-items:center; }
.radio { display:flex; align-items:center; gap:6px; }
.radio i { width:15px; height:15px; border-radius:50%; border:2px solid #c3cddc; display:inline-block; }
.radio.on i { border:5px solid #2f7cf6; }
.chk { display:flex; align-items:center; gap:6px; font-size:13px; color:#3a4656; }
.chk i { width:15px; height:15px; border-radius:3px; border:1px solid #c3cddc; background:#fff; display:inline-block; }
.chk.on i { background:#2f7cf6; border-color:#2f7cf6; position:relative; }
.chk.on i::after { content:"✓"; color:#fff; font-size:11px; position:absolute; left:2px; top:-1px; }
/* ---------- 步骤/时间线 ---------- */
.steps { display:flex; align-items:center; justify-content:space-between; padding:8px 6px 14px; }
.step { display:flex; flex-direction:column; align-items:center; gap:8px; width:120px; position:relative; }
.step .dot { width:38px; height:38px; border-radius:50%; display:flex; align-items:center; justify-content:center; font-size:14px; font-weight:600; color:#fff; background:#c3cddc; }
.step.done .dot { background:linear-gradient(135deg,#2f7cf6,#16b3ac); }
.step.cur .dot { background:#2f7cf6; box-shadow:0 0 0 5px rgba(47,124,246,.15); }
.step .s-tx { font-size:12.5px; color:#5b6b80; }
.step .s-sub { font-size:11px; color:#aab4c4; }
.steps .line { flex:1; height:2px; background:#e2e8f0; margin-bottom:34px; }
.steps .line.on { background:linear-gradient(90deg,#2f7cf6,#16b3ac); }
/* ---------- 树/列表 ---------- */
.list-rows .row { display:flex; align-items:center; gap:12px; padding:11px 6px; border-bottom:1px dashed #eef1f6; font-size:13px; color:#3a4656; }
.list-rows .row:last-child { border-bottom:none; }
.dot-ic { width:30px; height:30px; border-radius:8px; display:flex; align-items:center; justify-content:center; font-size:14px; flex-shrink:0; }
/* 404 fallback */
.note { background:#fff; border-left:4px solid #2f7cf6; border-radius:6px; padding:14px 18px; font-size:13px; color:#5b6b80; line-height:1.8; }
.note b { color:#2b3442; }
"""

NAV_ITEMS = [
    ("overview", "态势总览", [("总览驾驶舱",""), ("攻击态势",""), ("资产风险",""), ("威胁情报","")]),
    ("detect", "威胁检测", [("攻击检测",""), ("APT高级威胁",""), ("恶意文件检测",""), ("弱口令检测",""), ("登录入口识别","")]),
    ("analyze", "态势分析", [("威胁事件",""), ("威胁溯源",""), ("杀伤链分析",""), ("协议解析","")]),
    ("asset", "资产管理", [("资产发现",""), ("资产漏洞",""), ("API资产",""), ("应用识别","")]),
    ("response", "响应处置", [("联动阻断",""), ("诱捕反制",""), ("自动响应",""), ("沙箱检测","")]),
    ("log", "日志取证", [("PCAP取证",""), ("日志检索",""), ("离线回放","")]),
    ("sys", "系统管理", [("检测规则",""), ("白名单",""), ("证书管理",""), ("用户权限","")]),
]

def nav_svg(name):
    paths = {
        "overview": '<polygon points="3,11 22,4 18,21 12,17 8,21 3,11" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round"/>',
        "detect": '<path d="M4 6 L20 6 M4 12 L20 12 M4 18 L20 18" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/>',
        "analyze": '<path d="M3 17 L9 10 L14 14 L21 6" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/>',
        "asset": '<rect x="4" y="4" width="16" height="16" rx="2" fill="none" stroke="currentColor" stroke-width="1.6"/><circle cx="12" cy="12" r="3" fill="none" stroke="currentColor" stroke-width="1.6"/>',
        "response": '<path d="M12 3 L20 8 L12 13 L4 8 Z" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round"/><path d="M5 12 L4 21 L12 17 L20 21 L19 12" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round"/>',
        "log": '<rect x="4" y="4" width="16" height="16" rx="2" fill="none" stroke="currentColor" stroke-width="1.6"/><path d="M8 10 h8 M8 14 h5" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/>',
        "sys": '<circle cx="12" cy="12" r="8" fill="none" stroke="currentColor" stroke-width="1.6"/><circle cx="12" cy="12" r="3" fill="none" stroke="currentColor" stroke-width="1.6"/>',
    }
    return paths.get(name, "")

def nav_html(active_group, active_label):
    parts = ['<div class="nav">']
    for gid, gname, items in NAV_ITEMS:
        parts.append(f'<div class="nav-group">{gname}</div>')
        for label, _ in items:
            cls = "active" if (gid == active_group and label == active_label) else ""
            parts.append(f'<div class="item {cls}"><svg viewBox="0 0 24 24">{nav_svg(gid)}</svg><span>{label}</span></div>')
    parts.append('</div>')
    parts.append('<div class="s-foot">博智安全 · 态势感知平台 V4.2<br/>系统运行正常 · 引擎在线</div>')
    return "".join(parts)

def topbar_html(crumb_left, crumb_right):
    return f"""
    <div class="topbar">
      <div class="crumb">{crumb_left} <b>›</b> {crumb_right}</div>
      <div class="top-right">
        <div class="search">⌕ 搜索事件、IP、域名、资产…</div>
        <div class="notice">🔔</div>
        <div class="user"><div class="avatar">管</div><div class="u-tx">安全管理员<small>超级管理员</small></div></div>
      </div>
    </div>"""

def shell(active_group, active_label, crumb_left, crumb_right, page_title, page_sub, body):
    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>{page_title}</title><style>{CSS}</style></head>
<body><div class="app">
  <div class="sidebar">{nav_html(active_group, active_label)}
  </div>
  <div class="main">
    {topbar_html(crumb_left, crumb_right)}
    <div class="content">
      <div class="page-head"><div><h1>{page_title}</h1><p>{page_sub}</p></div>
      <div style="font-size:12.5px;color:#8a94a6;">数据更新于 2026-08-17 09:30:22</div></div>
      {body}
    </div>
  </div>
</div></body></html>"""

def stat_cards(items):
    """items: list of (label, num, sub, trend list)"""
    cards = []
    for label, num, sub, trend in items:
        bars = "".join(f'<i style="height:{h}px"></i>' for h in trend)
        cards.append(f"""<div class="card"><div class="c-label"><span>{label}</span><span style="color:#aab4c4;">•••</span></div>
        <div class="c-num">{num}</div><div class="c-sub">{sub}</div><div class="trend">{bars}</div></div>""")
    return f'<div class="cards">{"".join(cards)}</div>'

def toolbar_html(filters):
    """filters: list of html strings"""
    return f'<div class="toolbar">{"".join(filters)}</div>'

def inp(text, width=None, select=False):
    style = f' style="min-width:{width}px"' if width else ""
    cls = "inp select" if select else "inp"
    return f'<div class="{cls}"{style}>{text}</div>'

def btn(text, kind=""):
    return f'<div class="btn {kind}">{text}</div>'

def table_html(headers, rows, extra=None):
    th = "".join(f"<th>{h}</th>" for h in headers)
    trs = []
    for r in rows:
        tds = "".join(f"<td>{c}</td>" for c in r)
        trs.append(f"<tr>{tds}</tr>")
    return f'<div class="panel"><div class="p-head"><div class="p-title">{extra or "数据列表"}</div><div class="p-tools">{btn("导出", "")}{btn("刷新", "")}</div></div><table class="tbl"><thead><tr>{th}</tr></thead><tbody>{"".join(trs)}</tbody></table><div class="pager"><span>共 1,286 条记录</span><div class="pg">‹</div><div class="pg on">1</div><div class="pg">2</div><div class="pg">3</div><div class="pg">4</div><div class="pg">…</div><div class="pg">128</div><div class="pg">›</div></div></div>'

def panel_html(title, body_html, tools=None):
    tools_html = f'<div class="p-tools">{tools}</div>' if tools else '<div class="p-tools"></div>'
    return f'<div class="panel"><div class="p-head"><div class="p-title">{title}</div>{tools_html}</div><div class="p-body">{body_html}</div></div>'

# ---------- SVG 图表 ----------
def svg_line_chart(width, height, series, labels=None, color="#2f7cf6", fill=True):
    """series: list of values; returns svg"""
    maxv = max(series) * 1.15 or 1
    minv = min(series) * 0.8
    span = (maxv - minv) or 1
    pad_l, pad_r, pad_t, pad_b = 34, 14, 14, 24
    iw, ih = width, height
    step = (iw - pad_l - pad_r) / (len(series) - 1) if len(series) > 1 else 1
    pts = []
    for i, v in enumerate(series):
        x = pad_l + i * step
        y = pad_t + (maxv - v) / span * (ih - pad_t - pad_b)
        pts.append((x, y))
    path = " ".join(f"L{x:.1f},{y:.1f}" for x, y in pts[1:])
    area = f"M{pts[0][0]:.1f},{ih-pad_b} L{pts[0][0]:.1f},{pts[0][1]:.1f}" + path + f" L{pts[-1][0]:.1f},{ih-pad_b} Z"
    grid = "".join(f'<line x1="{pad_l}" y1="{pad_t + i*(ih-pad_t-pad_b)/4}" x2="{iw-pad_r}" y2="{pad_t + i*(ih-pad_t-pad_b)/4}" stroke="#eef1f6" stroke-width="1"/>' for i in range(5))
    glabels = "".join(f'<text x="{pad_l-8}" y="{pad_t + i*(ih-pad_t-pad_b)/4 + 4}" font-size="11" fill="#aab4c4" text-anchor="end">{int(maxv - i*(maxv-minv)/4)}</text>' for i in range(5))
    xlabels = ""
    if labels:
        n = len(labels)
        xlabels = "".join(f'<text x="{pad_l + i*(iw-pad_l-pad_r)/(n-1):.0f}" y="{ih-6}" font-size="11" fill="#aab4c4" text-anchor="middle">{labels[i]}</text>' for i in range(n))
    pts_dots = "".join(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3.2" fill="#fff" stroke="{color}" stroke-width="2"/>' for x, y in pts)
    fill_attr = f'<path d="{area}" fill="{color}" opacity="0.10"/>' if fill else ""
    return f'<svg viewBox="0 0 {iw} {ih}" width="{iw}" height="{ih}">{grid}{glabels}{fill_attr}<path d="M{pts[0][0]:.1f},{pts[0][1]:.1f}{path}" fill="none" stroke="{color}" stroke-width="2.4" stroke-linejoin="round" stroke-linecap="round"/>{pts_dots}{xlabels}</svg>'

def svg_bar_chart(width, height, items, color="#2f7cf6"):
    """items: list of (label, value)"""
    maxv = max(v for _, v in items) * 1.15 or 1
    pad_l, pad_b = 40, 24
    iw, ih = width, height
    n = len(items)
    bw = (iw - pad_l - 20) / n * 0.5
    bars = []
    for i, (lab, v) in enumerate(items):
        x = pad_l + i * (iw - pad_l - 20) / n + (iw - pad_l - 20) / n * 0.25
        h = (v / maxv) * (ih - pad_b - 16)
        bars.append(f'<rect x="{x:.1f}" y="{ih-pad_b-h:.1f}" width="{bw:.1f}" height="{h:.1f}" rx="3" fill="{color if i % 2 == 0 else "#7fb2ff"}"/>')
        bars.append(f'<text x="{x+bw/2:.1f}" y="{ih-8}" font-size="11" fill="#8a94a6" text-anchor="middle">{lab}</text>')
        bars.append(f'<text x="{x+bw/2:.1f}" y="{ih-pad_b-h-6:.1f}" font-size="11" fill="#3a4656" text-anchor="middle">{v}</text>')
    return f'<svg viewBox="0 0 {iw} {ih}" width="{iw}" height="{ih}">{bars}</svg>'

def svg_donut(width, height, items, center_label):
    """items: list of (label, value, color)"""
    total = sum(v for _, v, _ in items) or 1
    cx, cy, r = width / 2, height / 2, min(width, height) / 2 - 10
    r_in = r * 0.62
    start = -90
    arcs = []
    for lab, v, col in items:
        ang = v / total * 360
        a1, a2 = start, start + ang
        x1, y1 = cx + r * __import__("math").cos(__import__("math").radians(a1)), cy + r * __import__("math").sin(__import__("math").radians(a1))
        x2, y2 = cx + r * __import__("math").cos(__import__("math").radians(a2)), cy + r * __import__("math").sin(__import__("math").radians(a2))
        large = 1 if ang > 180 else 0
        arcs.append(f'<path d="M{x1:.1f},{y1:.1f} A{r},{r} 0 {large} 1 {x2:.1f},{y2:.1f}" fill="none" stroke="{col}" stroke-width="{r-r_in}" stroke-linecap="butt"/>')
        start = a2
    return f'<svg viewBox="0 0 {width} {height}" width="{width}" height="{height}">{arcs}<text x="{cx}" y="{cy-4}" font-size="20" font-weight="700" fill="#1d2837" text-anchor="middle">{center_label}</text><text x="{cx}" y="{cy+18}" font-size="11" fill="#aab4c4" text-anchor="middle">总计</text></svg>'

def legend_html(items):
    return f'<div class="legend">{"".join(f"<span><i style=\"background:{c}\"></i>{l}</span>" for l, c in items)}</div>'

def steps_html(steps):
    """steps: list of (label, sub, state) state: done/cur/wait"""
    parts = []
    for i, (lab, sub, state) in enumerate(steps):
        if i > 0:
            cls = "line on" if state != "wait" else "line"
            parts.append(f'<div class="{cls}"></div>')
        parts.append(f'<div class="step {state}"><div class="dot">{i+1}</div><div class="s-tx">{lab}</div><div class="s-sub">{sub}</div></div>')
    return f'<div class="steps">{"".join(parts)}</div>'
