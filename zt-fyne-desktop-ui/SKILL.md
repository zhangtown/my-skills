---
name: zt-fyne-desktop-ui
description: 固化并改造 Fyne 桌面客户端（Windows 优先）的**整套界面设计**——窗口形态（无边框/投影/圆角/标题栏）、版面结构（卡片/间距/尺寸策略）、每一个组件的形状与六种交互状态（按钮、输入框、下拉、勾选、列表、菜单、托盘、气泡、底栏提示）、鼠标悬停与按压反馈、光标、配色与字号令牌，以及构建发布与像素级验证。当用户要动桌面客户端界面时用它：调配色/字号/圆角/间距，加卡片、按钮、列表、弹层，加或改悬停效果，做无边框窗口与自绘顶栏，嫌"窗口没阴影/边界看不见/界面看着一般/交互不够精致"，要统一整体风格，要打包发布，或者要确认界面改动到底有没有生效——即使对方没说"Fyne""客户端""UI""设计"这些词也要用。也用于评审、重构已有客户端界面，或回答"这块界面该怎么设计"。
---

# Zt · Fyne 桌面客户端界面设计与改造

参考实现是 RemoteNet 客户端（`D:\ProgramData\projects\ZtRemoteNet`，Go + Fyne，Windows 优先）：
浅灰底 + 白浮卡 + 唯一暗红主色 + 自绘顶栏 + DWM 系统投影。每条规则背后都堆着被实测或
被用户否决过的坑——照做能少走一遍。

**这套界面是一个整体，不是"若干卡片的集合"。** 用户明确纠正过一次："整个技能都围绕着卡片的
布局去设计……我这个技能是对整体界面的设计，包括按钮、风格、阴影、按钮的响应、鼠标悬浮上去的
效果，关于界面上的所有设计都固化一下。" 所以从下面五层入手，别只盯版面。

## 界面的五层，各读哪份文件

| 层 | 管什么 | 读 |
|---|---|---|
| 窗口层 | 无边框、系统投影、Win11 圆角、自绘标题栏、拖动/缩放热区、关闭=收托盘 | `references/windows-chrome.md` |
| 版面层 | 卡片、槽位与间距、标签列、窗口尺寸策略、滚动区与底部余量 | `references/layout-and-interaction.md` |
| 组件层 | **每个元素长什么样、多大、什么光标**：按钮族 / 输入族 / 容器族 / 顶栏族 / 反馈族 / 图形族 | `references/components.md` |
| 状态层 | **六态**：正常 / 悬停 / 按压 / 焦点 / 禁用 / 选中；悬停叠色公式、焦点圈策略、禁用可读性、气泡、动画禁令 | `references/interaction-and-states.md` |
| 令牌层 | 色板、字号阶、圆角、间距、菜单密度、加新样式的判断顺序 | `references/design-tokens.md` |
| 验收层 | 构建、打包、换掉正在跑的 exe、像素级与窗口样式验证 | `references/build-and-verify.md` |

本技能只覆盖"怎么把界面做对"。要写 Fyne 控件/布局的通用 API 用法，配 `fyne-gui-dev-cn` 一起用。

开动之前先过这四件事：

1. **令牌有没有现成的？** 颜色、字号、圆角、间距都只有一个出处，改之前先找到它。
2. **有没有同族组件可以抄？** 加新东西之前先在 `components.md` 里找同族模板——
   同族共用形状、尺寸、状态、光标，跨族的"新发明"就是不一致的开始。
3. **验收标准是像素还是窗口样式？** "看着差不多"不算：间距量像素、投影采样窗外像素、
   窗口样式读 `GWL_STYLE`。代码写完 ≠ 生效（见验收层）。
4. **用户没让你动的别动。** 唯一一次被明确否掉的就是"顺手放大托盘右键菜单"——
   用户反问"啥时候让你改托盘菜单了？"。改动范围守住需求边界。

## 六条硬规则（每条都踩过）

### 一、改样式只改令牌，不写魔法值

色板、字号、圆角、行距集中在一处（RemoteNet 是 `cmd/gui/theme.go` + `cmd/gui/ui.go` 的常量块）。
界面代码里出现 `color.NRGBA{...}` 字面量或 `fyne.NewSize(13, ...)` 这类数字，就是下次不一致的来源。
要加新色先问：它是不是现有某个令牌的别名？（`colBarBg = colBg` 就是这么来的——原来是 `#E9EBEE`，
与版面底色差一档，视觉上多出一条横带，被否了。）

### 二、间距只有两个旋钮

- **行距 = `theme.Padding()` = 5**（容器自动加的）。改"卡片之间松紧"改它会影响全局，
  所以卡片内部用 `cardPadV/cardPadH` 补差额，不要在 VBox 里塞占位对象——
  插一个"3px 的占位格"看起来能得到 8px 缝隙，实测得到的是 13px（占位对象自带一整行行距）。
- **特殊间距用"槽位补差额"表达**：想要深色状态卡与下一张卡之间是 8px 而 VBox 只给 5px，
  就在槽位 padding 里补 `extra = 目标 − theme.Padding()`（RemoteNet 的 `heroSlot`）。
  这样"目标值"在代码里唯一且可读，而不是散落在布局里的魔法数字。

### 三、每个可交互元素必须有六态，悬停靠叠色而非换色

