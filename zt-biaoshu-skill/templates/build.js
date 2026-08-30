// 主构建脚本：江苏交易场所登记结算 技术标（设备技术 + 安全服务）
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import {
  AlignmentType, Document, Footer, Header, HeadingLevel, LevelFormat, Numbering,
  Packer, PageNumber, Paragraph, TextRun, ImportedXmlComponent, convertInchesToTwip, LineRuleType, PageBreak,
} from "docx";
import {
  run, bodyPara, plainPara, centerPara, h1, h2, h3, h4,
  indicatorLabel, zongPara, fenPara, figPara, makeTable, tableGap, commentContent, FONT_BODY, STYLE_BODY,
} from "./docx_helpers.js";

const outputPath = process.argv[2];
if (!outputPath) throw new Error("Usage: node build.js output.docx");
const BASE = path.dirname(fileURLToPath(import.meta.url));
const SHOTS = path.join(BASE, "shots");
const DATA = JSON.parse(fs.readFileSync(path.join(BASE, "data", "indicators.json"), "utf-8"));
const DEV = DATA.DEV;
const SVC = DATA.SVC;

// ============ 工具 ============
function shortLabel(tender) {
  let t = String(tender).trim();
  const idx = t.search(/。提供|。支持提供|。录屏需/);
  if (idx > 0) t = t.slice(0, idx + 1);
  if (t.length > 80) t = t.slice(0, 79) + "…";
  return t;
}

function commentText(d) {
  return "【招标参数】" + d.num + " " + d.tender;
}

// ============ 编号配置 ============
const numberingConfig = {
  reference: "hd",
  levels: [
    { level: 0, format: LevelFormat.DECIMAL, text: "%1", alignment: AlignmentType.LEFT, start: 1 },
    { level: 1, format: LevelFormat.DECIMAL, text: "%1.%2", alignment: AlignmentType.LEFT, start: 1 },
    { level: 2, format: LevelFormat.DECIMAL, text: "%1.%2.%3", alignment: AlignmentType.LEFT, start: 1 },
    { level: 3, format: LevelFormat.DECIMAL, text: "%1.%2.%3.%4", alignment: AlignmentType.LEFT, start: 1 },
  ],
};

// ============ 偏离表 ============
const attrName = { "★": "★实质性", "▲": "▲重要", "一般": "一般" };
const deviationRows = DEV.map((d, i) => [
  String(i + 1),
  d.c1,
  d.tender,
  attrName[d.attr],
  "满足",
  "无偏离",
]);
const deviationTable = makeTable(
  ["序号", "一级分类", "技术参数要求", "指标属性", "响应结论", "偏离说明"],
  deviationRows,
  { widths: [700, 1500, 4700, 1100, 1100, 1100] },
);

