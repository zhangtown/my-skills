# RemoteNet 逐组件清单（30 个组件族 × 交互状态 × 实现位置）

> **这是快照**：由一次全仓只读盘点生成，基准提交 `cea4dca`（2026-09-12）。
> 用途：动手加/改任何界面元素之前，先在这里查"这个元素在不在、在哪、有哪些状态"——
> 避免漏族、避免重复发明、避免把已有补丁再打一遍。
> 注意：**行号会随提交漂移，以文件路径 + 标识符名字为准**（直接 `rg` 名字最快）；
> 其中 §0.2 是**本项目已打的 11 处 vendor 补丁总表**（改样式前必看，别被补丁挡住）。


> 只读调研，基线：`D:\ProgramData\projects\ZtRemoteNet` 当前工作区（未构建、未修改）。
> 路径简写：`gui/` = `cmd/gui/`；`fyne/` = `vendor/fyne.io/fyne/v2/`；`glfw/` = `vendor/github.com/go-gl/glfw/v3.4/glfw/glfw/src/`。
> 结论口径：凡未打 vendor 补丁、也无自定义 widget 的状态，均按「Fyne 默认渲染 + `quietTheme` 令牌映射」记录。
> 主题令牌集中在 `gui/theme.go`（见文末「令牌缺口」与第 31 节）。

---

## 0. 前置：主题令牌与 vendor 补丁总表

### 0.1 主题令牌（`gui/theme.go`）

| 令牌 | 值 | 用途 | 位置 |
|---|---|---|---|
| `colBg` | #EFF0F3 | 内容区底、顶栏底（`colBarBg=colBg`）、HeaderBackground | gui/theme.go:24,32 |
| `colSurface` | #FFFFFF | 浮卡/输入框/菜单/弹层底 | gui/theme.go:25 |
| `colText` | #1F2328 | 主文字 | gui/theme.go:26 |
| `colTextMid` | #5A6169 | 次文字（底栏 info 提示） | gui/theme.go:27 |
| `colTextDim` | #9AA0A8 | 占位符 PlaceHolder | gui/theme.go:28 |
| `colHairline` | #E2E4E8 | 发丝线 Separator、TextSelection 之外的分隔 | gui/theme.go:29,83 |
| `colBorder` | #D5D8DD | 卡片描边、输入框边框、滚动条 | gui/theme.go:30,81,104 |
| `colBtnBg` | #EBEDF0 | 次级按钮底 | gui/theme.go:31 |
| `colBarClose` | #C42B1C | 顶栏 ✕ 悬停底（Windows 惯用红） | gui/theme.go:33 |
| `colBtnHover` | 黑 14%（NRGBA{0,0,0,0x24}） | 重要按钮 hover 叠加色 + 顶栏按钮 hover 底 | gui/theme.go:37 |
| `colAccent` | #A4243B | Primary/Hyperlink、焦点描线（Entry 聚焦） | gui/theme.go:38 |
| `colAccentBg` | #A4243B 8%（α0x14） | 悬浮/选中底（当前未被引用，见令牌缺口） | gui/theme.go:39 |
| `colSelBg` | #EAC6CE | Selection（文字选中/下拉高亮） | gui/theme.go:40 |
| `colDanger` | #D5382E | Error、危险按钮底、error 提示前缀 | gui/theme.go:41 |
| `colOK` | #2E8B57 | Success、ok 提示前缀 | gui/theme.go:42 |
| `colWarn` | #C07A00 | Warning | gui/theme.go:43 |
| `heroTop`/`heroBottom` | #2C313A → #15171C | 状态卡渐变（实际用字面量 #2C313A→#14161B，见缺口） | gui/theme.go:46-47；gui/ui.go:59-61 |
| `heroText`/`heroTextSub` | #F2F3F5 / #9BA3AD | 状态卡文字 | gui/theme.go:48-49 |
| `heroAccent` | #E04B5E | 状态卡强调色（未直接引用，见缺口） | gui/theme.go:50 |

Color() 映射补充（`gui/theme.go:58-107`）：
- `Foreground=colText`；`Button=colBtnBg`；`Background=colBg`；`Primary/Hyperlink=colAccent`。
- `Focus=#DEE2E8`（菜单/下拉高亮、按钮 focus 叠加），`Hover=#E4E7EB`，`Pressed=#D8DCE1`（theme.go:67,71,73 → 实际行 64-73）。
- `Disabled=#6B7280`（对白 4.6:1，「锁定但要看」），`DisabledButton=#F7F8FA`（比可用态更淡，避免层级倒挂）。
- `InputBackground=colSurface`、`InputBorder=colBorder`、`PlaceHolder=colTextDim`、`Separator=colHairline`、`ScrollBar=colBorder`。
- `Shadow=#1F2328 7%（α0x12）`；`MenuBackground/OverlayBackground=colSurface`；`HeaderBackground=colBg`。
- `widget.ButtonHoverDeepColorName=colBtnHover`（vendor 新增键，见 0.2-①）。

Size() 映射（`gui/theme.go:109-131`）：`sizeNameRowText=13`、`sizeNameMenuText=13`、`InputRadius=ButtonRadius=8`、`SelectionRadius=8`、`Padding=5`、`SeparatorThickness=1`、`Text=14`、`SubHeadingText=15`、`CaptionText=12`（气泡用）。

### 0.2 vendor 补丁（本项目改过的第三方文件）

| # | 文件 | 补丁内容 | 影响的状态 |
|---|---|---|---|
| ① | `fyne/widget/button.go:371-375,389-392` | 新增 `ButtonHoverDeepColorName="remotenetButtonHoverDeep"`；`buttonColorNames()` 中 hovered 分支由 `ColorNameHover` 改为该键（半透明黑按 alpha 叠加＝底色加深）。原因：主题 Hover 是不透明浅灰，blend 等于整替换，暗色 hero 上的红 CTA 会被抹灰像失效 | 按钮悬停 |
| ② | `fyne/widget/menu_item.go:22-24,341,363-364` | 新增 `MenuTextSizeName="remotenetMenuText"`；菜单文字 13 号 + `Monospace`；`minSizeUnchanged()` 一并校验该字号 | 菜单/下拉文字 |
| ③ | `fyne/widget/menu_item.go:58,302,366-372` | 弹层高亮块改 `ColorNameFocus`；禁用项文字 `ColorNameDisabled`；行内边距 `inset=1.5`、背景 `size-2*inset`（commit 6a5c3fe/9afc824 系列） | 菜单项悬停/激活/禁用 |
| ④ | `fyne/widget/menu.go:334-349,357` | 自定义 `menuBoxLayout`：菜单行距由 5px 收到 0，逐行 `y += o.MinSize().Height`，MinSize 高 = 各行和（不再 -2） | 菜单弹层行距 |
| ⑤ | `fyne/internal/driver/glfw/menu_bar_item.go:46-47,147` | 菜单栏文字 `TextStyle{Monospace:true}`；Layout 里字号取 `MenuTextSizeName` | 顶栏/托盘菜单文字 |
| ⑥ | `fyne/widget/select.go:427-436` | `bgColor()`：Disabled→`DisabledButton`；删除 focused 灰底（焦点残留）；hovered→`Hover`；其余 `InputBackground` | Select 各态 |
| ⑦ | `fyne/widget/check.go:378`、`fyne/widget/radio_item.go:199` | `focusIndicator.FillColor = color.Transparent`：去掉比勾选框/单选圈大一圈的焦点圆 | Check/Radio 焦点 |
| ⑧ | `fyne/internal/driver/glfw/window_desktop.go:808-810` | 建窗口时 `w.decorate && os.Getenv("REMOTENET_FRAMELESS") != "1"` 才加系统边框；否则 `Decorated=false`。入口：`gui/titlebar_windows.go:61 enableFrameless()`（在 `gui/main.go:33` 调用） | 无边框窗口 |
| ⑨ | `glfw/win32_window.c:76-107,372-380,1198-1205,1327-1340,1461-1476` | ①`getNativeWindowStyle()` 给无边框补 `WS_THICKFRAME`（DWM 才画系统投影）；②`getFrameCalcStyle()` 算客户区时去掉 `WS_THICKFRAME|WS_CAPTION`；③`updateWindowStyles()` 补回 `WS_THICKFRAME`；④`WM_NCCALCSIZE` 无边框返回 0（客户区==窗口矩形）；⑤创建后 `DwmSetWindowAttribute(DWMWA_WINDOW_CORNER_PREFERENCE=DWMWCP_ROUND)` + `DWMWA_BORDER_COLOR=DWMWA_COLOR_NONE`。拒绝过：`CS_DROPSHADOW`（只右下 5px 硬边）、自绘 1px 描边（压深一档）、`DwmExtendFrameIntoClientArea`（内缩 7px） | 窗口边界/圆角/投影 |
| ⑩ | `glfw/win32_platform.h:300-323,510`、`glfw/win32_init.c:152-154` | 补 `PFN_DwmSetWindowAttribute` 函数指针 + `DWMWA_*`/`DWMWCP_*` 常量（旧 SDK 缺失）并从 dwmapi 取符号 | 同上 |
| ⑪ | `glfw/glfw_tree_rebuild.go:12-14`、`glfw/c_glfw_windows.go:13` | C 树哈希标记 `3905fd840dcbfafce3b2f5bf249ca210644563f3`；改 C 代码后必须 `go run ./tools/glfwmarker -write` 才会重编 | 构建链路 |

