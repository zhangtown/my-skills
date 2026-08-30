# -*- coding: utf-8 -*-
"""页面规格示例 —— 复制到工作目录 mockgen/ 后按指标改写。
复用 base.py 设计系统（stat_cards / toolbar_html / table_html / panel_html /
svg_line_chart / svg_donut / steps_html / legend_html / shell）。
页面函数返回 body HTML；ALL_PAGES 登记 (导航组, 导航项, 面包屑1, 面包屑2, 页面标题, 副标题, 函数)。
每个 ▲ 指标对应一页，页面风格需统一（同品牌同系统）。
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from base import *  # noqa: F401,F403

# ============ 示例：语义分析检测 ============
def p01():
    body = stat_cards([
        ("今日检测流量", "12.8G", "↑ 18.2% 较昨日", [12, 18, 15, 22, 20, 26, 30]),
        ("语义分析命中", "1,024", "高危 86 条", [8, 10, 9, 14, 12, 16, 20]),
        ("漏洞利用拦截", "317", "成功率 99.2%", [6, 8, 7, 10, 9, 12, 14]),
        ("误报率", "0.32%", "↓ 0.08%", [5, 6, 5, 4, 4, 3, 3]),
    ])
    body += toolbar_html([
        inp("全部攻击类型 ▾", 160, True), inp("全部检测引擎 ▾", 150, True),
        inp("2026-08-17 09:00 ~ 09:30", 260), btn("查询", "primary"), btn("重置"),
    ])
    body += table_html(
        ["时间", "源IP", "目的IP", "攻击类型", "语义分析引擎", "命中规则", "风险等级", "处置状态"],
        [
            ["09:28:14", "<span class='mono'>103.21.140.118</span>", "<span class='mono'>192.168.10.25</span>",
             "SQL注入-语义变体", "SQLi语义引擎 v3.1", "SQLi.Semantic.0241", "<span class='tag red'>高危</span>", "<span class='tag green'>已阻断</span>"],
            ["09:27:52", "<span class='mono'>45.152.87.11</span>", "<span class='mono'>192.168.10.36</span>",
             "XSS-编码混淆", "XSS语义引擎 v2.8", "XSS.Semantic.0187", "<span class='tag red'>高危</span>", "<span class='tag green'>已阻断</span>"],
            ["09:26:40", "<span class='mono'>185.220.101.5</span>", "<span class='mono'>192.168.12.8</span>",
             "命令注入-混淆", "CMDi语义引擎 v3.0", "CMDi.Semantic.0092", "<span class='tag orange'>中危</span>", "<span class='tag green'>已阻断</span>"],
        ],
        "语义分析引擎实时命中记录",
    )
    body += '<div class="chart-row"><div class="chart-box"><h4>语义分析引擎命中趋势（近24小时）</h4>' + \
        svg_line_chart(620, 200, [42, 55, 48, 63, 70, 58, 82, 95, 76, 88, 102, 120, 98, 110, 132, 128, 145, 138, 152, 166, 158, 172, 180, 190],
                       ["00:00", "04:00", "08:00", "12:00", "16:00", "20:00", "24:00"]) + \
        '</div><div class="chart-box"><h4>攻击类型分布</h4>' + \
        svg_donut(220, 200, [("SQL注入", 38, "#2f7cf6"), ("XSS", 24, "#16a34a"), ("命令注入", 18, "#f59e0b"), ("Webshell", 14, "#e11d48"), ("其他", 6, "#8b5cf6")], "1,024") + \
        '<div style="display:flex;justify-content:center;">' + \
        legend_html([("SQL注入", "#2f7cf6"), ("XSS", "#16a34a"), ("命令注入", "#f59e0b"), ("Webshell", "#e11d48")]) + \
        '</div></div></div>'
    return body

# ============ 示例：自定义登录入口（表单页） ============
def p08():
    form = """
    <div class="form-grid">
      <div class="f-item"><label>登录入口名称 *</label><div class="f-inp">企业ERP系统登录</div></div>
      <div class="f-item"><label>入口类型 *</label><div class="f-inp">自定义业务系统 <span>▾</span></div></div>
      <div class="f-item"><label>登录URL *</label><div class="f-inp">https://erp.jsclearing.com/login.do <span>✎</span></div></div>
      <div class="f-item"><label>IP地址 / 端口 *</label><div class="f-inp">192.168.10.88 <span>▾</span> : 8443</div></div>
      <div class="f-item"><label>用户名/口令提取参数 *</label><div class="f-inp">username / password</div></div>
      <div class="f-item"><label>参数提取位置 *</label><div class="f-inp">POST Body <span>▾</span></div></div>
      <div class="f-item"><label>登录成功判定条件 *</label><div class="f-inp">返回码=200 且 包含"welcome" <span>✎</span></div></div>
      <div class="f-item"><label>归属资产</label><div class="f-inp">ERP-APP-01 <span>▾</span></div></div>
    </div>
    <div style="display:flex;gap:12px;padding:6px 0 2px;"><div class="btn primary">保存配置</div><div class="btn">测试连接</div><div class="btn">取消</div></div>
    """
    return panel_html("自定义登录入口信息", form, btn("帮助") + btn("最近配置", ""))

ALL_PAGES = {
    "d01_semantic": ("detect", "攻击检测", "威胁检测", "攻击检测", "语义分析引擎 · 漏洞利用检测", "基于请求语义的漏洞利用智能分析，覆盖编码混淆与语义变形攻击", p01),
    "d08_login_custom": ("detect", "登录入口识别", "威胁检测", "登录入口识别", "自定义登录入口", "按名称/IP/端口/URL/参数等灵活自定义登录入口信息", p08),
}
