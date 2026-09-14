---
name: drawio2vsdx
description: Convert draw.io diagrams (.drawio) into Visio .vsdx or Visio-friendly SVG by driving the draw.io desktop CLI plus Visio COM automation. Use when the user wants to open, convert or hand off a draw.io/drawio diagram to Microsoft Visio (drawio 转 visio, drawio 转 vsdx, 导出成 Visio 格式, Visio 打开 drawio 文件, 把流程图给客户改成 Visio), when Visio shows garbled or displaced labels after such a conversion (中文乱码, 文字跑到左上角, 文字丢失, 文本框变空白), or when several .drawio files must be converted in one go (批量转换 drawio, 批量导出 vsdx, 多页 drawio 导出). Do NOT use it to author new diagrams — that is the `drawio` skill — and it does not do the reverse direction (vsdx → drawio).
version: 1.0.0
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
```

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

## 三个坑（本技能已内建处理）

1. **文字丢失 / 跑到左上角 / 中文乱码**：draw.io 有些版本把文字写成
   `<switch><foreignObject>(XHTML)</foreignObject>…</switch>`，Visio 不认 foreignObject 这一支，
   于是标签要么消失、要么挤成一坨。`convert` 出 vsdx 前会自动把这类文本重写为普通 `<text>`
   （有兜底 text 元素就沿用其坐标，没有就按 foreignObject 框中心合成）。
   本机 draw.io v29.0.3 已经直接输出 `<text>`，这步是防御性空转；老版本或别人给的 SVG 会命中。
2. **多页只导了第一页**：draw.io CLI 的 `-a/--all-pages` 只对 PDF 有效，SVG 必须按页号循环 —— 这就是 `--all-pages` 的实现方式。
3. **转完在 Visio 里选不中单个框**：Visio 把整张图作为一个组合导入。`Ctrl+Shift+U`（或右键 → 组合 → 取消组合）解开后即可单独编辑；文字此时已是原生文本。

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
| Microsoft Visio | 只在出 vsdx 时需要。查 `C:\Program Files\Microsoft Office\root\Office16\VISIO.EXE`，可 `VISIO_EXE` 覆盖 |
| pywin32 | `python -m pip install pywin32`；仅 vsdx 模式需要，`fix-svg` 不用 |

没有 Visio 时的替代路径：`--mode svg` 出 SVG，再在 Visio 里「打开 / 插入 → 图片 → SVG」手动导入，效果等价（只是多一步点击）。

## 非目标

- 不生成新图（那是 `drawio` 技能的事）
- 不做 vsdx → drawio 反向转换
- 不保证样式像素级一致：字体、渐变、阴影、自定义箭头在 SVG→Visio 途中可能被简化；**文本内容**才是本技能的保证项

## 文件

- `scripts/drawio2vsdx.py` —— 全部实现（doctor / convert / verify / fix-svg），纯标准库 + pywin32，可直接当 CLI 用
