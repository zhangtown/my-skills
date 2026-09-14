---
name: drawio2vsdx
description: Convert draw.io diagrams (.drawio) into Visio .vsdx or Visio-friendly SVG by driving the draw.io desktop CLI plus Visio COM automation, and insert the result into a Word/WPS 文字 document (.docx) as an editable Visio object. Use when the user wants to convert or hand a diagram to Microsoft Visio (drawio 转 visio, drawio 转 vsdx, 导出成 Visio 格式, Visio 打开 drawio 文件), when a diagram must be placed into a Word 文档 / WPS 文字文档 (在 word 里插入 visio 流程图, 把流程图插进文档, 文档插图, 报告里加流程图, 一键插入), when Visio shows garbled or displaced labels after such a conversion (中文乱码, 文字跑到左上角, 文字丢失, 文本框变空白), or when several diagrams must be converted in one go (批量转换 drawio, 批量导出 vsdx, 多页 drawio 导出). Do NOT use it to author new diagrams — that is the `drawio` skill — and it does not do the reverse direction (vsdx → drawio).
version: 1.3.0
---

# drawio → Visio (.vsdx) 转换

把 `.drawio` 变成 Visio 能打开、且**文字仍是可编辑文本**的 `.vsdx`。

```
foo.drawio  --(draw.io 桌面版 CLI)-->  foo.svg  --(Visio COM)-->  foo.vsdx
```

## 快速开始

```bash
S=~/.skills-manager/skills/drawio2vsdx/scripts/drawio2vsdx.py

python "$S" doctor                    # 先体检：draw.io / Visio / pywin32
python "$S" convert 图.drawio          # 图.vsdx（同目录）
python "$S" convert 图.drawio -o out --keep-svg
python "$S" convert a.drawio b.drawio 目录/ --outdir out   # 批量；目录需加 --recursive
python "$S" convert big.drawio --all-pages                 # 多页 → big.p1.vsdx, big.p2.vsdx
python "$S" verify out/图.vsdx         # 验收：打印形状树 + 文本，证明文字可编辑
python "$S" fix-svg in.svg -o out.svg  # 仅修 SVG 文本（不碰 Visio）

# 一键插进 WPS 文字 / Word 文档（默认可编辑的 Visio 对象）
python "$S" word 图.drawio -d 报告.docx --at "{{流程图}}" --width-cm 12 --caption "图1  处理流程"
```

### 推荐链路（draw.io v29 起，务必先 prepare 再 convert）

```bash
P=~/.skills-manager/skills/drawio2vsdx/scripts/prepare_svg.py

# 1) 先修 SVG：重建文字坐标 + 扁平化 + 尺寸改 pt
python "$P" raw.svg ready.svg --drawio 原文件.drawio
# 2) 再转 Visio
python "$S" convert ready.svg --mode vsdx --keep-svg
# 3) 验收（并且先杀残留 Visio 进程，否则导出是缓存）
python "$S" verify ready.vsdx
```

`prepare_svg.py` 处理的是 SKILL.md「四个真实缺陷」里的 A/B/C；
缺陷 D（残留 Visio 进程返回缓存导出）需自己杀进程：

```powershell
Stop-Process -Name VISIO -Force -ErrorAction SilentlyContinue
```

`--shrink 0.92` 可以在文字恰好占满框宽时留一点余量，避免 Visio 边缘折行。

## 插进 WPS 文字 / Word 文档（一键）

```bash
python "$S" word 图.drawio -d 报告.docx                      # 插到文末
python "$S" word 图.drawio -d 报告.docx --at "{{流程图}}"      # 替换掉这个标记（推荐）
python "$S" word 图.drawio -d 报告.docx --at end --in-place   # 原地写回（自动先存 .bak）
python "$S" word 图.vsdx   -d 报告.docx --mode picture        # 只放矢量图，不要可编辑对象
```

| 开关 | 作用 |
|---|---|
| `-d/--doc` | 目标 `.docx`（必填） |
| `--at` | `end`（默认）/ `start` / **一段标记文本**，写成标记时会把那段文字替换成图（自建段落扫描，不用 Range.Find，WPS 下稳） |
| `--mode ole` | 默认。插入 **可双击编辑的 Visio 对象**，文档里存 `word/embeddings/oleObject1.bin`（ProgID `Visio.Drawing.15`）+ 一张 `image1.emf` 矢量显示图 |
| `--mode picture` | 只插矢量 EMF 图片（`.vsdx` 输入不支持此模式） |
| `--width-cm` | 按宽度缩放（自动保持长宽比）并居中 |
| `--caption` | 图下自动加一行居中图题 |
| `-o` / `--in-place` | 输出到 `原名_插图.docx`（默认）/ 原地覆盖（先备份 `原名.bak.docx`） |

**推荐工作流**：在文档里想放图的位置打一行 `{{流程图}}`，然后一条命令 —— 标记被图替换，其余正文一字不动。