- 悬停**不要用不透明浅灰覆盖**：红 CTA 被罩成灰会像"按钮失效"。改成**底色加深**
  （半透明黑 14% 叠加；RemoteNet 走 vendored 的 `ButtonHoverDeepColorName`）。
  同一条规则也适用于顶栏扁平按钮、菜单项、下拉项、列表行。
- **按压**要比悬停深一档（`#D8DCE1`），**选中/激活**要跟悬停区分开（`#DEE2E8`）。
- 禁用态要比可用态**更淡**，但**文字必须仍可读**（`#6B7280`，对白 4.6:1）——不能更显眼，也不能看不见。
- 焦点：**鼠标用户不要焦点环**（勾选框、单选框的焦点大圆是刻意设成透明的，别"修复"）；
  键盘可见性靠"项高亮"表达。
- **不加动画**：状态变化是瞬时的，这套界面的节奏是"即时反馈"。
- 长提示不要常驻版面（会把卡片撑变形），走**悬停气泡**：悬停才出现、自动折行、不占布局、
  不改变窗口尺寸（`cmd/gui/tips.go` 的 `newTipButton` / `newTipLabel` / `hoverTip`）。
- 给可点元素**顺手加 cursor**（`desktop.PointerCursor`）；缩放热区用对应的 resize 光标。

### 四、跨控件要"同族"，别自己发明

数据/命令类文字统一 **13 号等宽**（菜单项、下拉弹层、连接明细行、页签、底栏提示同字阶，
vendor 侧靠 `MenuTextSizeName` 保障，`gui/menu_test.go` 锁死）；正文 14、卡片标题加粗 14、
说明/气泡 12、状态标题 18 粗。圆角统一 **8**（卡片 10）。分隔线只有两级（发丝线 `#E2E4E8` /
边框 `#D5D8DD`）。加任何新元素前先回答："它属于哪一族？哪一族是它的模板？"

### 五、窗口尺寸由内容与用户共同决定，程序不许自作主张

- **长提示变长变短，绝不改窗口尺寸**（用户原话）。`fitBody()` 只在内容装不下时加高，
  绝不下缩、不动宽度——用户手拖过的高度是他要的。
- 默认宽度 = 内容的最小宽度（`Content().MinSize().Width`），不要写死一个"看着舒服"的数字。
- 高度 = 内容 + 底部留白 + 固定底栏 + 顶栏，用一个函数算（`bodyMinHeight()`），别在多处各算一遍。

### 六、反馈走底栏，决策才弹窗

- "操作完成/失败"这类**告知**一律走底栏 `footHint`（`✓` 绿 / `✗` 红 / `…` 灰），
  自动消失、不打断操作流、长文省略号且不撑宽窗口。
- 只有**需要用户决策**的事才弹对话框；破坏性操作（覆盖生成、删除配置）必须二次确认。
- 托盘菜单文案是主界面按钮的**镜像**（"连接"↔"断开连接"），互斥功能用 `Disabled` 表达，不要隐藏。

## Windows 窗口层：只走 DWM，不自绘

无边框窗口（`WS_POPUP`）**没有系统投影**，白底上窗口边界看不见。解法是给无边框窗口补
`WS_THICKFRAME` 并用 `WM_NCCALCSIZE` 把边框吃掉，让 DWM 按"有框窗口"给它画系统投影 +
Win11 圆角（代码位置与实测数据在 `references/windows-chrome.md`）。

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
- 想验证"某种窗口样式到底长什么样"，别改生产代码试探：用 `scripts/shadowlab/`
  （独立实验台，能一次跑出多种窗口样式的对比图和像素报告）。
- 新增视觉契约就补一个 `cmd/gui/*_test.go` 断言（间距、字号、不改窗口尺寸、位置对齐），
  让下次改动被测试拦住。

## 参考实现里的对应文件（RemoteNet）

| 关注点 | 文件 |
|---|---|
| 设计令牌、主题、vendor 补丁映射 | `cmd/gui/theme.go` |
| 版面常量、槽位、标签列宽、底栏提示 | `cmd/gui/ui.go`（`labelGap` / `cardSlot` / `heroSlot` / `bodyPadBottom` / `footHint`） |
| 窗口尺寸策略、状态与按钮联动 | `cmd/gui/app.go`（`bodyMinHeight` / `fitBody` / `setState`） |
| 自绘顶栏、无边框、拖动缩放 | `cmd/gui/titlebar_windows.go` |
| 交互状态与气泡 | `cmd/gui/tips.go`、`cmd/gui/tappabletext.go` |
| 菜单/下拉/勾选/单选的 vendor 补丁 | `vendor/fyne.io/fyne/v2/widget/{button,menu_item,menu,select,check,radio_item}.go` |
| 窗口投影/圆角的 vendor 补丁 | `vendor/github.com/go-gl/glfw/v3.4/glfw/glfw/src/win32_window.c` |
| 设计约束测试 | `cmd/gui/{cards,labels,menu,footbar,layout,tips,conns_cols}_test.go` |
| 品牌图形（圆点/托盘/应用图标） | `internal/brand/branding.go` |

本技能自带 5 个回归场景（`evals/evals.json`）与机械评分脚本，改进本技能时按
`references/build-and-verify.md` 末尾的流程重跑。
