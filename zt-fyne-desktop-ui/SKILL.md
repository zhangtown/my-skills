---
name: zt-fyne-desktop-ui
description: 设计与改造 Fyne 桌面客户端（Windows 优先）的界面——设计令牌、间距与卡片布局、悬停/气泡交互、无边框窗口与系统投影、构建发布与像素级验证。当用户要动桌面客户端界面时用它：调配色/字号/圆角/间距，加卡片、列表、按钮，加悬停提示，做无边框窗口与自绘标题栏，嫌"窗口没有阴影/边界看不见/看着一般"，要打包发布，或者要确认界面改动到底有没有生效——即使对方没说出"Fyne""客户端""UI""设计"这些词也要用。也用于评审、重构已有的 Fyne 客户端界面，或回答"这块界面该怎么设计"。
---

# Zt · Fyne 桌面客户端界面设计与改造

这套规则的参考实现是 RemoteNet 客户端（`D:\ProgramData\projects\ZtRemoteNet`，Go + Fyne，
Windows 优先）：浅灰底 + 白浮卡 + 唯一暗红主色 + 自绘顶栏 + DWM 系统投影。
下面的每条规则背后都堆着被实测或用户否决过的坑——照做能少走一遍。

先看这四件事，别急着写代码：

1. **令牌有没有现成的？** 颜色、字号、圆角、间距都只有一个出处，改之前先找到它。
2. **现有测试会不会拦你？** `cmd/gui/*_test.go` 是设计约束的可执行版本（卡片余量、标签列宽、
   菜单字号、底栏提示……）。改完必须跑。
3. **验收标准是像素还是窗口样式？** "看着差不多"不算：间距要量像素、投影要采样窗外像素、
   窗口样式要读 `GWL_STYLE`。代码写完不等于生效（下面有整整一节讲为什么）。
4. **用户没让你动的别动。** 这轮对话里唯一一次被明确否掉的就是"顺手放大托盘右键菜单"——
   用户问"啥时候让你改托盘菜单了？"。改动范围要守住需求边界。

## 先读哪个文件

| 要做的事 | 读 |
|---|---|
| 配色 / 字号 / 圆角 / 间距 / 悬停态 / 禁用态 | `references/design-tokens.md` |
| 版面结构、卡片、标签列、窗口尺寸策略、悬停气泡、底栏反馈 | `references/layout-and-interaction.md` |
| 窗口边框、自绘标题栏、拖动缩放、窗口阴影/圆角 | `references/windows-chrome.md` |
| 构建、打包、换掉正在跑的 exe、验证改动真的生效 | `references/build-and-verify.md` |

本技能只覆盖"怎么把界面做对"。要写 Fyne 控件/布局的通用 API 用法，配 `fyne-gui-dev-cn` 一起用。

## 四条硬规则（每条都踩过）

### 一、改样式只改令牌，不写魔法值

色板、字号、圆角、行距集中在一处（RemoteNet 是 `cmd/gui/theme.go` + `cmd/gui/ui.go`
的常量块）。界面代码里出现 `color.NRGBA{...}` 字面量或 `fyne.NewSize(13, ...)` 这类数字，
就是下次不一致的来源。要加新色先问：它是不是现有某个令牌的别名？（`colBarBg = colBg` 就是
这么来的——原来是 `#E9EBEE`，与版面底色差一档，视觉上多出一条横带，被否了。）

### 二、间距只有两个旋钮

- **行距 = `theme.Padding()` = 5**（容器自动加的），要改"卡片之间松紧"改它会影响全局，
  所以卡片内部用 `cardPadV/cardPadH` 补差额，不要在 VBox 里塞占位对象。
  插一个"3px 的占位格"看起来能得到 8px 缝隙，实测得到的是 13px（占位对象自带一整行行距）。
- **特殊间距用"槽位补差额"的表达方式**：想要深色状态卡与下一张卡之间是 8px，而 VBox 只给 5px，
  就在槽位的 padding 里补 `extra = 目标 − theme.Padding()`（RemoteNet 的 `heroSlot`）。
  这样"目标值"在代码里是唯一且可读的，而不是散落在布局代码里的魔法数字。

### 三、交互态必须"看得出层次"