### 0.3 本项目 GUI 自绘/自定义清单（无补丁处）

| 自定义件 | 类型 | 位置 |
|---|---|---|
| `barButton` | 顶栏扁平按钮（自绘 hover 底） | gui/titlebar_windows.go:244-296 |
| `barTitle` | 顶栏标题（报 0 最小宽 + 省略号） | gui/titlebar_windows.go:178-220 |
| `barDrag` | 顶栏拖动把手 | gui/titlebar_windows.go:298-355 |
| `resizeGrip` + `edgeGripLayout` | 右/下/右下缩放热区 | gui/titlebar_windows.go:359-480 |
| `tappableText` / `tipImage` | 可点文本 / 可悬浮图标（状态圆点） | gui/tappabletext.go:15-141 |
| `hoverTip` / `tipButton` / `tipLabel` | 气泡宿主与两种挂载件 | gui/tips.go:36-302 |
| `footHint` + `footHintRenderer` | 底栏提示（状态色+省略号） | gui/ui.go:394-481 |
| `labelCellLayout` | 标签列（定宽左对齐垂直居中） | gui/ui.go:347-363 |
| `footBarLayout` | 底栏（左提示+右按钮组） | gui/ui.go:365-392 |
| `minHeightLayout` / `fixedSize` | 抬高最小高 / 固定尺寸单元格 | gui/ui.go:503-552 |
| `card()` | 白卡容器（圆角 10+描边 1） | gui/ui.go:98-115 |
| `escList` | List 外包一层接管 ESC | gui/conns.go:437-461 |
| `brand` 包 | 状态点/托盘/应用图标的纯 Go 渲染 | internal/brand/branding.go |

---

## 1. 按钮（widget.Button：主/次/危险/普通过）

| 状态 | 实现方式 | 代码位置 |
|---|---|---|
| 正常-主按钮 HighImportance | 底 `ColorNamePrimary=#A4243B`、字 `ForegroundOnPrimary=#FFFFFF`；运行时切成「断开连接」 | gui/theme.go:38,99；gui/ui.go:78-79,86；gui/app.go:355-364 |
| 正常-次按钮（默认 Importance） | 底 `ColorNameButton=#EBEDF0`、字 `colText=#1F2328` | gui/theme.go:31,60,65 |
| 正常-低强调 LowImportance | 底透明（`background` 不设，见 vendor 分支），字 `colText`；禁用时底也透明（不套 DisabledButton） | fyne/widget/button.go:384-395；gui/ui.go:124-125,164-166 |
| 正常-危险 DangerImportance | 底 `ColorNameError=colDanger=#D5382E`、字 `ForegroundOnError`；只在「运行中」的断开态出现 | fyne/widget/button.go:400-403；gui/app.go:357-359 |
| 悬停 | 所有 Importance 统一：`ButtonHoverDeepColorName`（黑 14%）按 alpha 叠加＝底色加深；红按钮仍红、浅灰按钮可见加深 | fyne/widget/button.go:389-392（补丁①）；gui/theme.go:106 |
| 按压 | vendor 未改；`ColorNamePressed=#D8DCE1` 被主题提供，但按钮渲染路径未引用（悬停叠加优先） | gui/theme.go:72 |
| 焦点 | `backgroundBlend=ColorNameFocus=#DEE2E8`；字色仍 Foreground | fyne/widget/button.go:384-388 |
| 禁用 | 字 `ColorNameDisabled=#6B7280`；非 LowImportance 底 `ColorNameDisabledButton=#F7F8FA`（比可用态更淡）；LowImportance 底透明 | fyne/widget/button.go:384-388；gui/theme.go:110-113 |
| 选中/激活 | 按钮无选中态；状态即「运行中」由文本+Importance 切换（连接↔断开连接） | gui/app.go:353-365 |
| 尺寸 | `btnConnect` 150×40、`btnTest` 110×40（`fixedSize` GridWrap）；续期/推送到 NAS 等自然尺寸 | gui/ui.go:85-88 |
| 光标 | Fyne 默认（PointerCursor） | — |

**规范要点**：悬停 = 半透明黑 14% 叠加在任意底色上（不换色），保证暗底 CTA 不「变灰失活」；禁用色必须比可用色更淡（#F7F8FA vs #EBEDF0），且禁用文字对白 ≥4.5:1（#6B7280）。

## 2. tipButton（带气泡的按钮：续期证书 / 域名直连 / 进程直连）

| 状态 | 实现方式 | 代码位置 |
|---|---|---|
| 正常/悬停/按压/禁用 | 完全继承 `widget.Button`（含补丁①），本身只额外转发鼠标事件给气泡宿主 | gui/tips.go:223-252 |
| 悬停（气泡） | `MouseIn/Moved → b.Button.* + tipHover()`；`get()` 每次现取文案（可随状态变化） | gui/tips.go:233-248 |
| 禁用（气泡抑制） | `Disabled()` 时不弹气泡（`tipHover` 第一行判断） | gui/tips.go:246-248 |
| 业务禁用 | 连接明细子行：非隧道行或进程名空 → `btnProc.Disable()`；直连行/IP → `btnDomain.Disable()` | gui/conns.go:352-365 |
| 尺寸 | 明细子行按钮 86×28；续期证书 `newTipButton` 自然尺寸、Importance=Low | gui/conns.go:286-289；gui/ui.go:168 |

**规范要点**：能禁用的按钮不弹气泡（禁用态本身即说明不可用）；气泡文案惰性取（`get func() string`），避免状态未更新时弹旧文案。

## 3. 顶栏窗口按钮（─ 最小化 / ✕ 关闭）

| 状态 | 实现方式 | 代码位置 |
|---|---|---|
| 状态 | 实现方式 | 代码位置 |
|---|---|---|
| 正常 | 底 `color.Transparent`；文字 13 号居中 `colText`；不用 `widget.Button`（其浅灰胶囊贴顶栏像碎块） | gui/titlebar_windows.go:256-272 |
| 悬停-普通 | 底 `colBtnHover`（黑 14%） | gui/titlebar_windows.go:278-292 |
| 悬停-关闭 | 底 `colBarClose=#C42B1C`（Windows 惯用红） | gui/titlebar_windows.go:278-292 |
| 按压 | 无独立按压态（Tapped 即执行；最小化 `ShowWindow(SW_MINIMIZE=6)`，✕ 走 `quitFromBar→w.Close()`） | gui/titlebar_windows.go:141-142,294-296 |
| 焦点/禁用/选中 | 无（不进焦点链，无禁用入口） | — |
| 尺寸 | 各 34×32；✕ 组左侧垫 10px | gui/titlebar_windows.go:152-156 |
| 光标 | `desktop.PointerCursor` | gui/titlebar_windows.go:272 |

**规范要点**：关闭按钮悬停用系统语义红 #C42B1C，不用通用灰；`MouseMoved` 高频，重绘前先比对 `hover` 状态。

## 4. 顶栏菜单按钮（文件 / 帮助）

| 状态 | 实现方式 | 代码位置 |
|---|---|---|
| 正常 | 同 `barButton`（透明底 + 13 号 colText） | gui/titlebar_windows.go:232-241,256-264 |
| 悬停 | 同 `barButton`（黑 14%）；点击即弹层，无按压态 | gui/titlebar_windows.go:274-292 |
| 激活（弹层打开） | 按钮无「打开中」持续底色；弹层底 `colSurface`（MenuBackground/OverlayBackground） | gui/titlebar_windows.go:233-241；gui/theme.go:100 |
| 禁用/焦点/选中 | 无 | — |
| 尺寸 | 各 56×32 | gui/titlebar_windows.go:150-151 |
| 弹层定位 | `AbsolutePositionForObject(b)` + 按钮高度 → `ShowAtPosition`（贴按钮下沿，左对齐） | gui/titlebar_windows.go:238-240 |

**规范要点**：自绘下拉必须按控件绝对位置定位（不是鼠标点位置）；菜单项文字/行距走 vendor 补丁②④。

## 5. 顶栏标题 barTitle