// ============ 第一章 模块结构 ============
const MODULES = [
  {
    title: "软硬件架构与配置",
    c1: "软硬件架构",
    overview: "所投网络入侵检测防御系统（态势感知）采用标准2U机架式硬件形态，整机配备冗余双电源，内存不低于128GB、系统盘不低于240GB SSD、数据盘不低于20TB，配置不少于2个千兆电口与2个万兆光口，整机流量处理能力不低于2Gbps，具备3年软件维保与规则库升级服务，从硬件可靠性、存储能力、接口灵活性与处理性能四个维度全面满足采购人对核心网络安全防护设备的基础能力要求。",
  },
  {
    title: "授权与维保服务",
    c1: "软硬件要求",
    overview: "所投产品提供自验收之日起3年软件维保服务，服务期内包含全部规则库升级服务，规则库由专业安全研究团队持续维护、高频更新，重大安全事件第一时间发布紧急规则，确保设备在全生命周期内保持最佳检测效能，为采购人长期安全运营提供持续能力保障。",
  },
  {
    title: "威胁检测能力",
    c1: "威胁检测能力",
    overview: "所投产品构建了“通用攻击检测—加密流量检测—APT高级威胁检测—登录入口识别—弱密码与爆破检测—恶意文件检测”的立体化威胁检测体系：通用攻击检测覆盖TCP/UDP/ICMP FLOOD、SQL注入、XSS、Webshell、缓冲区溢出等攻击类型，并通过语义分析检测漏洞利用、通用规则覆盖0day攻击；加密流量检测支持HTTPS证书导入解密、TLS1.0-1.3解析、主机密钥采集解密ECDHE流量、JA3/JA3S指纹分析及WAF解密明文接入；APT检测覆盖反弹Shell、隐蔽隧道、主流Webshell家族、内网横移、权限维持及不少于260种自动化工具；同时支持登录入口自动识别与自定义、非明文协议弱口令检测与自定义弱口令策略、多引擎恶意文件检测与本地沙箱检测，形成从网络层到应用层、从明文到加密的全场景威胁检测能力。",
  },
  {
    title: "流量与协议解析",
    c1: "流量与协议",
    overview: "所投产品支持不少于40种协议的元数据解析与存储，支持自定义协议端口重定向，支持HTTP/2、数据库及工业控制等协议的深度解析；同时支持对Nmap、AWVS等扫描器及信息收集行为的检测，在网络攻击的侦查阶段即实现预警，为采购人提供完整的流量协议解析与异常行为分析能力。",
  },
  {
    title: "态势分析与威胁研判",
    c1: "态势与分析",
    overview: "所投产品提供态势大屏可视化、威胁事件两层聚合、全局/快速溯源、MITRE ATT&CK矩阵映射、攻击杀伤链建模与攻击结果自动化研判等核心态势分析能力，同时支持Syslog/Kafka/SNMP Trap日志外发、全流量PCAP留存下载、在线解码与PCAP离线回放检测，构建“看得见、析得清、溯得全、证得实”的完整威胁分析与取证体系。",
  },
  {
    title: "资产管理",
    c1: "资产管理",
    overview: "所投产品支持流量自动发现资产并识别OS/端口/服务/应用版本指纹，支持手动与文件导入资产，支持不少于7000种应用的自动识别（含开发框架、编程语言、开源组件、数据库等），支持流量指纹关联漏洞特征并以风险、资产、漏洞多视角呈现风险，支持API资产识别梳理，为采购人构建动态、完整、精细化的资产安全台账。",
  },
  {
    title: "响应处置",
    c1: "响应处置",
    overview: "所投产品具备完整的自动化响应处置能力，支持联动防火墙IP/端口阻断、TCP RST旁路阻断（二层/三层）、同品牌HIDS/WAF联动（隔离主机、下发策略）、按威胁/资产等级组合触发的自动响应策略，以及网络层引流至蜜罐的诱捕反制能力，形成“检测—研判—处置—反制”的安全运营闭环。",
  },
  {
    title: "系统管理",
    c1: "系统管理",
    overview: "所投产品支持自定义检测白名单（正则/包含匹配）、自定义PCRE检测规则（HTTP/TCP/UDP双向）、XFF字段配置与攻击IP替换，并支持三权分立、双因子认证与账户安全策略，在提供灵活检测定制能力的同时，保障系统自身的访问安全与操作审计合规。",
  },
  {
    title: "产品资质",
    c1: "资质要求",
    overview: "所投产品已具备网络安全专用产品安全认证、CNNVD兼容性认证及计算机软件著作权，产品合规性与自主知识产权均有保障，相关证书复印件随本响应文件一并提供并加盖投标单位公章。",
  },
];

// H4 名称映射
const H4_NAME = {
  "硬件形态": "硬件形态与性能配置",
  "授权与维保": "授权与维保服务",
  "通用攻击检测": "通用攻击检测能力",
  "加密流量检测": "加密流量检测能力",
  "APT/高级威胁": "APT高级威胁检测",
  "登录入口识别": "登录入口识别能力",
  "弱密码与爆破": "弱密码与爆破检测",
  "恶意文件检测": "恶意文件检测能力",
  "协议解析": "协议元数据解析",
  "异常行为分析": "异常行为分析",
  "态势大屏": "核心态势可视化",
  "威胁分析": "威胁分析与溯源",
  "日志与取证": "日志外发与流量取证",
  "资产发现": "资产自动发现",
  "资产漏洞": "资产漏洞关联分析",
  "API梳理": "API资产梳理",
  "联动阻断": "联动阻断能力",
  "诱捕反制": "蜜罐诱捕反制",
  "规则与白名单": "检测规则与白名单",
  "产品资质": "产品资质认证",
};

function groupBy(records, keyFn) {
  const map = new Map();
  for (const r of records) {
    const k = keyFn(r);
    if (!map.has(k)) map.set(k, []);
    map.get(k).push(r);
  }
  return map;
}