- 悬停**不要用不透明浅灰去覆盖**：红 CTA 被罩成灰会像"按钮失效"。改成**底色加深**
  （半透明黑 14% 叠加，RemoteNet 走 vendored 的 `ButtonHoverDeepColorName`）。
- 禁用态要比可用态**更淡**，不能更显眼（原来的 `#E7E9EC` 比可用态还亮，层级倒挂）。
- 长提示不要常驻版面（会把卡片撑变形），走**悬停气泡**：悬停才出现、自动折行、不占布局、
  不改变窗口尺寸（RemoteNet 的 `cmd/gui/tips.go`：`newTipButton` / `newTipLabel` / `hoverTip`）。

### 四、窗口尺寸由内容与用户共同决定，程序不许自作主张

- **长提示变长变短，绝不改窗口尺寸**（用户原话）。`fitBody()` 只在内容装不下时加高，
  绝不下缩、不动宽度——用户手拖过的高度是他要的。
- 默认宽度 = 内容的最小宽度（`Content().MinSize().Width`），不要写死一个"看着舒服"的数字。
- 高度 = 内容 + 底部留白 + 固定底栏 + 顶栏，用一个函数算（`bodyMinHeight()`），
  别在多处各算一遍。

## Windows 窗口层：只走 DWM，不自绘

无边框窗口（`WS_POPUP`）**没有系统投影**，白底上窗口边界看不见。解法是给无边框窗口补
`WS_THICKFRAME` 并用 `WM_NCCALCSIZE` 把边框吃掉，让 DWM 按"有框窗口"给它画系统投影 +
Win11 圆角（`references/windows-chrome.md` 有完整代码位置与实测数据）。

**不要**用这些被实测否掉的做法：

| 做法 | 为什么不行 |
|---|---|
| 自绘 1px 描边 | 会把界面整体压深一档，用户明确否过 |
| 类样式 `CS_DROPSHADOW` | 只有右下 5px 硬边，左边/上边完全没有投影 |
| `DwmExtendFrameIntoClientArea(1,1,1,1)` | 客户区被内缩 7px，内容跟着缩水 |
| `DefWindowProc` 的移动循环做拖动 | 它是模态循环，会卡住 Fyne 事件循环，拖动时画面发花；改用 `SetWindowPos` |

## 改完怎么验收

```bash
cd <客户端仓库>
export PATH="$USERPROFILE/go-sdk/go/bin:$PWD/.toolchain/root/ucrt64/bin:$PATH"
go test ./cmd/gui/                       # 设计约束的可执行版本
go build -ldflags "-H windowsgui" -o dist/<pkg>/gui.exe ./cmd/gui
```

- 改了 vendored glfw 的 `.c` 之后，**必须** `go run ./tools/glfwmarker -write`，
  否则 Go 构建缓存不会重编（缓存只哈希 `.go`，看不到被 `#include` 的 C 源码）。
- 界面改动要看**像素**：`scripts/wininfo.ps1`（窗口/客户区尺寸、`GWL_STYLE`、类样式）、
  `scripts/gap_analyze.ps1`（卡片间距）、`scripts/shadow_probe.ps1`（白底 + 窗外 16px 采样）。
  三条都在 `references/build-and-verify.md` 有用法与坑。
- 想验证"某种窗口样式到底长什么样"，别改生产代码试探：用 `scripts/shadowlab/`（独立实验台，
  能一次跑出多种窗口样式的对比图和像素报告）。

## 参考实现里的对应文件（RemoteNet）

| 关注点 | 文件 |
|---|---|
| 设计令牌、主题 | `cmd/gui/theme.go` |
| 版面常量、槽位、标签列宽 | `cmd/gui/ui.go`（`labelGap` / `cardSlot` / `heroSlot` / `bodyPadBottom`） |
| 窗口尺寸策略 | `cmd/gui/app.go`（`bodyMinHeight` / `fitBody`） |
| 自绘顶栏、无边框、拖动缩放 | `cmd/gui/titlebar_windows.go` |
| 悬停气泡 | `cmd/gui/tips.go`、`cmd/gui/tappabletext.go` |
| 设计约束测试 | `cmd/gui/{cards,labels,menu,footbar,layout,tips,conns_cols}_test.go` |
| vendor 补丁 | `vendor/.../glfw/src/win32_window.c`、`vendor/fyne.io/fyne/v2/widget/button.go` 等 |