| 状态 | 实现方式 | 代码位置 |
|---|---|---|
| 正常 | 14 号加粗 `colText`、左对齐，垂直居中 `(size.Height-m.Height)/2` | gui/titlebar_windows.go:186-214 |
| 宽度收缩 | `MinSize().Width=0`（不争宽），`ellipsize()` 逐字截断补 `…` | gui/titlebar_windows.go:216-220,197-204；gui/ui.go:483-501 |
| 悬停/按压/焦点/禁用/选中 | 无（纯展示，事件穿透给 `barDrag`） | — |
| 尺寸 | 高自适应，位于 46px 顶栏 Border 中区 | gui/titlebar_windows.go:163-170 |

**规范要点**：可被挤占的文字一律「报 0 宽 + 自管省略号」（canvas.Text 无 Truncation）；标题让位、菜单完整。

## 6. 顶栏拖动把手 barDrag

| 状态 | 实现方式 | 代码位置 |
|---|---|---|
| 正常 | 整条顶栏=把手；底色 `colBarBg=colBg`（与 hero 刻意不画分隔线）；实现 `Draggable`(`Dragged`+`DragEnd`) | gui/titlebar_windows.go:168-172,298-320 |
| 按压 MouseDown | 记录「光标绝对位置 − 窗口左上角」= `offX/offY`，`active=true` | gui/titlebar_windows.go:322-337 |
| 拖动中 | `GetCursorPos` 物理像素 → `moveWindowTo(pt.X-offX, pt.Y-offY)`（`SetWindowPos` + `SWP_NOSIZE|NOZORDER|NOACTIVATE`），不用 Fyne 逻辑增量（高 DPI 会跟不住） | gui/titlebar_windows.go:339-355,114-119 |
| 松开 | `MouseUp`/`DragEnd` → `active=false` | gui/titlebar_windows.go:337 |
| 双击最大化 | **未实现**（未找到处理代码） | — |
| 悬停/焦点/禁用/选中 | 无视觉变化；按钮按「最上层实现接口者」优先吃事件 | gui/titlebar_windows.go:169-172 注释 |

**规范要点**：无边框拖动必须用「绝对光标 − 按下偏移」；拖动区=整条顶栏，交互控件自行消化事件。

## 7. 边缘缩放热区 resizeGrip（右 / 下 / 右下角）

| 状态 | 实现方式 | 代码位置 |
|---|---|---|
| 正常 | 3 个透明 grip 叠在内容之上：右 5×H、下 W×5、角 14×14 | gui/titlebar_windows.go:450-480 |
| 悬停（光标） | `HResizeCursor` / `VResizeCursor` / `NWSEResizeCursor` | gui/titlebar_windows.go:452-466,391 |
| 按压 MouseDown | 记录物理像素光标 `sx,sy` 与窗口 `sw,sh` | gui/titlebar_windows.go:393-413 |
| 拖动中 | `w += pt.X - sx` / `h += pt.Y - sy` → `setWindowSize`（`SWP_NOMOVE|NOZORDER|NOACTIVATE`）；下限=内容 `MinSize()`（Fyne 会兜底弹回） | gui/titlebar_windows.go:419-448 |
| 松开 | `MouseUp`/`DragEnd` → `active=false` | gui/titlebar_windows.go:415-417 |
| 禁用/焦点/选中 | 无 | — |
| 依赖 | vendored glfw 补丁⑨（WS_THICKFRAME+DWM 投影/圆角）；缩放逻辑本身不依赖 | — |

**规范要点**：热区 5px、角 14px；缩放以物理像素差计算；下限绑内容最小尺寸。

## 8. 输入框（Entry / MultiLineEntry）

控件：`edHost/edPort/edListen/edCA/edCert/edKey`（单行）、`edDirect/edDirectProc/edOverride`（多行）、`browserRow` 里的端口行。

| 状态 | 实现方式 | 代码位置 |
|---|---|---|
| 正常 | 底 `InputBackground=#FFFFFF`、边框 1px `InputBorder=colBorder=#D5D8DD`、圆角 `InputRadius=8` | fyne/widget/entry.go:181-185；gui/theme.go:86-87,121-124 |
| 悬停 | Fyne 默认无底色变化（本主题未改 Entry 渲染） | fyne/widget/entry.go:1700-1730（无 hover 分支） |
| 聚焦 | 边框色改 `ColorNamePrimary=colAccent=#A4243B`；光标 `FillColor=ColorNamePrimary` | fyne/widget/entry.go:1710-1714,1860 |
| 校验错误 | 边框色 `ColorNameError=colDanger` | fyne/widget/entry.go:1726-1728 |
| 禁用 | 文字 `ColorNameDisabled=#6B7280`；边框 `ColorNameDisabled`；占位符同样走 Disabled | fyne/widget/entry.go:1267-1292,1717 |
| 占位符 | `PlaceHolder=colTextDim` | fyne/widget/entry.go:1042；gui/theme.go:85 |
| 选中文字 | `Selection=colSelBg=#EAC6CE`（近白在白底会隐形，故用暗红浅底） | gui/theme.go:70 |
| 多行 | `Wrapping=TextWrapWord`；直连域名定高 56、代理例外 88（`minHeightLayout`） | gui/ui.go:137-140,180-183,196-202 |
| 尺寸 | 端口框固定 90 宽；输入框列自适应 | gui/ui.go:224-225 |
| 光标 | Fyne 默认文本光标 | — |

**规范要点**：聚焦只改边框为品牌暗红（不整块高亮）；禁用文字仍保持 4.6:1；占位符不得用禁用色以外的灰（#9AA0A8）。

## 9. 下拉选择（Select：profileSel / selBrowser）

| 状态 | 实现方式 | 代码位置 |
|---|---|---|
| 正常 | 底 `InputBackground=#FFFFFF`、边框 `InputBorder=colBorder`、圆角 `InputRadius=8`；选项文字 13 号等宽（弹层） | fyne/widget/select.go:427-436；gui/theme.go:86-87 |
| 悬停 | 底 `ColorNameHover=#E4E7EB` | fyne/widget/select.go:430-432（补丁⑥） |
| 聚焦 | **不画灰底**（原始 Fyne 会对 focused 画灰；补丁删除，避免点空白/关弹层后灰底滞留） | fyne/widget/select.go:428-429 注释（补丁⑥） |
| 禁用 | 底 `ColorNameDisabledButton=#F7F8FA`；下拉箭头 `NewDisabledResource` | fyne/widget/select.go:427-429,443 附近 |
| 选中值文字 | 走 `ColorNameForeground`；未选择时占位符走 PlaceHolder（Fyne 默认） | fyne/widget/select.go:110-120 |
| 弹层行（悬停/激活） | 高亮块 `ColorNameFocus=#DEE2E8`；行距 0（menuBoxLayout）、行内缩 1.5px、13 号等宽 | fyne/widget/menu_item.go:302；fyne/widget/menu.go:334-349（补丁③④） |
| 弹层禁用项 | 文字 `ColorNameDisabled=#6B7280` | fyne/widget/menu_item.go:366-372 |
| 尺寸 | 弹层宽=控件宽，高=MinSize；`Alignment` 跟随 | fyne/widget/select.go:413-425 |

**规范要点**：焦点不落灰底（避免残留）；悬停浅灰 #E4E7EB；下拉高亮=Focus #DEE2E8 且必须与 Selection 分开（后者给文字选中）。

## 10. 复选框（Check：cbAutoConn / cbAutoRecon / cbAutostart）

| 状态 | 实现方式 | 代码位置 |
|---|---|---|
| 正常未选 | 图标描边 `InputBorder=colBorder`、底 `InputBackground=#FFFFFF` | fyne/widget/check.go:349-351 |
| 正常已选 | 勾选图标 `ColorNamePrimary=colAccent=#A4243B`、底 `ColorNameBackground=colBg` | fyne/widget/check.go:355-360 |
| 悬停 | Fyne 默认无 hover 分支（无底色变化） | fyne/widget/check.go:340-370 |
| 焦点/激活圈 | **不画**：`focusIndicator.FillColor=color.Transparent`（原大圆比勾选框大一圈且与主题冲突） | fyne/widget/check.go:378（补丁⑦） |
| 禁用 | 勾选框图标 `ColorNameDisabled=#6B7280`，标签文字 Disabled | fyne/widget/check.go:323-326,364-367 |
| 选中文字 | 标签 `ColorNameForeground=colText` | fyne/widget/check.go:172,323 |
| 尺寸/位置 | 三个开关收在「高级选项」折叠区内；行高按 Label 自然高 | gui/ui.go:188-190,205-209；gui/cards_test.go:44-71 |

**规范要点**：勾选的可见性靠「描边→主色实心」而不是外圈光环；焦点圈透明是本项目的刻意取舍（macOS/Windows 原生也会画，此处被否）。

## 11. 单选框（RadioGroup：rgScope 三选项）