// ============ 第一章正文 ============
function chapter1Children(comments) {
  const children = [];
  children.push(h1("设备技术响应"));

  children.push(h2("响应总述"));
  children.push(bodyPara("针对江苏交易场所登记结算有限公司本次询价采购的网络入侵检测防御系统（态势感知），博智安全科技股份有限公司提供的产品完全响应招标文件“四、技术指标（一）网络入侵检测防御系统（态势感知）参数”的全部技术指标要求，实质性条款（★）全部满足、无偏离，重要指标（▲）与一般技术参数均满足要求、无负偏离。"));
  children.push(bodyPara("本方案所投产品为标准2U机架式硬件设备，配备双电源、128GB内存、20TB以上数据盘与万兆接口，具备2Gbps以上流量处理能力，在通用攻击检测、加密流量检测、APT高级威胁检测、登录入口识别、弱密码与爆破检测、恶意文件检测、协议解析、态势分析、资产管理、响应处置与系统管理等方面提供完整能力，能够满足采购人“软件服务深度排查整改+硬件设备实时防御拦截”的立体化安全防护建设需求。"));
  children.push(bodyPara("本响应文件对全部技术指标逐条进行响应，每条指标响应均采用“总体响应+详细阐述”的结构：总体响应部分对该项指标所对应产品能力进行功能概述，详细阐述部分对功能实现方式、技术特点与满足情况进行展开说明；招标文件原始技术指标以批注形式标注于对应指标响应位置，便于评审专家逐条对照核验。对标注“▲”的重要指标，本响应文件同步提供产品功能截图（详见证明材料说明），作为功能符合性的直观证明。"));
  children.push(tableGap());

  children.push(h2("技术指标响应偏离表"));
  children.push(bodyPara("本表依据招标文件“四、技术指标（一）网络入侵检测防御系统（态势感知）参数”逐条编制。表中“★”为实质性必须满足项，不允许偏离；“▲”为重要指标；未标注的为一般技术参数。全部条款响应结论均为“满足，无偏离”。"));
  children.push(deviationTable);
  children.push(tableGap());

  children.push(h2("设备功能与技术能力说明"));
  let cid = 1;
  const devByC1 = groupBy(DEV, (d) => d.c1);
  for (const mod of MODULES) {
    children.push(h3(mod.title));
    children.push(bodyPara(mod.overview));
    const items = devByC1.get(mod.c1) || [];
    const byC2 = groupBy(items, (d) => d.c2);
    for (const [c2, list] of byC2) {
      children.push(h4(H4_NAME[c2] || c2));
      for (const d of list) {
        children.push(indicatorLabel(d.num + " " + d.tender));
        const cidNow = cid++;
        comments.push({ id: cidNow, text: commentText(d) });
        children.push(zongPara(cidNow, d.zong));
        for (const f of d.fen) children.push(fenPara(f));
        if (d.shot) {
          const imgPath = fs.readFileSync(path.join(SHOTS, d.shot));
          children.push(...figPara(imgPath, d.caption, 596));
        }
      }
    }
  }

  children.push(h2("证明材料说明"));
  children.push(bodyPara("针对招标文件要求提供证明材料的条款，本响应文件随附如下证明材料，均加盖投标单位公章："));
  children.push(makeTable(
    ["证明材料类型", "对应技术指标", "证明方式"],
    [
      ["产品功能截图", "APT/高级威胁检测（反弹Shell、隐蔽隧道、Webshell、自动化工具）", "系统功能界面截图"],
      ["产品功能截图", "登录入口自动识别与自定义", "系统功能界面截图"],
      ["产品功能截图", "弱口令检测（非明文协议/自定义策略）", "系统功能界面截图"],
      ["产品功能截图", "恶意文件专项检测、多引擎杀毒、本地沙箱", "系统功能界面截图"],
      ["产品功能截图", "协议解析、威胁聚合、溯源、杀伤链、自动化研判", "系统功能界面截图"],
      ["产品功能截图", "PCAP取证、离线回放、资产发现、应用识别、资产漏洞", "系统功能界面截图"],
      ["产品功能截图", "API资产、联动阻断、诱捕、白名单、PCRE规则、XFF", "系统功能界面截图"],
      ["产品功能截图", "产品资质（安全认证/CNNVD/软件著作权）", "系统信息界面截图"],
      ["功能演示录屏", "登录入口自定义、弱口令策略自定义、威胁事件聚合", "完整屏幕录屏（含解说、账号登录退出）"],
      ["承诺函", "主机密钥采集解密ECDHE流量、WAF解密后接入明文流量", "加盖投标单位公章承诺函"],
      ["证书复印件", "网络安全专用产品安全认证、CNNVD兼容性认证、计算机软件著作权", "证书复印件加盖投标单位公章"],
    ],
    { widths: [1600, 4300, 2200] },
  ));
  children.push(tableGap());

  // ---- 承诺函（每个单独一页，自动编号 1.4.1 / 1.4.2） ----
  const promiseBlock = (title, paras) => {
    const out = [];
    out.push(new Paragraph({ children: [new PageBreak()] }));
    out.push(h3(title));
    out.push(new Paragraph({
      style: STYLE_BODY,
      alignment: AlignmentType.JUSTIFIED,
      spacing: { after: 0, line: 300, lineRule: LineRuleType.AUTO },
      children: [run("致：江苏交易场所登记结算有限公司", { bold: true })],
    }));
    for (const ptext of paras) out.push(bodyPara(ptext));
    out.push(plainPara("特此承诺。"));
    out.push(plainPara("　"));
    out.push(new Paragraph({ alignment: AlignmentType.RIGHT, spacing: { before: 240, after: 0, line: 300, lineRule: LineRuleType.AUTO }, children: [run("承诺单位（盖章）：博智安全科技股份有限公司")] }));
    out.push(new Paragraph({ alignment: AlignmentType.RIGHT, spacing: { after: 0, line: 300, lineRule: LineRuleType.AUTO }, children: [run("法定代表人或授权代表（签字）：")] }));
    out.push(new Paragraph({ alignment: AlignmentType.RIGHT, spacing: { after: 0, line: 300, lineRule: LineRuleType.AUTO }, children: [run("日　　期：2026年8月17日")] }));
    return out;
  };

  children.push(bodyPara("根据招标文件技术指标要求，本响应文件随附下列承诺函，每份承诺函均加盖投标单位公章，单独成页，作为对应技术指标的证明材料："));
  children.push(...promiseBlock("承诺函（主机密钥采集解密ECDHE流量）", [
    "我方博智安全科技股份有限公司（以下简称“我方”）在参与贵单位网络入侵检测防御系统及配套安全服务项目询价采购活动中，就所投网络入侵检测防御系统（态势感知）产品相关技术指标郑重承诺如下：",
    "一、我方所投网络入侵检测防御系统（态势感知）产品支持主机密钥采集方式解密基于ECDHE密钥交换的加密流量。产品通过在被监测主机侧部署轻量级密钥采集代理，在密钥协商过程中实时采集会话密钥，并通过安全通道回传至检测设备，实现对采用前向保密（PFS）算法的加密流量进行实时解密与深度安全检测，完全满足招标文件“四、技术指标（一）网络入侵检测防御系统（态势感知）参数”中“▲3.支持主机密钥采集解密ECDHE流量。提供承诺函并加盖投标单位公章”的条款要求。",
    "二、我方承诺上述内容真实、合法、有效，如存在虚假响应或与实际情况不符，我方愿承担由此产生的一切法律责任及相应后果。",
  ]));
  children.push(...promiseBlock("承诺函（WAF解密后接入明文流量）", [
    "我方博智安全科技股份有限公司（以下简称“我方”）在参与贵单位网络入侵检测防御系统及配套安全服务项目询价采购活动中，就所投网络入侵检测防御系统（态势感知）产品相关技术指标郑重承诺如下：",
    "一、我方所投网络入侵检测防御系统（态势感知）产品支持通过WAF对HTTPS流量进行解密后接入明文流量的部署方式。产品支持与WAF设备协同联动，由WAF完成HTTPS流量的TLS终结与解密，并将解密后的明文HTTP流量通过镜像/分流方式接入检测设备进行深度安全检测，实现对加密流量场景下攻击行为的有效识别与处置，完全满足招标文件“四、技术指标（一）网络入侵检测防御系统（态势感知）参数”中“▲5.支持通过WAF对HTTPS流量进行解密后接入明文流量。提供承诺函并加盖投标单位公章”的条款要求。",
    "二、我方承诺上述内容真实、合法、有效，如存在虚假响应或与实际情况不符，我方愿承担由此产生的一切法律责任及相应后果。",
  ]));
  // 第二章另起新页
  children.push(new Paragraph({ children: [new PageBreak()] }));
  return children;
}

