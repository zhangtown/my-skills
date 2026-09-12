# 组件总规范：RemoteNet 里每一个界面元素长什么样、怎么响应

这份文件是"界面设计固化"的主入口。**加任何新界面元素之前，先在下面找到它的同族模板，照抄那族的
形状/尺寸/状态/光标**；找不到同族的，先按第 7 节的清单自审，再把新族补写进来。

六态机制（悬停叠色公式、焦点策略、禁用可读性、气泡、cursor、动画禁令）在
`references/interaction-and-states.md`；颜色 / 字号 / 圆角 / 间距的令牌在 `references/design-tokens.md`；
窗口边框/投影/圆角在 `references/windows-chrome.md`。这里只讲"组件本身"。

> 路径简写：`gui/` = `cmd/gui/`，`fyne/` = `vendor/fyne.io/fyne/v2/`。

## 1. 组件地图：五族，各族共用一份视觉

| 族 | 成员 | 共用规则 |
|---|---|---|
| **按钮族** | 主/次/低/危险按钮、带气泡按钮、顶栏窗口按钮、顶栏菜单按钮、底栏按钮、明细窗子行按钮 | 悬停＝黑 14% 叠色（`ButtonHoverDeepColorName`）；文字 14；圆角 8；禁用可见 |
| **输入族** | Entry（单/多行）、Select、Check、Radio | 白底 + 1px `colBorder` + 圆角 8；聚焦只改边框为主色；焦点圈透明 |
| **容器族** | `card()`、Accordion、AppTabs、连接列表行、滚动区 | 白卡圆角 10 + 1px 描边、无投影；卡间距 5；开合只加高不缩窗 |
| **顶栏族** | `barButton`/`barTitle`/`barDrag`/`resizeGrip` | 46px 高；控件盒 56×32 / 34×32；手型光标；事件"最上层接口者优先" |
| **反馈族** | `footHint`、`hoverTip` 气泡、对话框、托盘菜单+图标+通知 | 反馈不占版面、不改窗口尺寸；告知走底栏，决策才弹窗 |

**数据/命令字阶统一 13 号等宽**：菜单项、下拉弹层、连接明细行、页签、底栏提示——凡是"行式数据或命令"
一律 13 号 Monospace（`sizeNameRowText` / `SizeNameMenuText` 同值，vendor 侧靠
`MenuTextSizeName="remotenetMenuText"` 保障，`gui/menu_test.go` 锁死）。正文/标签用 14，卡片标题加粗 14，
小标题 15，说明/气泡 12，状态标题 18 粗。

## 2. 按钮族

| 组件 | 形状 / 尺寸 | 状态要点 | 实现位置 |
|---|---|---|---|
| 主按钮 HighImportance | 底 `colAccent #A4243B`、字 `#FFFFFF`；`btnConnect` 150×40、`btnTest` 110×40（`fixedSize`） | 悬停＝**黑 14% 叠加**（底更深，仍是红）；运行中变"断开连接"，危险态底 `colDanger` | `gui/ui.go:78-88`、`gui/app.go:353-365` |
| 次按钮（默认 Importance） | 底 `colBtnBg #EBEDF0`、字 `colText`；自然尺寸 | 悬停加深；禁用底 `#F7F8FA` < 可用态（层级不许倒挂） | `fyne/widget/button.go:384-395` |
| 低强调 LowImportance | 底透明、字 `colText`；用于"续期证书""进程直连""域名直连"等次级动作 | 禁用时**底仍透明**（不套禁用底色） | `gui/ui.go:124-125,164-166` |
| 危险按钮 Danger | 底 `colDanger #D5382E`；只在"运行中"替换主按钮 | 与主按钮同悬停公式 | `gui/app.go:357-359` |
| `tipButton` 带气泡按钮 | 包 `widget.Button`，额外转发鼠标事件给气泡宿主；明细子行 86×28 | 悬停同时加深底色 + 600ms 后弹气泡；**禁用时不弹气泡**；文案惰性取（`get func() string`） | `gui/tips.go:223-252`、`gui/conns.go:286-289` |
| 顶栏窗口按钮 ─ / ✕ | 34×32，文字 13 居中，底透明；✕ 组左垫 10px | 悬停底 `colBtnHover`（黑 14%）；**✕ 悬停底 `colBarClose #C42B1C`**（系统语义红，不用通用灰）；光标 `PointerCursor`；无按压态（Tapped 即执行） | `gui/titlebar_windows.go:244-296` |
| 顶栏菜单按钮 文件/帮助 | 56×32，透明底 + 13 号 `colText` | 悬停黑 14%；弹层打开时**按钮不加持续底色**；弹层定位＝控件绝对位置（`AbsolutePositionForObject` 贴按钮下沿左对齐），不是鼠标点 | `gui/titlebar_windows.go:150-151,232-241` |
| 底栏按钮 查看日志/导出诊断 | 默认 Importance，自然尺寸，固定在底栏右侧（滚动区之外） | 全局反馈入口，恒可用 | `gui/ui.go:232-250` |