| 状态 | 实现方式 | 代码位置 |
|---|---|---|
| 正常未选 | 外圈 `InputBorder=colBorder`、内点 `InputBackground=#FFFFFF` | fyne/widget/radio_item.go:178-180 |
| 正常已选 | 内点 `ColorNamePrimary=colAccent=#A4243B`、外圈 `ColorNameForeground` | fyne/widget/radio_item.go:182-183 |
| 悬停 | Fyne 默认无独立 hover 视觉 | fyne/widget/radio_item.go:165-195 |
| 焦点 | `focusIndicator.FillColor=color.Transparent`（补丁⑦，去掉大圆） | fyne/widget/radio_item.go:199 |
| 禁用 | 内点 `ColorNameDisabled`、外圈 Disabled、标签 Disabled | fyne/widget/radio_item.go:172,187-191 |
| 选中回调 | `onScopeChanged(v)`：切浏览器范围时刷新 `browserRow` 可见性与代理行提示 | gui/ui.go:212-216,678-736；gui/app.go:703 附近 |
| 尺寸 | Fyne 默认（选项纵向排列） | gui/ui.go:212-216 |

**规范要点**：与 Check 同款「去焦点大圆」；选中态用主色实心内点，未选用边框色，禁用一律 #6B7280。

## 12. 折叠项（Accordion：高级选项 / 证书管理）

| 状态 | 实现方式 | 代码位置 |
|---|---|---|
| 正常收起 | `widget.NewAccordion` 两项：标题「高级选项（点击展开）」「证书管理（点击展开）」；`MultiOpen=false`（同时只开一个） | gui/ui.go:205-209 |
| 展开/激活 | Fyne 默认 Accordion 渲染（标题加粗、展开后内容参与布局）；展开后 `body.MinSize()` 变高，被 `cards_test.go` 锁死 | fyne/widget/accordion.go（默认） |
| 禁用/焦点/悬停 | 无自定义（Fyne 默认焦点链） | — |
| 内容 | 第 1 项：三个 Check + 直连域名/进程直连/代理例外三行（带 tipLabel）；第 2 项：证书三行 + 续期/推送按钮 | gui/ui.go:188-209 |
| 布局影响 | 折叠卡是主面板最后一个对象；窗口高度只加高不缩（`fitBody`） | gui/ui.go:239-275；gui/app.go:272-300 |
| 尺寸 | `card("", a.certAcc)` 白卡内；标题/内容间距 `CustomPaddedLayout(8,12,14,14)` | gui/ui.go:98-115,245 |

**规范要点**：折叠区开合只影响滚动内容高度，绝不因此缩窗口（只 `fitBody` 加高）；开关类低频项必须收进折叠区，主面板保持「状态卡+三张卡」。

## 13. 状态圆点（tipImage，顶部 hero 左侧）

| 状态 | 实现方式 | 代码位置 |
|---|---|---|
| 正常 | 24×24（`tipImageSize=24`）等比 `ImageFillContain` 的 PNG 圆点；三态资源：`dot-disconnected/gray`、`dot-connected/green`、`dot-error/red` | gui/tappabletext.go:86-114；gui/icon.go:44-47 |
| 悬停 | `MouseIn/Moved` → `tipHover`：懒取 `dotTip()`（状态文字+补充提示，`\n` 拼接）；空串不弹 | gui/tappabletext.go:117-136；gui/app.go:257-269 |
| 移出 | `MouseOut → host.hideTip()` | gui/tappabletext.go:124-127 |
| 光标 | `desktop.DefaultCursor`（**注释写「悬停手型」，代码返回 Default，二者不一致**，见令牌缺口） | gui/tappabletext.go:138-141 |
| 禁用/焦点/选中/按压 | 无 | — |
| 颜色来源 | `internal/brand`：Connected #2FB35D、Error #E5483E、Disconnected #9EA3A8（渲染 PNG，不读主题令牌） | internal/brand/branding.go:6-11,27-35 |
| 切换 | `setState(text, dot, tray)` 同时换圆点/状态文字/托盘图标 | gui/app.go:230-247 |

**规范要点**：状态色必须「圆点/状态字/托盘」三者同源同刻切换；补充提示只走气泡、绝不占版面；气泡内容允许超长（自己折行，不影响窗口尺寸）。

## 14. hero 状态文字与流量行（heroTag / heroStatus / heroTraffic / heroServer）

| 元素 | 正常态实现 | 代码位置 |
|---|---|---|
| 渐变底 | `canvas.NewLinearGradient(#2C313A→#14161B, angle 0)`；实际字面量 #2C313A→#14161B（与 theme.heroBottom #15171C 不一致，见缺口） | gui/ui.go:59-61 |
| heroTag「网络加密隧道」 | 11 号 #9BA3AD（字面量，未走令牌） | gui/ui.go:63-64 |
| heroStatus | 18 号加粗 #F2F3F5（=heroText 字面量）；文案由 `setState` 更新 | gui/ui.go:70-72；gui/app.go:230-247 |
| heroTraffic | `tappableText` 13 号等宽 #C9CFD8；`OnTapped=showConnDetails`（有悬停光标接口但 Cursor() 未覆写→默认箭头）；内容 `↑ %s   ↓ %s   会话 %d` | gui/ui.go:73-74；gui/app.go:302-315 |
| heroServer | 12 号 #9BA3AD；`服务器 <addr>` 或「服务器（未填写）」 | gui/ui.go:75-76；gui/app.go:317-330 |
| 内边距 | `CustomPaddedLayout(12,14,16,16)`；tagRow 右对齐、statusRow 用 Padded 包裹、btnRow 用 Padded | gui/ui.go:84-95 |
| 悬停/按压/焦点/禁用/选中 | 圆点见第 13 节；流量文本只有 Tapped（无按压视觉）；其余纯展示 | — |

**规范要点**：深色面板文字三档：主 #F2F3F5 / 次 #9BA3AD / 数值 #C9CFD8；面板内边距 16/16 + 上下 12/14；状态卡与下方卡片间距 8px（`heroCardGap`）。

## 15. 卡片容器 card（白浮卡）

| 状态 | 实现方式 | 代码位置 |
|---|---|---|
| 正常 | `canvas.Rectangle` 白底、`CornerRadius=10`、`StrokeColor=colBorder=#D5D8DD`、`StrokeWidth=1` | gui/ui.go:98-101 |
| 内边距 | `CustomPaddedLayout(8,12,14,14)`（上 8 / 下 12 / 左右 14） | gui/ui.go:113 |
| 有标题 vs 无标题 | 标题=加粗 `widget.Label` 置于内容上方；无标题卡（证书管理）直接 VBox | gui/ui.go:104-112 |
| 悬停/按压/焦点/禁用/选中 | 无（静态容器） | — |
| 卡片间距 | `cardSlot`：左右各 5（`cardPadH`），上下 0（`cardPadV=0`）→ 卡间距 = VBox 行距 5px；hero 槽位另补 `heroCardGap`(8) − theme.Padding(5) | gui/ui.go:309-333 |
| 底部余量 | `bodyPadBottom=32`（防最后一张卡被底栏盖住，测试锁定 ≥24px） | gui/ui.go:526-529；gui/cards_test.go:30-42 |

**规范要点**：白卡=圆角 10 + 1px #D5D8DD 描边、无投影；卡间距 5px、hero 下 8px；滚动区底部余量 32px 是硬约束。

## 16. 标签与标签列（widget.Label / tipLabel / labelCellLayout）

| 元素/状态 | 实现方式 | 代码位置 |
|---|---|---|
| 普通标签 | `widget.NewLabel`（14 号 `ColorNameText`，走 `quietTheme`）；卡片标题 `NewLabelWithStyle(..., Bold)` | gui/ui.go:104-107,122-123 |
| tipLabel（直连域名/进程直连/代理例外） | 内嵌 `widget.Label`，`MouseIn/Moved` 弹气泡（说明三者的区别），`MouseOut` 收起 | gui/tips.go:254-302 |
| 标签列 | `labelCellLayout{w}`：固定列宽、**左对齐**（x=0）、垂直居中；MinSize=(w, 22+8) | gui/ui.go:347-363 |
| 列宽 | `labelColWidth(labels...) = 最宽标签实测 + labelGap(8)`；每卡独立计算 | gui/ui.go:302-303,335-344 |
| 悬停/按压/焦点/禁用/选中 | 无（Label 不可交互；tipLabel 仅气泡） | — |
| 约束测试 | 三张卡列宽余量必须恰为 8px；标签 x 必须为 0（禁止右对齐留白） | gui/labels_test.go:35-81 |

**规范要点**：标签列宽按最长标签实测 + 8px，不压字也不留白；必须左对齐（右对齐是历史投诉点）；tipLabel 文案必须写明与相邻项的「区别」。

## 17. 悬浮气泡 hoverTip（所有悬停提示的宿主）