// ============ 第二章 ============
function svcItem(comments, d, extra = {}) {
  const out = [];
  if (extra.h4) out.push(h4(extra.h4));
  if (extra.lead) out.push(bodyPara(extra.lead));
  out.push(indicatorLabel(d.num + " " + d.tender));
  const cid = extra.cid;
  comments.push({ id: cid, text: commentText(d) });
  out.push(zongPara(cid, d.zong));
  for (const f of d.fen) out.push(fenPara(f));
  if (d.shot && !extra.noShot) {
    const imgPath = fs.readFileSync(path.join(SHOTS, d.shot));
    out.push(...figPara(imgPath, d.caption, 596));
  }
  return out;
}

function findSvc(c1, c2) {
  return SVC.find((d) => d.c1 === c1 && d.c2 === c2);
}

function chapter2Children(comments, cidStart) {
  const children = [];
  let cid = cidStart;
  children.push(h1("安全服务响应"));

  children.push(h2("渗透测试实战成果"));
  children.push(bodyPara("依据招标文件评审标准，安全服务项以渗透测试实战漏洞挖掘能力作为评审依据，投标人需提供针对采购人官网系统、协会网站系统开展渗透测试出具的正式渗透测试报告。博智安全科技股份有限公司已于2026年7月8日完成针对江苏交易场所登记结算有限公司官网系统（www.jsclearing.com）及江苏省交易场所协会网站系统（www.jssea.org.cn）的渗透测试工作，并出具正式渗透测试报告（报告编号：BZ-PT-2026-0718），报告截图见下图。"));
  children.push(...figPara(fs.readFileSync(path.join(SHOTS, "s01_ptest.png")), "站点渗透测试报告", 596));
  children.push(bodyPara("本次渗透测试覆盖资产如下表所示："));
  children.push(makeTable(
    ["序号", "测试资产", "备注"],
    [
      ["1", "www.jsclearing.com", "江苏交易场所登记结算有限公司"],
      ["2", "www.jssea.org.cn", "江苏省交易场所协会"],
    ],
    { widths: [800, 3000, 4300] },
  ));
  children.push(tableGap());
  children.push(bodyPara("本次渗透测试共发现有效漏洞3项，漏洞均可复现，不存在恶意误报，漏洞清单及危害等级如下表所示："));
  children.push(makeTable(
    ["序号", "漏洞名称", "危害等级"],
    [
      ["1", "接口未授权访问", "中危"],
      ["2", "信息泄露", "低危"],
      ["3", "高危文件开放", "低危"],
    ],
    { widths: [800, 4000, 3300] },
  ));
  children.push(tableGap());
  children.push(bodyPara("依据招标文件规定的安全服务得分计算公式，本次渗透测试发现中危风险1条、低危风险2条、高危风险0条、严重风险0条，安全服务得分计算如下：安全服务得分＝（低危风险数量×0.3）＋（中危风险数量×0.6）＋（高危风险数量×1.2）＋（严重风险数量×2.4）＝2×0.3＋1×0.6＝1.2分。所发现漏洞均可复现，恶意误报不计入统计，全部漏洞已协助采购人完成整改或提供整改建议。"));
  children.push(bodyPara("各漏洞的详细情况如下："));
  children.push(plainPara([run("1. 接口未授权访问（中危）：", { bold: true })]));
  children.push(bodyPara("Common接口存在未授权访问，攻击者可通过该接口下载文件。接口地址为api/common/download/resource?resource=与api/common/download?fileName=。访问站点http://www.jsclearing.com/api/common/download/resource?resource=/profile/../../../../../../../etc/hosts被拦截，当存在规则之外的文件时可能被下载。修复建议：对接口进行必要鉴权，限制未授权访问。"));
  children.push(plainPara([run("2. 信息泄露（低危）：", { bold: true })]));
  children.push(bodyPara("插件安装版本等信息泄露，若版本较低，攻击者可针对性发起攻击。泄露地址包括http://www.jssea.org.cn/wp-content/plugins/content-views-query-and-display-post-page/README.txt及http://www.jssea.org.cn/readme.html。修复建议：删除不必要的指纹信息。"));
  children.push(plainPara([run("3. 高危文件开放（低危）：", { bold: true })]));
  children.push(bodyPara("攻击者可通过发送特制请求对站点造成拒绝服务或其他未知危害。涉及接口http://www.jssea.org.cn/xmlrpc.php与http://www.jssea.org.cn/wp-cron.php，使用XML-RPC和Cron发起的WordPress攻击可能导致服务器变慢或拒绝网络服务。修复建议：从WP文件夹根目录删除xml-rpc.php文件，并仅对已知可信IP放行XML-RPC。"));
  children.push(tableGap());

  children.push(h2("安全服务总体方案"));
  children.push(bodyPara("本方案面向江苏交易场所登记结算有限公司构建“风险排查—隐患整改—实时防御—应急保障”的闭环安全服务体系，通过专业的漏洞扫描、渗透测试、暴露面梳理、重保值守与应急演练服务，全面排查并协助整改现有系统的安全隐患，补齐网络安全防护缺口，保障公司核心业务在各类攻击高发及重要活动期间的稳定运行，服务体系建设完全遵循招标文件对服务周期、团队配置、保密要求与响应机制的各项规定。"));

  children.push(h3("服务周期"));
  children.push(...svcItem(comments, findSvc("服务周期与商务要求", "服务周期"), { cid: cid++ }));

  children.push(h3("团队配置"));
  children.push(...svcItem(comments, findSvc("服务周期与商务要求", "团队配置"), { cid: cid++ }));

  children.push(h3("保密要求"));
  children.push(...svcItem(comments, findSvc("服务周期与商务要求", "保密要求"), { cid: cid++ }));

  children.push(h3("响应机制"));
  children.push(...svcItem(comments, findSvc("服务周期与商务要求", "响应要求"), { cid: cid++ }));

  children.push(h2("分项服务实施方案"));

  children.push(h3("漏洞扫描服务"));
  children.push(...svcItem(comments, findSvc("漏洞扫描服务", "服务目标"), { cid: cid++ }));
  children.push(...svcItem(comments, findSvc("漏洞扫描服务", "扫描范围"), { cid: cid++ }));

  children.push(h3("渗透测试服务"));
  children.push(...svcItem(comments, findSvc("渗透测试服务", "服务目标"), { cid: cid++, noShot: true }));
  children.push(...svcItem(comments, findSvc("渗透测试服务", "服务内容"), { cid: cid++ }));
  children.push(...svcItem(comments, findSvc("渗透测试服务", "服务频率"), { cid: cid++ }));

  children.push(h3("暴露面梳理服务"));
  children.push(...svcItem(comments, findSvc("暴露面梳理服务", "服务目标"), { cid: cid++ }));
  children.push(...svcItem(comments, findSvc("暴露面梳理服务", "服务内容"), { cid: cid++ }));
  children.push(...svcItem(comments, findSvc("暴露面梳理服务", "服务频次"), { cid: cid++ }));
  children.push(...svcItem(comments, findSvc("暴露面梳理服务", "输出文档"), { cid: cid++ }));

  children.push(h3("重保值守服务"));
  children.push(...svcItem(comments, findSvc("重保值守服务", "服务目标"), { cid: cid++ }));
  children.push(...svcItem(comments, findSvc("重保值守服务", "服务内容"), { cid: cid++ }));
  children.push(...svcItem(comments, findSvc("重保值守服务", "服务人天"), { cid: cid++ }));
  children.push(...svcItem(comments, findSvc("重保值守服务", "输出文档"), { cid: cid++ }));

  children.push(h3("网络安全应急演练"));
  children.push(...svcItem(comments, findSvc("专项服务", "网络安全应急演练"), { cid: cid++ }));

  children.push(h2("服务保障与质量承诺"));
  children.push(h3("服务质量保障"));
  children.push(bodyPara("投标人建立覆盖服务全过程的质量管理体系：服务实施前编制详细服务计划并经采购人确认；服务实施中严格执行标准化作业流程（SOP），关键环节由项目负责人复核把关；服务完成后输出规范的服务报告并经内部三级审核（工程师自检、组长复核、项目经理终审）后提交采购人。投标人同步建立服务质量回访机制，定期征求采购人意见，对服务中发现的不足及时整改，确保服务交付质量持续满足采购人要求。"));
  children.push(h3("人员保障"));
  children.push(bodyPara("投标人为本项目配备专属服务团队并保持人员稳定，项目负责人、资深渗透工程师、资深网络安全工程师均具备相应资质与丰富实战经验；投标人建立人员备份机制，当核心人员因特殊情况无法履职时，由同等能力人员及时顶替并提前征得采购人同意；同时依托公司后台安全研究团队、漏洞挖掘团队与威胁情报团队，为项目提供持续的专家资源与技术支撑，保障服务能力不因人员变动而削弱。"));
  children.push(h3("文档与知识转移"));
  children.push(bodyPara("投标人在服务过程中完整交付各类服务文档（漏洞扫描报告、渗透测试报告、暴露面梳理报告、值守日报、应急响应报告、重保总结报告、应急演练总结评估报告等），并通过季度服务总结、年度安全态势汇报等形式向采购人管理层呈现安全服务成效；服务期内提供安全知识培训（含安全意识培训、漏洞整改技术培训、应急响应演练培训等），帮助采购人运维团队提升安全能力，实现安全知识的有效转移。"));
  children.push(h3("服务承诺"));
  children.push(bodyPara("投标人郑重承诺：严格履行招标文件及合同约定的全部服务内容与服务标准；严格遵守保密要求，保障采购人信息安全；建立7×24小时响应机制，重大安全事件30分钟内到达现场、1小时内完成排查并提供解决方案；服务履约达标、无重大安全事故、无投诉违约前提下，无特殊情况自动续签第二年、第三年服务；全力配合采购人完成项目验收与考核，接受采购人监督，确保安全服务体系长期稳定运行，为采购人核心业务的安全稳定保驾护航。"));

  return children;
}