**为什么不给主按钮单独配"悬停色"**：同一个按钮会出现在白卡与深色 hero 上，只有半透明叠色两边都对。
vendor 补丁 `fyne/widget/button.go:371-392` 新增 `widget.ButtonHoverDeepColorName` 并让 hovered 分支
用它；主题侧映射 `gui/theme.go:106`。**改按钮悬停逻辑前先读这两处。**

## 3. 输入族

| 组件 | 形状 / 尺寸 | 状态要点 | 实现位置 |
|---|---|---|---|
| Entry 单行 | 白底 + 1px `colBorder` + 圆角 8；端口框固定 90 宽；输入列自适应 | 聚焦＝边框变 `colAccent` + 光标同色（**不整块高亮**）；校验错误＝边框 `colDanger`；禁用＝字/边框 #6B7280 但仍可读；占位符 `colTextDim`；文字选中 `colSelBg #EAC6CE`（近白在白底会隐形） | `gui/theme.go:86-87,121-124`、`fyne/widget/entry.go:1700-1730` |
| Entry 多行 | 同上；`Wrapping=TextWrapWord`；直连域名定高 56、代理例外 88（`minHeightLayout`） | 同上；行高只抬最小高，不撑宽 | `gui/ui.go:196-202` |
| Select 下拉 | 白底 + `colBorder` + 圆角 8；弹层宽＝控件宽 | 悬停底 `#E4E7EB`；**聚焦不画灰底**（补丁⑥删除，避免点空白后灰底滞留）；禁用底 `#F7F8FA` + 箭头 `NewDisabledResource`；弹层项高亮 `#DEE2E8`、行距 0、行内缩 1.5px | `fyne/widget/select.go:427-436`、`gui/theme.go:86-87` |
| Check 复选框 | 未选＝`colBorder` 描边 + 白底；已选＝`colAccent` 勾 + 底 `colBg` | **焦点圈透明**（补丁⑦，刻意去掉点击后的大圆，别"修复"）；禁用＝图标 #6B7280；无悬停态 | `fyne/widget/check.go:340-378` |
| Radio 单选组 | 未选＝`colBorder` 外圈；已选＝`colAccent` 内点 + 前景色外圈 | 同 Check 去焦点大圆；回调 `onScopeChanged` 刷新浏览器行可见性 | `fyne/widget/radio_item.go:165-199`、`gui/ui.go:212-216` |
| 开关类归属 | 三个自动开关（自动连接/自动重连/开机自启）必须在"高级选项"折叠区内 | `cards_test.go` 锁死：折叠展开必须使内容变高 | `gui/ui.go:188-209`、`gui/cards_test.go:44-79` |

## 4. 容器族