**本机事实（2026-09 实测）**：这台机器**没装 Microsoft Word**（`Word.Application` 的 LocalServer32 为空、各处无 `WINWORD.EXE`），`.docx` 默认由 **WPS Office 12.1.0.25865**（`C:\Program Files\WPS Office\12.1.0.25865\office6\wps.exe`）打开。WPS 文字通过 `KWPS.Application` 提供 Word 兼容 COM（自己报 `Name='Microsoft Word' Version='12.0'`），`InlineShapes.AddOLEObject` / `AddPicture` 都可用 —— 脚本先试 `KWPS.Application` 再退到 `Word.Application`，两边都能跑。Visio 是微软正版 16.0，负责 SVG→VSDX 与 SVG→EMF。

**验收看什么**（脚本每次自动打印）：

```
[ok]   embedded Visio object: Visio.Drawing.15, word/embeddings/oleObject1.bin 15,360 B — double-click opens Visio
       media word/media/image1.emf 9,704 B
[ok]   marker '{{流程图}}' no longer in the text (replaced by the diagram)
```

双击那个对象就回 Visio 编辑，改完关闭，文档里的显示图自动更新。

## 为什么是这条链路（不是别的）

| 做法 | 结论 |
|---|---|
| draw.io CLI 直接导出 vsdx | **不可能**。CLI 只支持 `pdf png jpg svg xml`（`drawio.exe --help` 实测，v29.0.3） |
| 拿 `.drawio` 里的 XML 直接给 Visio | Visio 不认 mxGraph XML，只能靠 SVG 这种它原生支持的矢量格式中转 |
| 先转 PNG 再插入 | 文字变成像素，Visio 里改不了字 —— 除万不得已不要用 |
| **本技能**：CLI 导 SVG → Visio COM 导入并另存 | Visio 把 SVG 当**原生形状**导入（组 → 子形状 → 文本形状），文字保持可编辑、可搜索 |

实测（本机）：一张含中文的 `.drawio` → `.vsdx` 13.9 KB，结构 10 个节点，
`verify` 打印出 `text='开始'`、`text='处理 & 校验'` —— 确认是文本形状而非图片。

## 命令参考

| 命令 | 作用 |
|---|---|
| `doctor` | 检查 draw.io exe / Visio exe / pywin32，给出可用模式结论（缺失 Visio 时降级为只出 SVG） |
| `convert INPUT...` | 主命令。`INPUT` 可以是文件或目录 |
| `verify FILE.vsdx` | 只读打开 vsdx，递归打印 `形状名 + text=`，用来证明没有退化成图片 |
| `fix-svg IN.svg` | 把 `<switch><foreignObject>` 文本重写回 `<text>`（见下方坑 1） |

`convert` 常用开关：

- `-o/--outdir DIR` 输出目录（默认与输入同目录）
- `--mode auto|vsdx|svg` 默认 auto：有 Visio + pywin32 就出 vsdx，否则只出 SVG
- `-p/--page N` 单页，**1-based**（与 draw.io CLI 的 `--page-index` 一致）
- `--all-pages` 每页一个文件，命名 `名字.pN.vsdx`
- `--theme light|dark|auto` 默认 `light` —— Visio 是浅色画布，dark 主题的浅色字会看不清
- `--keep-svg` 保留中间 SVG（默认转完就删）
- `--embed-diagram` 把 drawio XML 塞进 SVG，之后还能拖回 draw.io 编辑
- `--visible` 显示 Visio 窗口（默认隐藏，只闪一下）
- `--recursive` 目录输入时递归子目录

## 坑（本技能已内建处理 + 使用前必读）

1. **文字丢失 / 跑到左上角 / 中文乱码**：draw.io 有些版本把文字写成
   `<switch><foreignObject>(XHTML)</foreignObject>…</switch>`，Visio 不认 foreignObject 这一支，
   于是标签要么消失、要么挤成一坨。`convert` 出 vsdx 前会自动把这类文本重写为普通 `<text>`
   （有兜底 text 元素就沿用其坐标，没有就按 foreignObject 框中心合成）。
2. **多页只导了第一页**：draw.io CLI 的 `-a/--all-pages` 只对 PDF 有效，SVG 必须按页号循环 —— 这就是 `--all-pages` 的实现方式。
3. **转完在 Visio 里选不中单个框**：Visio 把整张图作为一个组合导入。`Ctrl+Shift+U`（或右键 → 组合 → 取消组合）解开后即可单独编辑；文字此时已是原生文本。

### ⚠️ draw.io v29.0.3 实测的四个真实缺陷（2026-09 补充，务必先处理）

这版 draw.io 的 SVG 导出**不是**坑 1 描述的 `<switch>` 形态，而是：

```xml
<g data-cell-id="n4"><g transform="translate(0.5,0.5)"><rect x="6" y="26" width="69.36" height="18"/></g>
  <g><g><text x="0.0" y="0.0" text-anchor="middle" font-family="Helvetica" font-size="12">标签</text></g></g></g>
```