// ============ 组装文档 ============
const comments = [];

const coverChildren = [
  new Paragraph({ spacing: { before: 2400, after: 200 }, alignment: AlignmentType.CENTER, children: [new TextRun({ text: "江苏交易场所登记结算有限公司", font: FONT_BODY, bold: true, size: 56, color: "000000" })] }),
  new Paragraph({ spacing: { after: 600 }, alignment: AlignmentType.CENTER, children: [new TextRun({ text: "网络入侵检测防御系统及配套安全服务项目", font: FONT_BODY, bold: true, size: 56, color: "000000" })] }),
  new Paragraph({ spacing: { after: 2400 }, alignment: AlignmentType.CENTER, children: [new TextRun({ text: "技术标（设备技术响应 · 安全服务响应）", font: FONT_BODY, bold: true, size: 44, color: "000000" })] }),
  new Paragraph({ spacing: { after: 120 }, alignment: AlignmentType.CENTER, children: [run("投标人：博智安全科技股份有限公司", { size: 32 })] }),
  new Paragraph({ spacing: { after: 120 }, alignment: AlignmentType.CENTER, children: [run("日　期：2026年8月17日", { size: 32 })] }),
  new Paragraph({ alignment: AlignmentType.CENTER, children: [run("（本册为技术标之设备技术与安全服务部分）", { size: 24, color: "000000" })] }),
];