| 组件 | 形状 / 尺寸 | 状态要点 | 实现位置 |
|---|---|---|---|
| `card()` 白卡 | 圆角 **10** + 1px `colBorder` 描边 + `colSurface` 底、**无投影**；内边距上 8 / 下 12 / 左右 14；有标题=加粗 Label 在内容上方 | 静态容器，无状态；卡间距＝VBox 行距 5（`cardSlot` 只做左右 5）；hero 下间距 8（`heroSlot` 补 `8-5=3`） | `gui/ui.go:98-115,309-333` |
| Accordion 折叠项 | 两项：高级选项 / 证书管理；`MultiOpen=false`；标题"（点击展开）" | 开合**只影响滚动内容高度，绝不因此缩窗口**（`fitBody` 只加高不缩、不动宽度）；低频开关必须收进折叠区 | `gui/ui.go:205-209,239-275`、`gui/app.go:272-300` |
| AppTabs 页签 | 连接明细窗三页签（全部/已结束/失败）；文字 13 号等宽 | 切换必须 `collapseAll()`（否则上一页展开态泄漏） | `gui/conns.go:480-490` |
| List 行（连接明细） | 列宽 150/380/110 + 行留白 10（`connColsWidth=650`），行高 30；主行三段 13 号等宽 | 隧道行正常色、直连行整体灰 `#6B7280`；点行展开（按连接 ID 记忆，`SetItemHeight`+`RefreshItem`）；快照只追加不改序（1.5s 轮询）；行本身无选中/悬停底色 | `gui/conns.go:26-32,152-247,366-402` |
| 滚动区 + 滚动条 | `container.NewVScroll(inner)`，滚动条仅换色（`colBorder`），**Fyne 默认尺寸** | 底部余量 `bodyPadBottom=32` 是硬约束（测试锁 ≥24px）；窗口高度**不得**依赖 `VScroll.MinSize()`（那是常量 32），用 `bodyMinHeight()` 自算 | `gui/ui.go:249,258,526-529`、`gui/app.go:270-285` |
| 分隔线 | 两级：发丝线 1px `colHairline #E2E4E8`（菜单分隔）/ 边框 1px `colBorder #D5D8DD`（卡片、输入框轮廓） | **顶栏与 hero 之间刻意不画线**（用底色延续） | `gui/ui.go:287,291`、`gui/titlebar_windows.go:168-170` |

## 5. 顶栏族（无边框窗口的自绘部分）

| 组件 | 形状 / 尺寸 | 状态要点 | 实现位置 |
|---|---|---|---|
| `barButton` 扁平按钮 | 文字 13 居中 `colText`、透明底（不用 `widget.Button`——浅灰胶囊贴顶栏像碎块）；顶栏 46 高、左右内边距 10、logo 28 | 悬停底 `colBtnHover`（先比对 hover 再重绘，`MouseMoved` 高频） | `gui/titlebar_windows.go:48-57,244-296` |
| `barTitle` 标题 | 14 号加粗 `colText`，垂直居中；**`MinSize().Width=0`** + `ellipsize()` 逐字截断补 `…` | 纯展示，事件穿透给拖动把手；窄窗时标题让位、菜单完整（canvas.Text 无 Truncation，必须自管省略） | `gui/titlebar_windows.go:178-220`、`gui/ui.go:483-501` |
| `barDrag` 拖动把手 | 整条顶栏即把手（`Draggable`+`MouseDown/Up`）；实现"绝对光标坐标 − 按下偏移"（**不能用 Fyne 逻辑增量**，高 DPI 跟不住） | 无悬停/按压视觉；可点子控件自己消化事件（最上层实现接口者优先）；双击最大化**未实现** | `gui/titlebar_windows.go:298-355` |
| `resizeGrip` 缩放热区 | 右 5×H、下 W×5、角 14×14，透明叠在内容之上 | 光标 `HResizeCursor`/`VResizeCursor`/`NWSEResizeCursor`；按物理像素差改窗口；下限＝内容 `MinSize()` | `gui/titlebar_windows.go:359-480` |
| 窗口本体 | 无边框（`REMOTENET_FRAMELESS=1` 必须在 `NewWindow` 前设）；边界靠系统投影+圆角 | 关闭＝收托盘（`SetCloseIntercept`：Hide + 托盘通知），退出＝显式菜单；窗口高度单调不减 | `gui/titlebar_windows.go:44-61`、`gui/ui.go:49-52`；详见 `windows-chrome.md` |

## 6. 反馈族与图形族

