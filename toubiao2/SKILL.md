---
name: toubiao2
description: 网络安全行业投标技术方案制作。当用户需要撰写投标技术方案、生成系统详细设计文档、响应招标技术指标、或提到"投标""技术方案""招标""写方案""标书"时使用。产出为系统详细设计方案docx，按"平台→设备→模块→子模块"四级结构组织，每个子模块含指标响应论述+功能截图+展开点+技术原理图。
---

# 投标技术方案制作

将招标技术指标转化为系统详细设计方案docx。

## 输入处理

1. 用户提供技术参数/技术指标文件（通常为docx表格）
2. 指标按**平台（项目名称）-设备-模块-子模块**四级组织
3. 如果指标文件中缺失平台名称，询问用户；模块按子模块功能自行聚合

## 文档结构

**标题层级：**
- H1: 第一章 XX平台
- H2: 一、功能设计
- H3: 1. XX设备（多设备时按1/2/3顺序编号）
- H4: (1) 模块组成
- H5: ①XX模块（**每个设备独立从①重新编号**）
- H6: 1)XX子模块（模块内独立编号，跨模块重置）

**子模块结构（5段式）：**
1. 概述段落（定位、对标指标）
2. 功能截图（题注=子模块名称）
3. 指标响应论述d1（技术细节展开，**不加COMMENT**）
4. 指标改写段（原文换个方式阐述，保留全部关键字和数字，**COMMENT批注选中此段**）
5. 补充论述d2（辅助技术说明）
6. 展开点×3（段落+技术原理图，无标题无序号）

## 各层级写法

### 设备概述：一段话，**要讲卖点**，突出设备优势。
### 模块：一段话。配Mermaid架构图（LR横向，2层模块→子模块）。
### 子模块：概述→截图→论述+COMMENT→展开点+原理图。

## 界面设计规范

### 四步设计流程

| 步骤 | 工具 | 动作 | 产出 |
|------|------|------|------|
| 1. 建立规范 | gral-frontend-skill | `/user:magistero teach` | `.design-context.md` |
| 2. 匹配风格 | UI/UX Pro Max (SKILL) | `python skills/ui-ux-pro-max/scripts/search.py "<query>" --design-system -p "项目名"` | 配色+字体+风格 |
| 3. 生成页面 | frontend-design (SKILL) | 输入token+布局+指标上下文 | HTML界面 |
| 4. 审查打磨 | Impeccable (SKILL) | `critique` → `polish` | 高质量界面 |

### 设计Token（UI/UX Pro Max推荐）

```
主蓝: #1E40AF  辅蓝: #3B82F6  强调琥珀: #D97706
成功绿: #059669  危险红: #DC2626
背景: #F8FAFC  表面: #FFFFFF  边框: #DBEAFE
字体: Fira Code(标题) + Fira Sans(正文)，fallback用Microsoft YaHei/Consolas
```

### 布局差异化

- **禁止顶部雷同的4数字banner**：每个子模块顶部按指标特征设计
- **连续子模块不用相同模板**：同一模块内用不同布局骨架
- **模块内5种骨架轮换**（v%5=0~4）：卡片网格+图表、表格+侧详情、纯表格+统计卡、双栏面板+筛选器、进度条+环形图+时间线
- **分析展示模块专用**（模块6）：3种可视化密集型仪表盘（4环形图+柱状图+攻击地图SVG+告警滚动+饼图+趋势线+统计表）
- 攻击地图使用**SVG世界地图轮廓+飞线+脉冲攻击源点**，禁止占位文字
- **截图前必须删除旧截图**（screenshot函数有缓存检查），否则改动不生效
- 白底纯白，系统字体，不依赖Google Fonts CDN

## COMMENT批注机制

- **批注位置**：COMMENT必须加在**指标改写段**（第4段），不是d1论述段（第3段）
- **sid→okey精确映射**：子模块sid与实际指标编号需用映射表
  ```python
  sid_to_okey = {'10':'d11','11':'d12',...}  # sid≠指标号时纠正
  ```
- **多设备ORIG分离**：不同设备使用不同ORIG前缀避免冲突
  - Device 1 (诱捕设备): `d1-d21`
  - Device 2 (扫描设备): `s1-s33`  
  - Device 3 (挖掘平台): `p1-p21`
- **融合指标**：子模块合并多指标时（如设备1子模块6融合d6+d10），需为每个指标单独加一段改写+独立COMMENT
- 批注内容：招标指标原文完整抄录，含序号，一字不差
- 批注作者："技术对标"
- 审查：`verify_comments.py`（存在性/位置/逐字比对）

## 图片审查机制

`verify_images.py` 检查三项：
1. **空白图**：文件<500字节
2. **重复图**：同MD5出现多次（绝对禁止）
3. **过度使用**：同一rId引用>3次

原理图匹配优先级：专属子模块图 > 模块级图 > **不插入**（绝不回退arch架构图）