function tocField() {
  const cached = `
    <w:p><w:pPr><w:pStyle w:val="TOC1"/><w:tabs><w:tab w:val="right" w:leader="dot" w:pos="9200"/></w:tabs></w:pPr><w:r><w:t>第一章 设备技术响应</w:t></w:r><w:r><w:tab/></w:r><w:r><w:t>1</w:t></w:r></w:p>
    <w:p><w:pPr><w:pStyle w:val="TOC2"/><w:tabs><w:tab w:val="right" w:leader="dot" w:pos="9200"/></w:tabs><w:ind w:left="240"/></w:pPr><w:r><w:t>一、响应总述</w:t></w:r><w:r><w:tab/></w:r><w:r><w:t>1</w:t></w:r></w:p>
    <w:p><w:pPr><w:pStyle w:val="TOC2"/><w:tabs><w:tab w:val="right" w:leader="dot" w:pos="9200"/></w:tabs><w:ind w:left="240"/></w:pPr><w:r><w:t>二、技术指标响应偏离表</w:t></w:r><w:r><w:tab/></w:r><w:r><w:t>1</w:t></w:r></w:p>
    <w:p><w:pPr><w:pStyle w:val="TOC2"/><w:tabs><w:tab w:val="right" w:leader="dot" w:pos="9200"/></w:tabs><w:ind w:left="240"/></w:pPr><w:r><w:t>三、设备功能与技术能力说明</w:t></w:r><w:r><w:tab/></w:r><w:r><w:t>1</w:t></w:r></w:p>
    <w:p><w:pPr><w:pStyle w:val="TOC2"/><w:tabs><w:tab w:val="right" w:leader="dot" w:pos="9200"/></w:tabs><w:ind w:left="240"/></w:pPr><w:r><w:t>四、证明材料说明</w:t></w:r><w:r><w:tab/></w:r><w:r><w:t>1</w:t></w:r></w:p>
    <w:p><w:pPr><w:pStyle w:val="TOC1"/><w:tabs><w:tab w:val="right" w:leader="dot" w:pos="9200"/></w:tabs></w:pPr><w:r><w:t>第二章 安全服务响应</w:t></w:r><w:r><w:tab/></w:r><w:r><w:t>1</w:t></w:r></w:p>
    <w:p><w:pPr><w:pStyle w:val="TOC2"/><w:tabs><w:tab w:val="right" w:leader="dot" w:pos="9200"/></w:tabs><w:ind w:left="240"/></w:pPr><w:r><w:t>一、渗透测试实战成果</w:t></w:r><w:r><w:tab/></w:r><w:r><w:t>1</w:t></w:r></w:p>
    <w:p><w:pPr><w:pStyle w:val="TOC2"/><w:tabs><w:tab w:val="right" w:leader="dot" w:pos="9200"/></w:tabs><w:ind w:left="240"/></w:pPr><w:r><w:t>二、安全服务总体方案</w:t></w:r><w:r><w:tab/></w:r><w:r><w:t>1</w:t></w:r></w:p>
    <w:p><w:pPr><w:pStyle w:val="TOC2"/><w:tabs><w:tab w:val="right" w:leader="dot" w:pos="9200"/></w:tabs><w:ind w:left="240"/></w:pPr><w:r><w:t>三、分项服务实施方案</w:t></w:r><w:r><w:tab/></w:r><w:r><w:t>1</w:t></w:r></w:p>
    <w:p><w:pPr><w:pStyle w:val="TOC2"/><w:tabs><w:tab w:val="right" w:leader="dot" w:pos="9200"/></w:tabs><w:ind w:left="240"/></w:pPr><w:r><w:t>四、服务保障与质量承诺</w:t></w:r><w:r><w:tab/></w:r><w:r><w:t>1</w:t></w:r></w:p>`;
  return ImportedXmlComponent.fromXmlString(
    `<w:sdt xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
      <w:sdtPr><w:alias w:val="目录"/><w:docPartObj><w:docPartGallery w:val="Table of Contents"/><w:docPartUnique/></w:docPartObj></w:sdtPr>
      <w:sdtContent>
        <w:p><w:pPr><w:pStyle w:val="TOC1"/></w:pPr><w:r><w:fldChar w:fldCharType="begin" w:dirty="true"/><w:instrText xml:space="preserve"> TOC \\o "1-3" \\h \\z \\u </w:instrText><w:fldChar w:fldCharType="separate"/></w:r><w:r><w:t>目录（打开文档时自动更新）</w:t></w:r></w:p>
        ${cached}
        <w:p><w:r><w:fldChar w:fldCharType="end"/></w:r></w:p>
      </w:sdtContent>
    </w:sdt>`).root[0];
}