| 组件 | 形状 / 尺寸 | 状态要点 | 实现位置 |
|---|---|---|---|
| `footHint` 底栏提示 | 13 号 `canvas.Text`，前缀 `✓ `/`✗ `/`… `，色 `colOK`/`colDanger`/`colTextMid`；`MinSize().Width=0` | 长文省略号、**不撑宽窗口/底栏**；只在真实 Layout（宽>0）时截断，避免 0 宽 Refresh 吃掉整条；空消息清空；`Showing(kind,msg)` 比完整串 | `gui/ui.go:394-481`、`gui/footbar_test.go` |
| `hoverTip` 气泡 | `widget.Label`（必须，`canvas.Text` 遇到 `\n` 出豆腐块）+ `container.NewPadded`；字号 12；宽 420 折行（按字符宽，中英混排不能按字节）；偏移 (14,20)，越界回收/翻转 | 600ms 延迟 + 6px 抖动容差；已显示则跟随鼠标；换文案换代 `gen` 丢弃旧 timer；挂**当前画布** overlay（借用别的窗口画布弹不出来）；窗口/对话框关闭必须 `close()` | `gui/tips.go:17-200`、`gui/conns.go:520-530` |
| 状态圆点 `tipImage` | 24×24（PNG 源 64px）；三态圆点 + 悬停气泡 | 悬停／移动即弹（`dotTip()` 懒取）；空串不弹；光标现状是 `DefaultCursor`（注释写"手型"，**不一致**，见第 8 节） | `gui/tappabletext.go:86-141`、`gui/icon.go:44-52` |
| 对话框 | `ShowError` / `ShowInformation` / `ShowConfirm`；生成证书用 `dialog.NewForm` 并显式 `Resize(560,280)` | 破坏性操作必须二次确认（覆盖生成、删配置/证书）；**模态必被母窗尺寸夹住** → 宽表用独立窗口 | `gui/app.go:671-699`、`gui/ui.go:981-1006` |
| 原生文件对话框 | `internal/winfile`（`GetOpenFileNameW`/`GetSaveFileNameW`），过滤器「证书/PEM」+「所有文件」 | **不用 Fyne 自绘文件选择器**；取消是正常路径（`ErrCanceled` 静默返回）；过滤器拼双 NUL | `internal/winfile/openfile_windows.go`、`gui/ui.go:891-935` |
| 托盘菜单 + 图标 + 通知 | 菜单项与主界面同一套（13 号等宽、高亮 `#DEE2E8`、禁用 #6B7280）；图标＝深色 mini 方块 + 状态色 Z 徽标 | 文案＝主界面按钮的镜像（连接↔断开连接）；互斥功能用 `Disabled` 而不是隐藏；托盘图标与界面圆点同状态色系、同刻切换 | `gui/tray.go:20-112`、`gui/icon.go:49-52` |
| 应用/品牌图形 | `internal/brand` 纯 Go 渲染 PNG：圆点 Connected `#2FB35D` / Error `#E5483E` / Disconnected `#9EA3A8`；托盘/圆点多档尺寸（圆角 6/7/8） | 图标是 PNG（不读主题令牌），**允许比主题色更艳**（小尺寸需要）；应用图标 32px 是有意选择 | `internal/brand/branding.go:6-35`、`gui/icon.go:44-70` |

## 7. 新组件对齐清单（加任何界面元素前逐条过）

