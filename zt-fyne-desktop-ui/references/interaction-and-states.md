# 交互与状态：每个控件都要有六态

这套界面的"精致"不在配色本身，而在**每个可交互元素都定义了六种状态**：
正常 / 悬停 / 按压 / 焦点 / 禁用 / 选中（激活）。只画正常态的控件，鼠标划过去那一刻就露馅——
这是 RemoteNet 返工最多的地方，git 历史里一串都是它：`3132ab1`（按钮悬停改"底色加深"）、
`9afc824`（悬停高亮块高度回归）、`6b0403f`（悬浮色改可见浅灰 + 按压加深）、
`62ffc0c`（去掉焦点大圆）、`c7b09bc`（输入框选中高亮不可见）。

## 一条总公式：交互态 = 在原底色上叠色

**任何悬停 / 按压 / 选中都必须是"叠在原底色上"，不能换成另一个不透明颜色。**
同一个控件会同时出现在白卡与深色 hero 面板上（主按钮就是），不透明覆色做不到两边都对——
红按钮被灰罩住会被读成"按钮失效"（`cmd/gui/theme.go:35` 的注释就是这么写的）。

| 场景 | 令牌 / 常量 | 值 | 机制与位置 |
|---|---|---|---|
| 重要按钮（红 CTA、深底按钮）悬停 | `ButtonHoverDeepColorName` | `colBtnHover = #00000024`（黑 14%） | **叠加** = 底色加深；vendor 补丁 `vendor/fyne.io/fyne/v2/widget/button.go:371-392`（`backgroundBlend = ButtonHoverDeepColorName`），主题侧映射在 `cmd/gui/theme.go:105` |
| 一般控件悬停（下拉、列表、菜单项、图标） | `ColorNameHover` | `#E4E7EB` | 白卡上可见的浅灰 |
| 按压 | `ColorNamePressed` | `#D8DCE1` | 比悬停深一档，拉出层次 |
| 激活 / 焦点高亮（菜单项、下拉展开态、下拉选项） | `ColorNameFocus` | `#DEE2E8` | 语义是"高亮当前项"，**不是** Tab 焦点环 |
| 禁用按钮底 | `ColorNameDisabledButton` | `#F7F8FA` | 淡到贴住卡片：**让"可用"比"禁用"更实** |
| 次级按钮底 | `colBtnBg` | `#EBEDF0` | 白卡上必须有边界，不能只靠描边 |
| 文字选中高亮 | `colSelBg` | `#EAC6CE` | 近白在白卡上会隐形 |
| 深色面板上的悬停/强调 | `heroAccent` | `#E04B5E` | 深底上要亮一档才看得见 |

## 禁用态：可读性优先，且不动布局

- 禁用**不改变尺寸与位置**（布局不许跳动），只降明度/饱和。
- 禁用文字用中灰 `#6B7280`（对白 4.6:1）。曾用 `#8A9098`（3.2:1），被判定太淡——
  连接期间这些字段是"锁定但用户仍要看"的信息，不是装饰。
- 层级别倒挂：禁用底色必须比可用态更淡（原 `#E7E9EC` 比可用态还亮，已否）。

## 焦点：鼠标用户不要焦点环

- `62ffc0c` 刻意去掉了 checkbox 点击后的大圆：`vendor/fyne.io/fyne/v2/widget/check.go:175`
  把 `focusIndicator` 画成 `ColorNameBackground`（等于隐形），radio 同理。**别"顺手修复"它。**
- 键盘可见性靠"项高亮"（`ColorNameFocus`）表达，不靠描边环。
- 真要做键盘焦点环，先确认它不会在鼠标点击时冒出来——这个方向被否过一次。

## 悬停提示（气泡）：不占布局、不改尺寸

`cmd/gui/tips.go` 是唯一入口：

- `newTipButton(label, getText, host)` / `newTipLabel(text, getText, host)` 包一层就有悬停气泡；
- `hoverTip.showTip / tipHover / hideTip` 管生命周期；`wrapTip` 按**字符宽度**折行
  （中英混排不能按字节折）；
- 气泡**不参与布局**、**绝不改变窗口尺寸**（用户明确要求，见 `8566c0b` 的提交信息）；
- 相关信息**合并成一条**气泡文案（状态圆点 + "连接明细"），不要弹两个气泡；
- 长文本用截断 + 气泡看全文（`newTipLabel` + `textTruncateEllipsis`）：卡片里的路径不许把卡片顶宽。

## 指针形状（cursor）

| 元素 | cursor | 位置 |
|---|---|---|
| 顶栏按钮 | `desktop.PointerCursor` | `cmd/gui/titlebar_windows.go:272`（`barButton.Cursor()`） |
| 可点文字（顶部流量行、连接明细三列） | `desktop.PointerCursor` | `cmd/gui/tappabletext.go`（`tappableText.Cursor()`）；约定锁在 `cmd/gui/tips_test.go` 的 `TestHoverCursors` |
| 窗口边缘/角落缩放热区 | `desktop.HResizeCursor` 等 | `cmd/gui/titlebar_windows.go:382-456`（`newResizeGrip(edge, min, cur)`） |
| 纯装饰（状态圆点 `tipImage`） | `desktop.DefaultCursor` | `cmd/gui/tappabletext.go`（只弹气泡、点了没反应） |

新加可点元素**顺手给出 cursor**；不给就还是默认箭头，用户不知道它能点。

## 过渡动画：默认不加

`cmd/gui/` 与 `internal/` 里没有任何 `NewAnimation` / `Animate(` 调用——状态变化是瞬时的。
**不要引入淡入淡出、位移过渡**：这套界面的节奏是"即时反馈"，加动画反而显得比系统慢半拍。
真需要动效先问用户（这是设计决策，不是实现细节）。

## 结果反馈：走底栏，不弹对话框

- 测试结果、打开浏览器、推送到 NAS 的结果 → 底栏即时提示（`cmd/gui/ui.go:401 newFootHint()`，
  `footbar_test.go` 守它），随后自动消失。
- 只有**需要用户决策**的事才弹对话框/确认；"操作完成"这类告知一律走底栏，别打断操作流。
- 文案要带动作 + 结果（做了什么、成功还是失败），别只写"完成"。

## 换状态的检查清单（改完照着走一遍）

1. 鼠标划过每个可点元素：有悬停反馈吗？在白卡和深色面板上都看得见吗？
2. 按下时有没有"按下去"的感觉（比悬停深一档）？
3. 禁用时：文字还读得清吗？布局有没有跳？
4. 选中/激活态：和悬停态区分得开吗？（菜单项的"当前项"与"鼠标所在项"是两回事）
5. 可点元素的 cursor 对吗？
6. 有没有不小心引入动画或焦点环？