| 状态/参数 | 实现方式 | 代码位置 |
|---|---|---|
| 触发（延迟） | `tipDelay=600ms` 定时器；计时前若位移 < `tipJitter=6px` 视为抖动、保持计时；换文案或移开则换代 `gen` 丢弃 | gui/tips.go:53-89 |
| 已显示后移动 | 直接跟随鼠标重新定位（不再计时） | gui/tips.go:59-62 |
| 移出 | `MouseOut` → `hideTip()`（停 timer、`pop.Hide()`） | gui/tips.go:126-135 |
| 内容 | `widget.Label`（**必须**，canvas.Text 不支持 `\n` 会出豆腐块）+ `SizeName=CaptionText=12`；`container.NewPadded` 包边 | gui/tips.go:45-51,97-112 |
| 折行 | `wrapTip` 按 `tipMaxWidth=420` 估算宽度折行，保留原换行，优先在空格/路径分隔符/标点处断 | gui/tips.go:17-23,152-200 |
| 定位 | 默认光标右下 `(x+14, y+20)`；右/下越界回收（左/上至少 4px），下方不够翻到光标上方 `(pos.Y-h-8)` | gui/tips.go:63-95 |
| 关闭清理 | `close()`：气泡挂画布 overlay，对话框关闭必须显式关，否则残留 | gui/tips.go:128-135；gui/conns.go:520-530 |
| 禁用/焦点/选中/按压 | 无（气泡不参与） | — |
| 依赖 | `widget.NewPopUp`（画布 overlay）+ `fyne.Do` 回主线程；跨窗口不可复用（明细窗自建一个） | gui/conns.go:520；gui/tips.go:82-88 |

**规范要点**：气泡 600ms 延迟 + 6px 抖动容差；宽 420px 折行、12 号字；必须绑定当前画布（借用别的窗口画布弹不出来）；窗口/对话框关闭时要 `close()`。

## 18. 连接明细列表（连接列表行/子行/tappableText/escList）

独立窗口「连接明细」，含三个页签、每页一个 `widget.List`。

| 状态 | 实现方式 | 代码位置 |
|---|---|---|
| 行正常（隧道） | 主行三段 `tappableText`（进程 150 / 目标 380 / 状态 110，各包 `GridWrapLayout(w,30)`），13 号等宽、`ColorNameForeground` | gui/conns.go:152-172,200-215 |
| 行正常（直连） | 主行三段文字整体改 `ColorNameDisabled=#6B7280`（灰显），隧道行醒目 | gui/conns.go:238-247 |
| 悬停 | 主行无底色变化；三段各挂气泡：进程=完整路径+PID、目标>22 字给全文、状态=「点这一行展开/收起明细」 | gui/conns.go:248-263 |
| 点击/激活（展开） | 点主行任意格 `toggle()`，按连接 ID 记忆展开态；展开显式 `SetItemHeight(header+sub)` + `RefreshItem`，收起复位模板高 | gui/conns.go:366-402 |
| 子行 | 13 号等宽 `widget.Label`（`sizeNameRowText`）；详情 `MediumImportance`（隧道）/`LowImportance`（直连）；失败行 `DangerImportance` 红字 | gui/conns.go:174-215,267-290 |
| 子行按钮 | `tipButton` 86×28、LowImportance；非隧道/无进程名则 `Disable()` | gui/conns.go:282-289,352-365 |
| 选中/焦点 | 无行选中概念；列表可获焦点但无高亮（行是纯容器） | gui/conns.go:437-461 |
| 键盘 | `escList` 覆写 `TypedKey`，ESC 交回对话框（列表夺焦后 canvas 回调不再触发）；`canvas.SetOnTypedKey` 兜底 | gui/conns.go:437-461,568-575 |
| 刷新 | 1.5s 轮询 `connRefreshInterval`，只追加不改行序（`allRows` + 下标视图） | gui/conns.go:20,100-140,580-592 |
| 窗口/尺寸 | 独立窗口（弹窗会被主窗 424px 夹住）；宽=列合计 `connColsWidth=150+380+110+10` +24，高 580；`MinSize` 撑窗口 | gui/conns.go:26-32,498-508 |
| 行左留白 | `connRowPad=10`（主行与统计行同起点） | gui/conns.go:30,166-168,514-516 |
| 页签 | `container.NewAppTabs` 全部/已结束/失败；`OnChanged=collapseAll`（防止跨页残留展开态） | gui/conns.go:480-490 |

**规范要点**：明细表列宽=「典型内容放得下」反推（有测试锁）；行序只追加、展开态按 ID 记忆；`List` 需要不等高行时用 `SetItemHeight`；ESC 必须由列表显式接管。

## 19. 页签（AppTabs）

| 状态 | 实现方式 | 代码位置 |
|---|---|---|
| 正常/选中 | Fyne 默认 AppTabs 渲染 + 主题令牌（选中强调色走 Primary=colAccent；底/发丝线走 Background/Separator） | fyne/container/tabs.go（默认）；gui/theme.go:58-107 |
| 悬停/按压/焦点 | Fyne 默认（未打补丁） | — |
| 禁用 | 无禁用页签 | — |
| 切换 | `tabs.OnChanged` → `collapseAll()` 收起所有展开子行 | gui/conns.go:480-490 |

**规范要点**：页签切换不能让上一个页签的行状态（展开态）泄漏到新页；页签文字用等宽 13 号（全局 `sizeNameMenuText` 同源，菜单/列表/页签字阶一致）。

## 20. 底栏提示 footHint（滚动区之外，左下）

| 状态/kind | 实现方式 | 代码位置 |
|---|---|---|
| ok | 前缀 `✓ `，颜色 `colOK=#2E8B57` | gui/ui.go:409-428 |
| error | 前缀 `✗ `，颜色 `colDanger=#D5382E` | gui/ui.go:409-428 |
| info（默认） | 前缀 `… `，颜色 `colTextMid=#5A6169` | gui/ui.go:409-428 |
| 空消息 | `Set("",...)` 清空 `full` 与显示 | gui/ui.go:410-414 |
| 窄宽度 | 13 号 `canvas.Text`，`ellipsize` 逐字截断补 `…`；`MinSize().Width=0` 不参与底栏宽度（长提示不能撑宽窗口） | gui/ui.go:394-481,483-501 |
| 布局时机 | 只在真实 Layout（宽>0）时截断，避免 `Set` 后的 0 宽 Refresh 把整条吃掉 | gui/ui.go:454-472；gui/footbar_test.go:46-50 |
| 匹配判断 | `Showing(kind,msg)` 比较含前缀的完整串（截断不影响判断） | gui/ui.go:433-443 |
| 悬停/按压/焦点/禁用/选中 | 无（纯展示） | — |
| 位置 | `footBarLayout`：左提示占满剩余、右侧按钮组自然宽贴右垂直居中；整条在 `Border.bottom`，滚动再长也压不掉 | gui/ui.go:237-250,365-392 |

**规范要点**：反馈文字三态色（绿/红/灰）靠 kind 前缀；长文必须省略号且不改变窗口/底栏布局；底栏按钮固定在滚动区外是硬约束（测试锁）。

## 21. 底栏按钮（查看日志 / 导出诊断）

| 状态 | 实现方式 | 代码位置 |
|---|---|---|
| 正常 | 默认 Importance 按钮（底 #EBEDF0、字 #1F2328），自然尺寸 | gui/ui.go:232-234 |
| 悬停/按压/焦点 | 继承通用按钮（补丁① 悬停加深；Focus #DEE2E8） | fyne/widget/button.go:384-395 |
| 禁用 | 随运行态一起禁用（`setButtonsRunning` 未含二者；二者恒可用） | gui/app.go:333-350 |
| 行为 | 查看日志=notepad 打开 remotenet-gui.log；导出诊断=winfile.SaveFile 默认名 `remotenet-诊断-*.txt` | gui/app.go:851-870,732-810 |
| 尺寸/间距 | HBox 右侧，Padded 底栏；按钮间距 Fyne 默认 Padding=5 | gui/ui.go:237-250 |

**规范要点**：全局反馈入口永远可见（固定在底栏右侧）；文件落盘走原生对话框（见第 27 节）。

## 22. 滚动区与滚动条

| 状态 | 实现方式 | 代码位置 |
|---|---|---|
| 正常 | `container.NewVScroll(inner)` 包裹主面板（`inner` = body + 底部 32px 余量）；滚动条颜色 `ColorNameScrollBar=colBorder=#D5D8DD` | gui/ui.go:249,258；gui/theme.go:103-104 |
| 滚动条尺寸 | Fyne 默认（**未**覆写 `ScrollBar` 尺寸类 SizeName） | fyne/internal/widget/scroller.go |
| 悬停/按压/拖动 | Fyne 默认（拖动滚动条内置；未打补丁） | — |
| 禁用 | 无 | — |
| 特殊约束 | `VScroll.MinSize().Height` 是常量 32，不能当内容高；窗口高度=内容+底栏+留白，用 `bodyMinHeight()` 自算 | gui/app.go:270-285；gui/ui.go:263 注释 |