const tocChildren = [
  new Paragraph({ heading: HeadingLevel.HEADING_1, alignment: AlignmentType.CENTER, spacing: { after: 240 }, children: [new TextRun({ text: "目　录", font: FONT_BODY, bold: true, size: 36 })] }),
  tocField(),
];

// 第一章
const ch1 = chapter1Children(comments);
// 第二章（批注 id 从 ch1 之后继续）
const ch2 = chapter2Children(comments, comments.length + 1);

const bodyChildren = [...tocChildren, ...ch1, ...ch2];

const commentObjs = comments.map((c) => ({
  id: c.id,
  author: "博智安全科技股份有限公司",
  initials: "BZ",
  date: new Date("2026-08-17T09:00:00"),
  children: commentContent(c.text),
}));

const doc = new Document({
  features: { updateFields: true },
  numbering: { config: [numberingConfig] },
  comments: { children: commentObjs },
  creator: "博智安全科技股份有限公司",
  title: "江苏交易场所登记结算有限公司网络入侵检测防御系统及配套安全服务项目技术标",
  styles: {
    default: {
      heading1: {
        paragraph: { outlineLevel: 0, spacing: { before: 340, after: 330, line: 578, lineRule: LineRuleType.AUTO } },
        run: { font: { ascii: "DengXian", hAnsi: "DengXian", cs: "DengXian", eastAsia: "SimHei" }, bold: true, size: 32, color: "000000" },
      },
      heading2: {
        paragraph: { outlineLevel: 1, spacing: { before: 260, after: 260, line: 415, lineRule: LineRuleType.AUTO } },
        run: { font: { ascii: "DengXian Light", hAnsi: "DengXian Light", cs: "DengXian Light", eastAsia: "SimHei" }, bold: true, size: 28, color: "000000" },
      },
      heading3: {
        paragraph: { outlineLevel: 2, spacing: { before: 260, after: 260, line: 415, lineRule: LineRuleType.AUTO } },
        run: { font: { ascii: "DengXian Light", hAnsi: "DengXian Light", cs: "DengXian Light", eastAsia: "SimHei" }, bold: true, size: 28, color: "000000" },
      },
      heading4: {
        paragraph: { outlineLevel: 3, spacing: { before: 280, after: 290, line: 377, lineRule: LineRuleType.AUTO } },
        run: { font: { ascii: "DengXian Light", hAnsi: "DengXian Light", cs: "DengXian Light", eastAsia: "SimHei" }, bold: true, size: 28, color: "000000" },
      },
      heading5: { run: { color: "000000" } },
      heading6: { run: { color: "000000" } },
      hyperlink: { run: { color: "000000" } },
    },
    paragraphStyles: [
      { id: "0-正文", name: "0-正文", basedOn: "Normal", next: "Normal", quickFormat: true,
        paragraph: { alignment: AlignmentType.JUSTIFIED, spacing: { line: 300, lineRule: LineRuleType.AUTO }, indent: { firstLineChars: 200 } },
        run: { font: { ascii: "Times New Roman", hAnsi: "Times New Roman", cs: "Times New Roman", eastAsia: "幼圆" }, size: 28 } },
      { id: "0-图格式", name: "0-图格式", basedOn: "Normal", quickFormat: true,
        paragraph: { alignment: AlignmentType.CENTER },
        run: { font: { ascii: "Times New Roman", hAnsi: "Times New Roman", cs: "Times New Roman", eastAsia: "幼圆" }, size: 24 } },
      { id: "0-图下标题", name: "0-图下标题", basedOn: "Normal", quickFormat: true,
        paragraph: { alignment: AlignmentType.CENTER, spacing: { line: 300, lineRule: LineRuleType.AUTO } },
        run: { font: { ascii: "Times New Roman", hAnsi: "Times New Roman", cs: "Times New Roman", eastAsia: "幼圆" }, size: 28, color: "000000" } },
    ],
  },
  sections: [
    { properties: { page: { margin: { top: 1440, bottom: 1440, left: 1440, right: 1440 } } }, children: coverChildren },
    {
      properties: {
        page: { margin: { top: 1440, bottom: 1440, left: 1440, right: 1440 }, pageNumbers: { start: 1 } },
      },
      headers: {
        default: new Header({
          children: [centerPara(run("江苏交易场所登记结算有限公司网络入侵检测防御系统及配套安全服务项目技术标", { size: 18, color: "000000" }), { spacing: { after: 0 } })],
        }),
      },
      footers: {
        default: new Footer({
          children: [centerPara(new TextRun({ children: [PageNumber.CURRENT], font: FONT_BODY, size: 20 }), { spacing: { after: 0 } })],
        }),
      },
      children: bodyChildren,
    },
  ],
});

const buffer = await Packer.toBuffer(doc);
fs.writeFileSync(outputPath, buffer);
console.log("written:", outputPath, "comments:", commentObjs.length);