## 多设备生成架构

多设备项目需注意以下关键点：

**SID偏移**：不同设备的子模块SID需偏移避免冲突
- 设备1 SID保持原样（如1-20）
- 设备2 SID = 原SID + 设备1最大SID
- 设备3 SID = 原SID + 设备1最大SID + 设备2最大SID

**ORIG分离**：不同设备使用不同前缀
```python
# Device 1: d1-d21, Device 2: s1-s33, Device 3: p1-p21
if '漏洞挖掘平台' in device: okey = f'p{num}'
elif '漏洞扫描' in device: okey = f's{num}'
else: okey = f'd{num}'
```

**H5编号独立**：每个设备的模块从①重新编号
```python
if mod_num <= 6: c = circled[mod_num - 1]       # 设备1/2: ①-⑥
else: c = circled[mod_num - 7]                     # 设备3: ①-④独立
```

**generate()结构**：每个设备的概述+模块组成描述+子模块循环紧密编排在一起，不要先写所有设备概述再写子模块。

**COMMENT查找**：okey前缀决定用哪个ORIG字典
```python
orig_dict = DEV1_ORIG if okey.startswith('d') else ORIG
```

## 架构图与原理图

- **Mermaid.js渲染**（`mermaid_diagrams_v2.py`）：flowchart LR横向，neutral主题+蓝色系
- SVG→PNG转换：`_svg2png_playwright(svg_path, png_path)` 接收SVG文件路径
- Mermaid HTML渲染：Playwright截图`.mermaid svg`元素，`page.goto`超时45s
- 模块级原理图命名：`arch_m{mod_num}`（架构图）、`m{mod_num}_p{exp_idx}`（原理图）
- 展开点优先匹配专属图`m{mod_num}_p{idx}`，回退到模块架构图`arch_m{mod_num}`
- 原理图缓存在`output/svg/`，按key命名，存在且>500字节则跳过重新渲染

## 写作规范

**禁止**："在技术实现层面"、"在XX方面"、英文引号`""`和`''`、箭头→、性能数字、招标指标编号引用
**强制**："其中包括XX、XX、XX等"、"通过XX技术/方法/手段，实现XX能力/效果"、中文引号`""`
**指标改写**：将原文换一种表述方式（如"支持XXX"→"系统支持XXX"），严格保留关键字和数字（少于/不低于/≥/≤等），禁止"在XX方面"前缀

## 字体与格式

| 元素 | 字体 | 大小 | 行距 |
|------|------|------|------|
| 标题(H1-H6) | 宋体加粗 | **四号(14pt)** | 1.5 |
| 正文 | 宋体 | 小四(12pt) | 1.5，首行缩进2字符 |
| 题注 | 宋体 | 小五(10pt) | 居中 |
| 页边距 | A4，上下2.54cm，左右3.18cm |

**标题字体关键实现**：`_add_heading`中必须在**run级别**显式设置`w:eastAsia`、`w:ascii`、`w:hAnsi`字体，不能仅依赖Style样式继承，否则Word会回退到MS Gothic等非预期字体。

```python
def _add_heading(doc, text, level):
    p = doc.add_paragraph(style=f'Heading {level}')
    p.clear()
    run = p.add_run(text)
    run.font.name = FONT_NAME_H  # 宋体
    run.font.size = FONT_SIZE_H  # 四号14pt
    run.font.bold = True
    rPr = run._element.get_or_add_rPr()
    rFonts = OxmlElement('w:rFonts')
    rFonts.set(qn('w:eastAsia'), FONT_NAME_H)
    rFonts.set(qn('w:ascii'), FONT_NAME_H)
    rFonts.set(qn('w:hAnsi'), FONT_NAME_H)
    rPr.insert(0, rFonts)
    return p
```

## 关键脚本

`scripts/toubiao2/`：
- `docx_utils.py`：H1-H6/BD/IMG/COMMENT/inject_comments/reset_seq_counter/_svg2png_playwright。`_add_heading`必须在run级别显式设置东亚字体。
- `indicator_data.py/2/3`：sm()数据注册+设备1（诱捕设备）20子模块结构化内容
- `generate_full_docx.py`：单设备版（诱捕设备）20子模块生成
- `generate_docx_v2.py`：2设备版（扫描+挖掘）54子模块生成
- `generate_docx_v3.py`：**3设备全量版**（诱捕+扫描+挖掘）74子模块生成，含指标改写+COMMENT重定位+多设备ORIG分离+SID偏移+英文引号清理
- `mermaid_diagrams.py`：设备1诱捕设备25张Mermaid图
- `mermaid_diagrams_v2.py`：设备2/3共39张Mermaid图（10模块架构图+29原理图）
- `verify_comments.py`：批注审查（存在性/位置/逐字比对）
- `verify_images.py`：图片审查（空白/重复/过度使用）