**规范要点**：滚动条是唯一「Fyne 默认尺寸 + 仅换颜色」的控件，若要统一视觉需补 `SizeNameScrollBar`（见令牌缺口）；窗口高度不得依赖 Scroll 的 MinSize。

## 23. 分隔线与发丝线

| 形态 | 实现方式 | 代码位置 |
|---|---|---|
| 菜单分隔（文件/帮助/托盘） | `fyne.NewMenuItemSeparator()`，颜色 `ColorNameSeparator=colHairline=#E2E4E8`、厚 1px | gui/ui.go:287,291；gui/tray.go:33,35；gui/theme.go:29,83,125-126 |
| 卡片边界 | 用 `colBorder=#D5D8DD` 1px 描边（非发丝线） | gui/ui.go:104 |
| 顶栏与 hero 之间 | **刻意不画线**：顶栏底 `colBarBg=colBg`，靠底色延续到 hero 渐变 | gui/titlebar_windows.go:168-170 |
| 按钮/输入框描边 | `colBorder`（输入框）、`colHairline` 仅分隔语义 | gui/theme.go:81,83 |

**规范要点**：两级线：发丝线 #E2E4E8（1px 分隔）/ 边框 #D5D8DD（1px 卡片/输入框轮廓）；顶栏↔hero 不用线，用色块接续。

## 24. 下拉菜单（PopUpMenu）与菜单项

| 状态 | 实现方式 | 代码位置 |
|---|---|---|
| 弹层正常 | 底 `MenuBackground/OverlayBackground=colSurface=#FFFFFF`；阴影 Shadow #1F2328 7%（α0x12）；行距 0（`menuBoxLayout`） | gui/theme.go:100,102；fyne/widget/menu.go:334-349 |
| 菜单项文字 | 13 号 `Monospace`（=连接明细行），正常 `ColorNameForeground=colText`；快捷键提示色=前景 19.8% 透明 | fyne/widget/menu_item.go:363-372,379-384（补丁②） |
| 菜单项悬停/激活 | 高亮块 `ColorNameFocus=#DEE2E8`；行内缩 1.5px（块宽=行宽−3、高=行高−3？实现为 background.Resize(size−2×1.5) 后 Move(1.5,1.5)） | fyne/widget/menu_item.go:302；gui/theme.go:67-68 |
| 菜单项按压 | 无独立按压态（Tapped 执行） | — |
| 菜单项禁用 | 文字 `ColorNameDisabled=#6B7280`；SVG 图标 `NewDisabledResource`；托盘「启动浏览器/系统代理」按范围互斥禁用 | fyne/widget/menu_item.go:346-348,366-372；gui/tray.go:66-80 |
| 菜单项选中 | 可勾选项（当前菜单无 `Checked`）走 Fyne 默认勾选图标 | — |
| 尺寸 | 文字 13（`MenuTextSizeName`）；行高=text.MinSize+内边距（minSizeUnchanged 校验字号/图标/内边距三者变化才重算） | fyne/widget/menu_item.go:22-24,330-345 |
| 顶部菜单栏 | 已全部被自绘顶栏按钮替代；vendored `menu_bar_item.go` 补丁仅保证残留路径同字号等宽 | fyne/internal/driver/glfw/menu_bar_item.go:46-47,147 |

**规范要点**：菜单与「连接明细」列表同字阶（13 号等宽）——跨控件的「数据/命令字阶」统一；高亮 #DEE2E8；禁用 #6B7280；弹层行距 0、内缩 1.5px 是刻意压缩。

## 25. 系统托盘菜单

| 状态 | 实现方式 | 代码位置 |
|---|---|---|
| 正常 | `desktop.App.SetSystemTrayMenu`：显示主界面 / 连接 / 系统代理 / 启动浏览器 / — / 连接明细 / — / 退出 | gui/tray.go:20-41 |
| 文案随状态 | 连接中：「断开连接」「关闭系统代理」；否则「连接」「接管系统代理」；`trayMenu.Refresh()` | gui/tray.go:56-80 |
| 禁用（互斥） | 浏览器范围：`miLaunch.Disabled=!browserMode`、`miProxy.Disabled=browserMode`（系统代理由用户自理） | gui/tray.go:73-74 |
| 悬停/按压/高亮/文字 | 与第 24 节同一套 vendor 补丁（13 号等宽、Focus 高亮、禁用 #6B7280） | 补丁②③④ |
| 图标 | `trayRes(state)`：深色 mini 方块+状态色 Z 徽标（Connected/Error/Disconnected），随 `setTrayIcon` 切换 | gui/icon.go:49-52；gui/tray.go:96-102 |
| 未支持平台 | 返回「当前驱动不支持系统托盘」错误（不阻断启动） | gui/tray.go:43-51 |
| 通知气泡 | `fyne.NewNotification`（Windows 无开始菜单快捷方式可能静默失败，不阻塞） | gui/tray.go:104-112；gui/app.go:1157-1175 |

**规范要点**：托盘文案是主界面按钮的镜像（同一动作两种状态文案）；互斥功能用 `Disabled` 表达而不是隐藏；托盘图标与界面圆点同状态色系。

## 26. 对话框（错误/信息/确认/表单）

| 形态 | 触发 | 实现方式 |
|---|---|---|
| 错误 | `showError(title, err)` | `dialog.ShowError(fmt.Errorf("%s\n\n%v",title,err), a.w)`（fyne/widget/dialog，默认令牌渲染） | gui/app.go:671-678 |
| 信息 | `showInfo(title,msg)` | `dialog.ShowInformation(title,msg,a.w)` | gui/app.go:680-687 |
| 确认 | `confirm(title,msg,onOK)` | `dialog.ShowConfirm(title,msg,func(ok bool),a.w)`；删除证书/覆盖生成等 | gui/app.go:689-699 |
| 表单 | 生成证书 | `dialog.NewForm("生成证书","生成","取消",[服务域名/IP, 输出目录], cb, a.w)`；`form.Resize(560×280)`；确认后再 `confirm` 覆盖警告 | gui/ui.go:981-1006 |
| 按钮语义 | 主/取消按钮走默认 Importance + 补丁①；对话框底色/发丝线走主题令牌 | fyne/widget/dialog |
| 悬停/按压/焦点/禁用 | 对话框按钮即 `widget.Button`（同第 1 节）；Form 的 Entry 同第 8 节；禁用态 Fyne 默认 | — |
| 窗口关系 | 模态挂在主窗 `a.w` 上，**必被主窗尺寸夹住**（这是连接明细改用独立窗口的原因） | gui/conns.go:500-506 注释 |

**规范要点**：破坏性操作（覆盖生成、删除配置）必须二次确认；表单尺寸显式 560×280；模态弹窗宽度受母窗限制 → 宽表必须独立窗口。

## 27. 原生文件对话框（winfile）

| 状态/形态 | 实现方式 | 代码位置 |
|---|---|---|
| 打开 | `winfile.OpenFile(title, dir, filters...)` → `GetOpenFileNameW`（comdlg32），系统「打开」界面（地址栏/最近/库/网络可用） | internal/winfile/openfile_windows.go:22,88-90,106-139 |
| 另存为 | `winfile.SaveFile(...)` → `GetSaveFileNameW`，默认名 4096 缓冲 | internal/winfile/openfile_windows.go:90-93,106-120 |
| 取消 | 返回 `ErrCanceled`（`CommDlgExtendedError=0`）；调用方**静默返回**，不算错误 | internal/winfile/openfile_windows.go:82-86,136-141；gui/ui.go:891-935 |
| 真错误 | 返回 `文件对话框错误 0x%X` | internal/winfile/openfile_windows.go:141 |
| 过滤器 | 「证书/PEM 文件」`*.pem;*.crt;*.cer;*.key` + 「所有文件」`*.*`；`buildFilter` 手工拼双 NUL（不能用 StringToUTF16 会 panic） | gui/ui.go:891-935；internal/winfile/openfile_windows.go:143-157 |
| 标志 | `OFN_HIDEREADONLY|NOCHANGEDIR|PATHMUSTEXIST|FILEMUSTEXIST|EXPLORER|ENABLESIZING|DONTADDTORECENT`；无父窗口（任务栏独立按钮） | internal/winfile/openfile_windows.go:24-32,122-135 |
| 悬停/按压/焦点/禁用 | 系统对话框原生行为（不受本项目样式控制） | — |

**规范要点**：**不用 Fyne 自绘文件选择器**——文件选择必须走系统对话框；取消是正常路径（`ErrCanceled` 静默）；过滤器清单拼接必须兼容内嵌 NUL。

