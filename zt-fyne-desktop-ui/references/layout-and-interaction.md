# 版面、尺寸与交互

> 本文件管"版面怎么摆"（骨架、卡片、槽位、尺寸策略、滚动与底部余量）。
> **每个组件自身长什么样、多大、什么光标**在 `components.md`；
> **悬停/按压/焦点/禁用/选中六态机制**在 `interaction-and-states.md`。

## 主面板骨架（RemoteNet `cmd/gui/ui.go`）

```
Border(
  top    = 自绘顶栏（46px，固定在滚动区之外）
  bottom = 底栏 footerBox（即时提示 + 导出诊断/查看日志，永远可见）
  center = VScroll( CustomPaddedLayout(0, bodyPadBottom=32, 0, 0) 包住的 body )
)
body = VBox( heroSlot(深色状态面板), cardSlot(配置卡), cardSlot(设置卡), cardSlot(证书卡) )
```

三条不变量：

1. **顶栏和底栏在滚动区之外**——滚动的是中间的卡片区。底栏的"导出诊断/查看日志"因此永远可见，
   不会被内容顶出去。
2. **底栏上方的 32px 留白（`bodyPadBottom`）是"卡片不被滚动区裁掉一半"的余量**，
   同样参与窗口默认高度的计算。`cards_test.go` 会把它锁住。
3. **滚动区的高度不能用 `VScroll.MinSize().Height`**（Fyne 给的是常量 32），要自己按内容算。

## 三组间距，三个出处

| 间距 | 值 | 出处 | 说明 |
|---|---|---|---|
| 一般卡片之间 | 5 | `theme.Padding()` | VBox 自动加的一行行距 |
| 卡片内部左右内缩 | `cardPadH = 5` | `cardSlot()` | 上下是 `cardPadV = 0` |
| 深色状态卡 ↔ 配置卡 | **8** | `heroSlot()` 的底 padding `extra = 8 − theme.Padding()` | 用户指定"稍微大一点" |

**深色卡与配置卡之间为什么是"补差额"而不是"直接在 VBox 里插一个 3px 的占位对象"**：
插占位对象会多出一整行行距，实测得到 13px 而不是 8px（5 + 3 + 5）。
槽位 padding 在卡片矩形之外、也参与 MinSize，所以"深色卡底 → 白卡顶"正好 5 + 3 = 8px。
想再调这个间距，只改 `heroCardGap` 一个数。

**深色状态面板是通栏的**：它比白卡左右各宽 5px（不被 `cardPadH` 内缩）。这是刻意设计，
给 `heroSlot` 补左右 padding 会破坏它。

## 标签列宽：每张卡自己算

`labelColWidth = 该卡片最长标签 + labelGap(8)`。

原来是一个全局常量 `labelColWidth = 92`（按"服务器域名"5 个字定的），结果标签短的卡片
在标签和输入框之间留出一大片空白。改成"按卡算"之后，"连接配置"的标签列就只留 8px 缝。
`labels_test.go` 会断言每张卡的列宽减最长标签宽正好等于 `labelGap`。

推论：**加标签要顺手检查这张卡的列宽**；标签变长，列宽自动跟着变，无需手工调数字。
另外标签文案要短——"服务器域名"这种 5 字标签会把它所在的卡片整体推宽，能缩就缩
（用户把"服务器域名"改成了"服务域名"就是这个原因）。

## 窗口尺寸策略（`cmd/gui/app.go`）

**默认尺寸**

- 宽 = 内容的最小宽度：`minW := a.w.Content().MinSize().Width`，然后 `Resize(NewSize(minW, minH))`。
  不要写死一个"看着舒服"的宽度——内容变了它就错了。
- 高 = `bodyMinHeight() = body.MinSize().Height + bodyPadBottom + footerBox.MinSize().Height + titleBarH`。

**内容变化时（`fitBody()`）**

- 只在**装不下**时加高：`if need <= sz.Height { return }`。
- **绝不下缩、绝不动宽度**。用户手拖过的高度是他要的；提示文字变长变短都不许动窗口
  （这是明确需求，不是优化）。
- 内容变矮时窗口不变，多出来的部分是底部留白。

**次级窗口**：连接明细窗用 `w.Resize(fyne.NewSize(content.MinSize().Width, 580))`
（`cmd/gui/conns.go`）——宽度跟内容、高度固定 580，因为它的内容是可滚动列表。

## 交互四条

### 1. 长提示走悬停气泡（`cmd/gui/tips.go`）

常驻的长提示会把卡片撑变形或者被截断，所以：

- `newTipButton(label, getText, host)` / `newTipLabel(text, getText, host)` 包一层，
  悬停时在光标旁弹气泡；
- `hoverTip.showTip/tipHover/hideTip` 管气泡生命周期，`wrapTip` 按字符宽度自动折行
  （中英混排不能按字节折）；
- 气泡**不占布局、不改窗口尺寸**；
- 状态圆点 + "连接明细"两段文本合并成一条气泡文案（遥控器式换行拼接），别做成两个气泡。

### 2. 悬停 = 底色加深，不是变灰

见 `design-tokens.md`。红 CTA 被灰罩住会被误读成"按钮失效"。

### 3. 结果反馈走底栏，不弹对话框

测试结果、打开浏览器、推送到 NAS 的结果都写在底栏（`footerBox`）里，随后自动消失。
对话框会打断操作流，而这些都是"操作完成的确认"，不是需要决策的事。

### 4. 文字截断要有明确的"谁让位"

顶栏标题在剩余宽度不足时截断（`…`），不能让标题把右侧菜单挤到一起。
实现是"给标题算出剩余宽度再 `Resize`"，不是让 Fyne 自由抢占。
同理，卡片里的路径/长文本要截断或走气泡，不要让它把卡片顶宽。

## 设计约束的测试守护（`cmd/gui/*_test.go`）

改版面之前先看这些测试，改完之后必须全绿——它们就是"设计已定稿"的可执行版本：

| 测试 | 守什么 |
|---|---|
| `cards_test.go` | 卡片不被滚动区裁掉（底部余量 = `bodyPadBottom`） |
| `labels_test.go` | 每张卡的标签列宽 = 最长标签 + `labelGap` |
| `menu_test.go` | 菜单字号 13、与列表同色（菜单/列表不能有落差） |
| `footbar_test.go` | 底栏提示的存在与自动消失 |
| `tips_test.go` | 气泡折行宽度 |
| `layout_test.go` | 主面板整体尺寸关系 |
| `conns_cols_test.go` | 连接明细列宽 |

跑：`go test ./cmd/gui/`。**改了 vendor 里的 Fyne 渲染代码也要跑**（菜单/按钮的补丁就在 vendor 里）。