- **缺陷 A｜文字坐标是假的**。每个 `<text>` 都是 `x="0.0" y="0.0"`，且 `font-family`/`font-size`
  也不是你在 `.drawio` 里设的值。本技能的 `fix_foreign_object` 若无 `<switch>` 可改就会原样放过，
  结果所有文字堆在原点（现象：**框是空的**）。
  → **对策**：转换前**按同一 cell 的 `<rect>` 几何重建 `<text>`**（居中 `x=rx+rw/2`；
  泳道标题等 `align=left` 的用 `x=rx+2, text-anchor=start`；字号取 `.drawio` 里该
  `mxCell` 的 `fontSize`）。
- **缺陷 B｜嵌套组导致折行（最隐蔽）**。`<g data-cell-id>` 会让 Visio 生成**按父级比例缩放**的
  子形状，字号被算歪 → 中文全部折行（"统一接入描/述"）。
  → **对策**：**扁平化 SVG** —— 抽掉所有 `<g data-cell-id>`，只把 `rect`/`text`/`path`
  平铺到根（drawio 这些组没有额外 transform，坐标已是绝对值）。扁平后 Visio 存的是
  真实 `Char.Size`（如 `0.114 in = 8.21 pt`）与真实 `Width`，折行消失，
  且 `top-level shapes` 从 1 变成元素个数。
- **缺陷 C｜根尺寸写 `px` 会被按 96dpi 折算**。`width="424px"` → Visio 页面只有 318pt（×0.75）。
  → **对策**：根 `<svg>` 的 `width`/`height` 直接写 **`pt`**（`width="424pt"`），页面即设计尺寸。
- **缺陷 D｜残留 `VISIO.EXE` 进程返回缓存导出**。导出文件字节数完全一样，会让人误判"改动无效"。
  → **对策**：跑前 `Stop-Process -Name VISIO -Force`（或 `taskkill /IM VISIO.EXE /F`）。

**别再用** `shape.CellsSRC(3,0,0).FormulaU="X pt"` / `shape.Characters.CharProps(0, fs)` /
`AddRow` 去 Visio 里改字号 —— 在 SVG 导入的**嵌套组**上这些都写不进去（导出的 XML 里根本
不出现 `Char.Size`）。根因是缺陷 B 的嵌套缩放，正确解法是扁平化，不是换 API。

## 验收标准（每次转换后都跑）

```bash
python "$S" verify out/图.vsdx
```

- 期望：`text-bearing shape(s)` ≥ 图里的标签数，且节点树里能看到中文原文。
- `text-bearing = 0` 说明文字没进来（通常是坑 1），可 `--keep-svg` 保留 SVG 后跑 `fix-svg` 再重导。
- 只关心"能不能打开"时，看文件大小：几 KB 级说明是矢量形状；上百 KB 且很大才像位图。

## 依赖

| 依赖 | 说明 |
|---|---|
| draw.io Desktop | 提供 CLI。默认查 `C:\Program Files\draw.io\draw.io.exe`，可用环境变量 `DRAWIO_EXE` 覆盖 |
| Microsoft Visio | 出 vsdx / EMF 时需要。查 `C:\Program Files\Microsoft Office\root\Office16\VISIO.EXE`，可 `VISIO_EXE` 覆盖 |
| WPS 文字 或 MS Word | `word` 子命令用。WPS 走 `KWPS.Application`，MS Word 走 `Word.Application`，脚本自动选 |
| pywin32 | `python -m pip install pywin32`；vsdx / EMF / 文档插入都需要，`fix-svg` / `prepare-svg` 不用 |

**本机实测环境（2026-09）**：draw.io 29.0.3 + Visio 16.0 + pywin32 312（装在
`C:\Users\ELEX-ZT\.workbuddy\binaries\python\envs\default`）。该 venv 的 python 路径：
`...\envs\default\Scripts\python.exe`。从 Bash 调脚本时用**绝对路径**，
`cd xxx && python script.py` 在这个 shell 里 cwd 可能不生效。

没有 Visio 时的替代路径：`--mode svg` 出 SVG，再在 Visio 里「打开 / 插入 → 图片 → SVG」手动导入，效果等价（只是多一步点击）。

## 非目标

- 不生成新图（那是 `drawio` 技能的事）
- 不做 vsdx → drawio 反向转换
- 不保证样式像素级一致：字体、渐变、阴影、自定义箭头在 SVG→Visio 途中可能被简化；**文本内容**才是本技能的保证项

## 文件

- `scripts/drawio2vsdx.py` —— 全部实现（doctor / convert / verify / fix-svg / word），纯标准库 + pywin32，可直接当 CLI 用
- `scripts/prepare_svg.py` —— **转换前的 SVG 预处理**（重建文字坐标 / 扁平化 / px→pt / 去 light-dark），
  针对 draw.io v29 的缺陷 A/B/C。用法见上方「推荐链路」