1. **找到同族模板**并抄形状：按钮抄按钮族、容器抄 `card()`、反馈抄 `footHint`/气泡。
2. **六态齐不齐**：正常/悬停/按压/焦点/禁用/选中——详见 `interaction-and-states.md` 的检查清单。
3. **颜色只用令牌**：不写 `color.NRGBA{...}` 字面量，不新造颜色（现状里仍有 12 处字面量，见第 8 节）。
4. **字号用现成字阶**：数据/命令 13 等宽、正文 14、说明 12、状态 18；不要为"看起来刚好"另开一档。
5. **圆角 8**（卡片 10）；间距用 5 的倍数，标签→控件 8。
6. **不动窗口尺寸**：新元素不许让窗口自动变大变小（只有 `fitBody` 的"只加高"例外），长文本用省略号 + 气泡。
7. **给 cursor**：可点 → `PointerCursor`；纯装饰 → `DefaultCursor`；缩放热区 → 对应 resize 光标。
8. **不加动画、不加焦点环**（除非用户明确要求）。
9. **补一个约束测试**（`cmd/gui/*_test.go`，见 `build-and-verify.md`）：锁住间距/字号/不改窗口/位置这类视觉契约。
10. **真机验证**：`go test ./cmd/gui/ -count=1` + 重建 + `swap_gui.ps1` 换 exe + 截图/像素采样（脚本见 `build-and-verify.md`）。
11. 数值有来历：要么是既有 const/令牌，要么能说出参考的同类控件——**别写"看着差不多"的魔法数**。

## 8. 已知不一致与未实现项（别当成"顺手修"的目标）

这些是盘点时确认的现状。它们**不是**待办清单：改动会牵动已固化的视觉，先问用户。

| 项 | 现状 | 处置建议 |
|---|---|---|
| 令牌缺口（12 处颜色字面量） | `#DEE2E8`(Focus)、`#E4E7EB`(Hover)、`#D8DCE1`(Pressed)、`#6B7280`(Disabled)、`#F7F8FA`(DisabledButton)、`#1F2328` 7%(Shadow)、`#FFFFFF`(OnPrimary)、hero 三段文字色、卡片底 `#FFFFFF`、渐变 `#2C313A→#14161B` | 提令牌是纯重构，需用户点头；`ui.go:59-61` 的 `#14161B` 与 `theme.heroBottom #15171C` 差一档 |
| 已定义但零引用 | `colAccentBg`(#A4243B 8%)、`heroTop`、`heroBottom`、`heroAccent`(#E04B5E) | 要么删，要么接回 hero/选中底——**问用户** |
| 状态色两套 | 主题 `colOK #2E8B57` / `colDanger #D5382E` vs 图标 `#2FB35D` / `#E5483E` | 建议明文豁免"小尺寸 PNG 图标更艳"，而不是硬统一 |
| 圆点光标 | 注释写"悬停手型"，代码返回 `DefaultCursor`；`tappableText` 可点但没覆写 `Cursor()` | 若统一成手型，属于交互改进，需用户确认 |
| 顶栏双击最大化 | 未实现 | 用户提过窗口行为，但未要求此功能 |
| 滚动条尺寸 | 未覆写 `SizeNameScrollBar`，是唯一"Fyne 默认尺寸"控件 | 统一视觉需先补令牌 |
| 菜单项按压态 / 列表行选中态 | 无 | 现状可接受；引入会改变已冻结的观感 |

## 9. 组件索引（速查）

| 想要什么 | 用什么 | 位置 |
|---|---|---|
| 白卡 / 卡槽 | `card(title, content)` / `cardSlot(o)` / `heroSlot(o)` | `gui/ui.go:98-115,309-333` |
| 悬停气泡按钮 / 标签 | `newTipButton(label,get,host)` / `newTipLabel(text,get,host)` | `gui/tips.go:223-302` |
| 底栏提示 | `newFootHint()` + `Set(kind,msg)` | `gui/ui.go:394-481` |
| 标签列 / 定宽单元格 / 抬高最小高 | `labelColWidth` / `fixedSize(o,w,h)` / `minHeight(o,h)` | `gui/ui.go:335-344,503-552` |
| 可点文字 / 状态圆点 | `newTappableText` / `newTipImage` | `gui/tappabletext.go:15-141` |
| 顶栏按钮 / 标题 / 拖动 / 缩放 | `newBarButton` / `newBarTitle` / `newBarDrag` / `newResizeGrip` | `gui/titlebar_windows.go:186-480` |
| 连接列表（ESC 接管） | `makeConnList` / `escList` | `gui/conns.go:437-461` |
| 品牌图形（圆点/托盘/应用图标） | `internal/brand` | `internal/brand/branding.go` |
| 打开/保存文件 | `winfile.OpenFile/SaveFile` | `internal/winfile/openfile_windows.go` |