## 28. 光标（cursor）形状汇总

| 控件 | 光标 | 实现位置 |
|---|---|---|
| 顶栏按钮（文件/帮助/─/✕） | `desktop.PointerCursor` | gui/titlebar_windows.go:272 |
| 拖动把手 barDrag | Fyne 默认（箭头；`Cursor()` 未覆写） | — |
| 缩放热区（右/下/角） | `HResizeCursor` / `VResizeCursor` / `NWSEResizeCursor` | gui/titlebar_windows.go:391,452-466 |
| 状态圆点 tipImage | `desktop.DefaultCursor`（代码），但注释写「悬停手型」——**实现与注释不符** | gui/tappabletext.go:138-141 |
| tappableText（流量行、明细行） | Fyne 默认箭头（`Cursor()` 未覆写，尽管可点） | gui/tappabletext.go:46 |
| 输入框/按钮/下拉/复选/单选 | Fyne 默认（文本光标/箭头） | — |

**规范要点**：可点元素建议统一 PointerCursor（现状不一致：顶栏按钮手型、可点文字与圆点是箭头）；缩放热区三向光标必须区分。

## 29. 自定义布局与间距体系

| 布局 | 作用 | 关键数值 | 位置 |
|---|---|---|---|
| `labelCellLayout` | 标签列固定宽、左对齐、垂直居中 | 宽=`labelColWidth`；MinSize=(w, 22+8) | gui/ui.go:347-363 |
| `footBarLayout` | 底栏：左提示+右按钮组 | 按钮组自然宽、垂直居中；提示占满剩余 | gui/ui.go:365-392 |
| `minHeightLayout` | 只抬最小高（多行框） | `minHeight(o, h)` | gui/ui.go:531-552 |
| `fixedSize` | 固定尺寸单元格 | GridWrapLayout(w,h) | gui/ui.go:503-508 |
| `edgeGripLayout` | 三缩放热区摆位 | 5 / 5 / 14 | gui/titlebar_windows.go:468-480 |
| `menuBoxLayout`（vendor） | 菜单行距 0 | 行高逐个累加 | fyne/widget/menu.go:334-349 |
| `cardSlot` | 卡片左右 5、上下 0 | `cardPadV=0, cardPadH=5` | gui/ui.go:309-318 |
| `heroSlot` | hero 左右 0、底部补 3px | `heroCardGap(8) − Padding(5)` | gui/ui.go:320-333 |
| `body` 内边距 | 底部余量 | `bodyPadBottom=32` | gui/ui.go:249,526-529 |
| hero 内边距 | 上 12 下 14 左右 16 | CustomPaddedLayout(12,14,16,16) | gui/ui.go:94 |
| 卡片内边距 | 上 8 下 12 左右 14 | CustomPaddedLayout(8,12,14,14) | gui/ui.go:113 |
| 明细行内距 | 左 10，子行上/右/下= Padding(5) | `connRowPad=10` | gui/conns.go:30,166-168,291-294 |

**规范要点**：主面板节奏 = 卡间距 5px、hero 下 8px、卡内 8/12/14/14、body 底 32px；所有「标签→控件」间距 8px；这些值都已有 const 或集中在少量函数里，可作为间距规范基线。

## 30. 窗口本体（无边框 / 圆角 / 投影 / 图标）

| 项 | 实现方式 | 位置 |
|---|---|---|
| 无边框 | `enableFrameless()` 置 `REMOTENET_FRAMELESS=1`（必须在 `NewWindow` 前，`main.go:33` 调用）；vendored glfw 读环境变量把 `Decorated=false` | gui/titlebar_windows.go:44-61；gui/main.go:31-33；补丁⑧ |
| 边界/投影/圆角 | `WS_THICKFRAME` + `WM_NCCALCSIZE=0`（客户区铺满）+ DWM 投影 + `DWMWCP_ROUND` 圆角 + `DWMWA_COLOR_NONE` 去强调色描边 | 补丁⑨（win32_window.c:76-107,1198-1205,1461-1476） |
| 顶栏 | 46px 高、左右 10 内边距、logo 28px；底 `colBarBg`；Border 布局（logo 左 / 菜单右 / 标题中区可截断） | gui/titlebar_windows.go:48-57,130-175 |
| 默认尺寸 | `minW=内容 MinSize().Width`、`minH=bodyMinHeight()`（内容+底栏+32+46）→ `Resize` + `CenterOnScreen` | gui/ui.go:261-268 |
| 高度策略 | `fitBody()` 只加高不缩、不动宽度（用户拖过的尺寸不被回填/提示改动） | gui/app.go:272-300 |
| 窗口图标 | Fyne 只给 GLFW 一张资源（原样不重绘）；本项目用 32px `app-32.png` + `winicon_windows.go` 轮询 `WM_SETICON` 换 exe 内嵌 .ico 的真 16/32 图 | gui/icon.go:55-70；gui/winicon_windows.go:1-116 |
| 关闭语义 | `SetCloseIntercept(onClose)`：点 ✕/系统关闭 → `Hide` + 托盘通知（真正退出在菜单/托盘） | gui/ui.go:49-52；gui/ui.go:1157-1166；gui/app.go:811-850 |
| 自启驻留 | `-autostart` 时不 `Show()`（托盘驻留） | gui/main.go:48-53 |

**规范要点**：无边框窗口的「边界感」全交给系统投影+圆角（不画自绘描边、不用 CS_DROPSHADOW）；关闭=收托盘、退出=显式动作；窗口高度是单调不减的。

## 31. 尺寸与间距令牌汇总（可实现值）

| 项 | 值 | 来源 |
|---|---|---|
| 圆角 | 卡片 10；按钮/输入框/下拉/选中 8 | gui/ui.go:100；gui/theme.go:121-124 |
| 行高/字阶 | 正文 14 / 小标题 15 / 说明 12 / 数据行与菜单 13 / 状态标题 18 / 顶栏标题 14 粗 / heroTag 11 | gui/theme.go:127-131；gui/ui.go:72；gui/titlebar_windows.go:191 |
| 间距 | 全局 Padding 5；标签→控件 8；卡间距 5；hero 下 8；明细行左 10；子行内 5 | gui/theme.go:125；gui/ui.go:303,321 |
| 分隔 | 1px（SeparatorThickness） | gui/theme.go:125-126 |
| 顶栏 | 46 高 / 左右 10 / logo 28 / 菜单按钮 56×32 / 窗口按钮 34×32 | gui/titlebar_windows.go:48-57,150-156 |
| 缩放热区 | 5 / 5 / 14 | gui/titlebar_windows.go:55-56 |
| 主操作 | 连接 150×40、测试 110×40、端口 90 宽 | gui/ui.go:85-88,225 |
| 多行框 | 直连 56 / 例外 88 | gui/ui.go:196-202 |
| 明细窗 | 列 150/380/110 + 行留白 10；高 580；默认宽=合计+24 | gui/conns.go:26-32,498-508 |
| 气泡 | 宽 420 / 延迟 600ms / 抖动 6px / 字号 12 / 偏移 (14,20) | gui/tips.go:17-23,87；gui/theme.go:131 |
| 状态圆点 | 24×24 | gui/tappabletext.go:96 |

---

## 与本项目设计相关的既有测试

`cmd/gui/` 下 7 个测试文件，全部在约束「视觉/布局」而不是业务逻辑：

| 文件 | 一句话（它在锁什么） | 关键常量/阈值 |
|---|---|---|
| `cmd/gui/cards_test.go:30-42` `TestBottomClearance` | 主面板滚动区底部余量必须够，否则最后一张卡（高级选项/证书管理）会被底栏盖住一截（用户反馈过两次） | `bodyPadBottom=32`；断言 `slack = 视口高 − body.MinSize().Height >= 24px` |
| `cmd/gui/cards_test.go:44-79` `TestAutoOptionsInsideAdvanced` | 三个开关（启动自动连接/断开自动重连/开机自动启动）必须在「高级选项」折叠区内，不能留在主面板；展开折叠区必须使内容变高 | 折叠项 `a.certAcc.Items[0].Detail`；展开前后 `body.MinSize().Height` 必增 |
| `cmd/gui/conns_cols_test.go:13-51` `TestConnColumnWidths` | 明细表列宽能放下典型内容（防止改字号/列宽后内容被截断）；统计两行也要在窗口宽度内完整显示 | `connColProc=150`、`connColTarget=380`、`connColInfo=110`（「隧道 · 进行中」为基准）、`connRowPad=10`、`connColsWidth=650`；文案样例 `optimizationguide-pa.googleapis.com:443`、`本次 46 条（进行中 8）…` |
| `cmd/gui/footbar_test.go:17-57` `TestFootHint` | 底栏提示按 kind 上色/加前缀；窄宽度省略号截断且不超宽；宽够显示全文；空消息清空；提示不参与底栏宽度 | 130px 宽必须出现 `…` 且 `MinSize().Width <= 131`；600px 显示全文；`ok→"✓ "`、`error→"✗ "`、`info→"… "`；`MinSize().Width == 0` |
| `cmd/gui/labels_test.go:16-48` `TestLabelColumnWidths` | 每张卡标签列宽 = 该卡最长标签 + `labelGap`，误差必须恰为 8px | `labelGap=8`；三张卡标签组：证书管理 / 高级选项（本地代理、直连域名、进程直连、代理例外）/ 连接设置 |
| `cmd/gui/labels_test.go:51-63` `TestLabelCellLeftAligned` | 标签列必须左对齐（右对齐会把短标签推到列尾留白，旧版 104px 右对齐被投诉） | 布局后 `l.Position().X == 0` |
| `cmd/gui/layout_test.go:21-76` `TestDetailNeverResizesWindow` | 状态补充提示绝不动窗口尺寸、绝不进 body 最小尺寸、必须进圆点气泡；主面板固定 4 个子项（状态卡+三张卡） | `len(a.body.Objects)==4`；对 6 种文案（含两倍超长）断言窗口尺寸与 `body.MinSize()` 不变；文案须 `strings.Contains(a.dotTip(), …)` |
| `cmd/gui/menu_test.go:11-20` `TestMenuTextSize` | 菜单字号契约：vendor 尺寸名与值必须保持 | `widget.MenuTextSizeName == "remotenetMenuText"`；`quietTheme.Size(...) == 13` |
| `cmd/gui/tips_test.go:25-84` `TestAdvancedRowTips` | 高级选项三行的气泡必须各说各的（域名 vs 程序 vs 系统代理），三条文案互不相同且都写明「区别」 | 关键词 `域名` / `程序` / `系统代理`；`tipFormDirectDomain`、`tipFormDirectProc`、`tipProxyOverride` 三者互不相等且都含「区别」 |

---

## 令牌缺口

代码里出现、但未集中为命名令牌的颜色字面量/魔法尺寸（= 写规范时的「待固化项」）。按类型分组：

### 颜色字面量（散落在逻辑里）

| 位置 | 值 | 现状/建议 |
|---|---|---|
| `cmd/gui/theme.go:64` | `#DEE2E8`（Focus：菜单/下拉高亮、按钮 focus） | 写在 `Color()` 分支里的字面量，建议提为 `colFocus` |
| `cmd/gui/theme.go:70` | `#E4E7EB`（Hover） | 同上，建议 `colHover` |
| `cmd/gui/theme.go:72` | `#D8DCE1`（Pressed） | 同上，建议 `colPressed`（当前按钮路径未用到） |
| `cmd/gui/theme.go:89` | `#6B7280`（Disabled 文字） | 建议 `colDisabled` |
| `cmd/gui/theme.go:94` | `#F7F8FA`（DisabledButton 底） | 建议 `colBtnDisabledBg` |
| `cmd/gui/theme.go:96` | `#1F2328` 7%（Shadow α0x12） | 建议 `colShadow` |
| `cmd/gui/theme.go:98` | `#FFFFFF`（ForegroundOnPrimary） | 建议 `colOnPrimary` |
| `cmd/gui/theme.go:39,46-47,50` | `colAccentBg`(#A4243B 8%)、`heroTop`、`heroBottom`(#15171C)、`heroAccent`(#E04B5E) | **已定义但全项目零引用**（grep 验证）：要么删除，要么接回 hero/选中底 |
| `cmd/gui/ui.go:59-61` | 渐变 `#2C313A → #14161B` | 与 `theme.heroBottom`(#15171C) 不一致（差 1 个色阶），且绕开令牌 |
| `cmd/gui/ui.go:63` | heroTag `#9BA3AD` | 等于 `heroTextSub` 的字面量复制 |
| `cmd/gui/ui.go:70` | heroStatus `#F2F3F5` | 等于 `heroText` 的字面量复制 |
| `cmd/gui/ui.go:73` | heroTraffic `#C9CFD8` | 无令牌（面板数值色） |
| `cmd/gui/ui.go:75-76` | heroServer `#9BA3AD` | 同 heroTag（第三处复制） |
| `cmd/gui/ui.go:99` | 卡片底 `#FFFFFF` | 应当用 `colSurface` |
| `cmd/gui/titlebar_windows.go:261` | barButton 文字 `colText`（好） | — |
| `internal/brand/branding.go:27-35` | 状态色 `#2FB35D` / `#E5483E` / `#9EA3A8`（Connected/Error/Disconnected） | 与主题 `colOK=#2E8B57`、`colDanger=#D5382E` **不同值**：同一语义两套色，需要统一或明确「PNG 图标色允许更艳」的规则 |
| `vendor/…/menu_item.go:260` | `inset=1.5` 高亮块内缩 | vendor 魔法值（commit 6a5c3fe：5px→1.5px），影响所有弹层视觉 |

### 尺寸/间距魔法值（无 const 或未进入令牌体系）

| 位置 | 值 | 用途 |
|---|---|---|
| `cmd/gui/titlebar_windows.go:150-156` | 菜单按钮 56×32、窗口按钮 34×32、✕ 组左垫 10 | 顶栏控件盒 |
| `cmd/gui/titlebar_windows.go:189` | 顶栏标题 14 号 Bold | 与 `SizeNameSubHeadingText=15`/`Text=14` 无显式对应 |
| `cmd/gui/titlebar_windows.go:262` | barButton 13 号 | 与 `sizeNameRowText/MenuText` 同值但独立书写 |
| `cmd/gui/ui.go:86-87` | 连接 150×40 / 测试 110×40 | 主操作尺寸 |
| `cmd/gui/ui.go:94` | hero 内边距 12/14/16/16 | 布局魔法值 |
| `cmd/gui/ui.go:113` | 卡片内边距 8/12/14/14 | 布局魔法值 |
| `cmd/gui/ui.go:196,201` | 多行框最小高 56 / 88 | `directEntryHeight=56` 是局部 const，88 是裸值 |
| `cmd/gui/ui.go:225` | 端口输入框宽 90 | 魔法值 |
| `cmd/gui/ui.go:402-403` | footHint 13 号 | 与 13 号系列重复书写 |
| `cmd/gui/ui.go:1005` | 生成证书表单 560×280 | 对话框尺寸魔法值 |
| `cmd/gui/conns.go:286-289` | 子行按钮 86×28 | 魔法值 |
| `cmd/gui/conns.go:153,158-160` | 主行单元格高 30 | 魔法值（行高另由 `SetItemHeight` 动态改） |
| `cmd/gui/conns.go:507` | 明细窗高 580 | 魔法值 |
| `cmd/gui/conns.go:509` | 明细窗宽=内容宽+24 | 魔法余量 |
| `cmd/gui/tips.go:87-95` | 气泡偏移 14/20、边距 4、翻转 8 | 与 `tipMaxWidth/Delay/Jitter` 同处但未命名 |
| `cmd/gui/icon.go:44-52` | 圆点/托盘 PNG 64px | 图标源尺寸魔法值（显示 24px / 托盘按系统） |
| `cmd/gui/icon.go:64` | 应用图标 32px | 有意选择（README 注释），建议写成 `iconAppSize=32` |
| `gui/theme.go:18-22` | `sizeNameRowText` 与 `sizeNameMenuText` 同值 13 | 两个尺寸名同值，可合并或注明「同字阶不同用途」 |
| `cmd/gui/ui.go:303` | `labelGap` 已有 const（好） | — |

> 低悬果实：① `colFocus/colHover/colPressed/colDisabled/colDisabledBg/colShadow/colOnPrimary` 七个字面量提进 `theme.go` 头部；② hero 三段文字色提为 `heroTextSub/heroText/heroValue`；③ `brand` 状态色与主题 `colOK/colDanger` 对齐（或写死「品牌图标不参与主题」的豁免说明）；④ 顶栏控件盒、主操作按钮、明细窗 580/24 提为布局常量。

---

## 盘点统计

- 组件/控件族：**30 个**（第 1–30 节），其中自定义 widget/布局 **14 件**，vendor 补丁 **11 处**。
- 状态覆盖：按钮 4 种 Importance、顶栏 4 类控件、输入类 5 种（Entry/MultiLine/Select/Check/Radio）、容器 4 种（card/Accordion/AppTabs/List 行）、反馈 4 种（footHint/气泡/对话框/托盘通知）、系统形态 3 种（无边框窗口/原生文件对话框/光标）。
- 未找到项（明确用 Fyne 默认或未实现）：顶栏双击最大化、滚动条自定义尺寸、列表行选中态、菜单项按压态、圆点手型光标（注释与实现不符）、`colAccentBg/heroTop/heroBottom/heroAccent` 令牌引用。
