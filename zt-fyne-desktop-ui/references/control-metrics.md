# 控件度量与细节事实（RemoteNet 实测）

这份是"确切数值 + 出处"的速查表：和 `components.md`（长什么样）配合看。
每条都带 `file:line`；Fyne 默认值标注为「默认」；仓库没覆盖的一律落到 `theme.DefaultTheme()` 的浅色变体
（`cmd/gui/theme.go` 的 `quietTheme.Color/Size` 末尾就是这么回落的）。

参考仓库：`D:\ProgramData\projects\ZtRemoteNet`。行号可能随提交漂移，找不准就按符号名 grep。

---

## 1. 滚动条

- 仓库只有两处滚动区：主面板 `cmd/gui/ui.go:258` 的 `container.NewVScroll(inner)`；
  连接明细 `cmd/gui/conns.go:69-71` 的三个 `*widget.List`（rawAll / rawDone / rawFail），
  外面套 `escList` 接管 ESC（`conns.go:405-414`）。没有横向滚动、没有其它 `widget.Scroll`。
- 主题只覆盖了颜色：`ColorNameScrollBar → colBorder #D5D8DD`（`cmd/gui/theme.go:103`、定义 `:32`）。
  尺寸与轨道底色**都没覆盖**。
- Fyne 默认（`vendor/fyne.io/fyne/v2/theme/size.go:259-262,283`）：
  `SizeNameScrollBar = 12`、`SizeNameScrollBarSmall = 3`、`SizeNameScrollBarRadius = 3`；
  浅色轨道 `#DBDBDB`（`theme/color.go:251-252`），滑块为黑 60%（`0x99`）。
- 行为（`vendor/fyne.io/fyne/v2/internal/widget/scroller.go:207-253`）：
  「大」容器（内容明显超出）用 12px 宽轨道 + 圆角 3 的滑块，背景轨道**只在 isLarge 时显示**；
  小容器用 `Small*2 = 6`，轨道隐藏；**未滚动时滑块自动隐藏**（除非 `scrollBarAlwaysVisible`）。
- 结论：滚动条就是「细条 + #D5D8DD」，没有 hover 反馈、没有自定义宽度。
  想改外观只能覆盖上面三个 SizeName + `ColorNameScrollBarBackground`——但先问一遍用户，别顺手改。

## 2. 文件选择器（不用 Fyne 自带，走 Win32 原生）

- 仓库**完全没有** `dialog.NewFileOpen/NewFileSave/ShowFileOpen`（grep 为空）。
  用的是自写的 Win32 封装 `internal/winfile/openfile_windows.go`：
  `OpenFile → GetOpenFileNameW`、`SaveFile → GetSaveFileNameW`（`:96-100`）；
  flags = `ofnHideReadOnly|ofnNoChangeDir|ofnPathMustExist|ofnFileMustExist|ofnExplorer|ofnEnableSizing|ofnDontAddToRes`（`:22-30`，用法 `:75-78`）；
  `hwndOwner = 0`（`:72`）＝ 没有父窗口，所以对话框**不会居中在主窗口上**；
  取消返回 `ErrCanceled`（`:105-107`）；`buildFilter` 用双 NUL 的 UTF-16（`:113+`）。
- 两处调用：
  - `cmd/gui/ui.go:893`（`browseFile` `:891`，按钮 `btnBrowseCA/Cert/Key` `:190-192`）——标题「选择 CA 证书 / 选择客户端证书 / 选择客户端私钥」，过滤 `*.pem;*.crt;*.cer;*.key`；证书目录见 `certDir()` `ui.go:868-882`。
  - `cmd/gui/app.go:790` `winfile.SaveFile("导出诊断", exeDir(), defName, Filter{文本文件, *.txt})`。
- 外观 = **系统原生、不可 theme 定制**。顺带澄清：Fyne 自带的 `dialog/file_windows.go` 是**自绘**对话框，
  只借 `kernel32.GetLogicalDrives` 枚举盘符（`vendor/fyne.io/fyne/v2/dialog/file_windows.go:12-25`）——
  所以"想要原生就用 winfile，不要退回 Fyne 自带对话框"。

## 3. 对话框

- 全部调用点：`app.go:676` `dialog.ShowError`（包在 `showError` `:671-678`）、
  `app.go:685` `dialog.ShowInformation`（`showInfo` `:680-687`）、
  `app.go:694` `dialog.ShowConfirm`（`a.confirm` `:689-697`）；
  `ui.go:990-1004` `dialog.NewForm("生成证书","生成","取消",…)` ——**唯一**带自定义尺寸的对话框
  （`form.Resize(fyne.NewSize(560,280))` `ui.go:1003`）。
- `a.confirm` 的调用点：`ui.go:859` 删除配置、`ui.go:999` 生成证书（覆盖确认）、`ui.go:1050` 尚未连接、
  `ui.go:1287` 续期证书、`ui.go:1304`/`:1361` 推送到 NAS。全部走默认样式，
  没有 `SetConfirmText`、没有 `SetConfirmImportance`、没有自定义尺寸。
- 按钮文案（中文来自 Fyne 内置翻译 `vendor/fyne.io/fyne/v2/lang/translations/base.zh_Hans.json`）：
  确认框 `lang.L("No") → "不"`、`lang.L("Yes") → "是"`（且 `Importance = High`，
  `dialog/confirm.go:46,50`）；信息/错误框 `lang.L("OK") → "好"`（`dialog/information.go:17`）。
  仓库没有调用 `lang.AddTranslations/SetLanguage` → 跟随系统 locale。
- 几何（`vendor/fyne.io/fyne/v2/dialog/base.go:17-18`）：内边距 `padWidth=32 / padHeight=16`；
  圆角 = `SizeNameDialogRadius`（默认 **10**，仓库未覆盖，与卡片同档）；
  按钮居中贴底 `(宽/2 − 按钮宽/2, 高 − 16 − 按钮高)`；
  最小尺寸 = `max(内容,按钮,标题) + 32` 宽、`内容+按钮+标题+theme.Padding()+32` 高。
- **Esc / Enter 不存在**：vendor 的 `dialog` 包没有任何键处理（grep `KeyNameEscape`/`KeyNameReturn`
  在 `dialog/*.go` 与 `widget/popup.go` 里都是空）→ 对话框只能用鼠标点按钮，Esc 不会关闭。
  要加键盘支持得自己在内容上挂键盘处理（或在 PopUp 层处理），别以为默认就有。
- 底色与阴影：`ColorNameOverlayBackground → colSurface`（白卡）、
  `ColorNameShadow = #1F2328 α0x12`（`cmd/gui/theme.go`）。

## 4. 菜单（顶栏下拉 + 托盘）

- 顶栏下拉：菜单内容在 `cmd/gui/ui.go:273-290`（`fileMenu` / `helpMenu`）——
  文件：生成证书… / 续期证书… / 推送到 NAS… / 打开证书目录 / 打开配置目录 / ─ / 连接明细… / 导出诊断 / 查看日志 / ─ / 退出；
  帮助：使用说明 / 关于。
  挂载在自绘顶栏：`cmd/gui/titlebar_windows.go:232-240` 的 `newBarMenuButton` →
  `widget.NewPopUpMenu(m, c).ShowAtPosition(fyne.NewPos(pos.X, pos.Y+b.Size().Height))`（`:239`，紧贴按钮下方）；
  顶栏按钮固定宽高 `56×32`（`titlebar_windows.go:~160`）。
- 菜单项文字：vendor 侧加了 `widget.MenuTextSizeName`（`vendor/fyne.io/fyne/v2/widget/menu_item.go:22-24`，
  原为 `SizeNameText = 14`），主题里同名映射为 **13 号等宽**
  （`cmd/gui/theme.go:19-21`；渲染处 `menu_item.go` 的 `refreshText` 用 `TextStyle{Monospace:true}`）。
  项高：`MinSize = 文字 + (innerPad*2 + checkSpace, innerPad*2 − 2)`，`innerPad = SizeNameInnerPadding = 8`
  → 垂直内边距 **14px**；高亮块 inset 硬编码 **1.5**；背景圆角 = `SizeNameMenuRadius`（默认 **3**，未覆盖）。
- 弹层行距：`vendor/fyne.io/fyne/v2/widget/menu.go:333` 的 `[RemoteNet patch] menuBoxLayout` 把行距改成 **0**
  （原为 `theme.Padding()`）；弹层高度受画布高度限制（`menu.go:249-256`）。
  项 hover 底色 = `ColorNameFocus = #DEE2E8`；弹层底 = `ColorNameMenuBackground → colSurface`。
- 托盘菜单：`cmd/gui/tray.go:21-41`（显示主界面 / 连接|断开连接 / 系统代理|关闭系统代理 / 启动浏览器 / ─ / 连接明细 / ─ / 退出），
  `desk.SetSystemTrayMenu(a.trayMenu)`（`:41`），动态文案在 `refreshTray`（`:59-77`）。
- **托盘菜单是 Win32 原生菜单**（`vendor/fyne.io/systray/systray_windows.go:485-511` `CreatePopupMenu` +
  `SetMenuInfo(MIM_APPLYTOSUBMENUS)`；`:602-620` `SetMenuItemInfoW`）→ 项高、字阶、内边距全由系统决定，
  **theme 管不到**。曾经有人（模型）顺手把托盘菜单放大，被用户明确否掉——保持原生。
- 仓库没有自绘菜单渲染器，也没有右键上下文菜单。

## 5. 气泡 tip（`cmd/gui/tips.go`）

- 常量：`tipMaxWidth = 420`（`:18`）、`tipDelay = 600ms`（`:20`）、`tipJitter = 6`（`:22`）。
- 本体：`widget.NewPopUp(container.NewPadded(t.lbl), cnv)`（`:126`）；
  文字用 `theme.SizeNameCaptionText`（主题里 = **12**）；折行按 rune 宽度（13 全角 / 7 半角，`:172-186`）。
- 圆角与内边距来自 PopUp 默认：`SizeNamePopupRadius` 默认 **5**、内边距 `SizeNameInnerPadding = 8`
  （`vendor/fyne.io/fyne/v2/widget/popup.go:113-115,179-182,212-214`）；底色 = `ColorNameOverlayBackground → colSurface`。
  → **气泡不是圆角胶囊，是 5px 圆角的白方块**；想更圆要覆盖 `SizeNamePopupRadius`（会影响所有弹层）。
- 定位：先 `pos + (14, 20)`（`:130`）；右边界 `画布宽 − 气泡宽 − 4`、下限 4；
  下方放不下就上翻 `y = pos.Y − 气泡高 − 8`、下限 4（`:132-143`）。
- 出现时机：`time.AfterFunc(tipDelay)` + jitter 去抖（`:63-90`）→ **悬停 600ms 才出现**，快速划过不弹。
- 组件：`tipButton` / `tipLabel`（`:250+`）、`tipImage`（`cmd/gui/tappabletext.go`，`tipImageSize = 24`）；
  `tappableText` 自己实现 `MouseIn/Moved/Out`（`tappabletext.go:56-88`）。

## 6. 鼠标指针

- `desktop.PointerCursor`（手型）调用点：`cmd/gui/titlebar_windows.go:272` —— 顶栏「文件 / 帮助 / ─ / ✕」。
- 缩放热区：`titlebar_windows.go:382-391` 的 `resizeGrip.Cursor()` 返回 `g.cur`；
  实例分别是 `:456` `HResizeCursor`（右）、`:457` `VResizeCursor`（下）、`:458` `NWSEResizeCursor`（右下角）。
- `cmd/gui/tappabletext.go` 里两个自定义组件都显式给了光标（并带 `desktop.Cursorable` 编译期断言）：
  - `tappableText.Cursor() = PointerCursor`（**可点**：顶部流量行 `cmd/gui/ui.go:70`、连接明细三列
    `cmd/gui/conns.go:156-158` + `:216` 挂 `OnTapped`）——手型是这里“能点”的唯一暗示。
    commit `cea4dca` 补上；之前它没覆写 `Cursor()`，是箭头。
  - `tipImage.Cursor() = DefaultCursor`（**不可点**：状态圆点只悬停出气泡、点了没反应）。
    曾经注释写“悬停手型”而代码返回箭头，现已按实际行为改注释——别把圆点改成手型，那是误导。
  - 这两条约定由 `cmd/gui/tips_test.go` 的 `TestHoverCursors` 锁住。
- 其它控件（按钮、输入框、勾选、菜单项）仓库未显式设置，交给 Fyne 与控件默认。

## 7. 间距与几何速查

| 项 | 值 | 出处 |
|---|---|---|
| 全局行距 | `theme.Padding() = 5` | `cmd/gui/theme.go`（Size 覆盖） |
| 控件内边距 | `SizeNameInnerPadding = 8`（未覆盖，Fyne 默认） | `theme/size.go:253` |
| 深色卡 ↔ 下一张卡 | 8（`heroSlot` 补差额 3 + 行距 5） | `cmd/gui/ui.go` 的 `heroSlot`/`heroCardGap` |
| 卡片内缩 | `cardPadV = 0`、`cardPadH = 5` | `cmd/gui/ui.go` 的 `cardSlot` |
| 标签 ↔ 控件 | `labelGap = 8` | `cmd/gui/ui.go` |
| 底部余量 | `bodyPadBottom = 32` | `cmd/gui/ui.go` |
| 多行输入最小高 | `directEntryHeight = 56`（代理例外 ≥ 88） | `cmd/gui/ui.go` |
| 顶栏 | `titleBarH = 46`、`barSidePad = 10`、`barLogoSize = 28`、`gripThickness = 5`、`gripCorner = 14` | `titlebar_windows.go:56-62` |
| 菜单项垂直内边距 | 14（`8*2 − 2`）；菜单行距 0；高亮 inset 1.5 | vendor `widget/menu_item.go`、`widget/menu.go:333` |
| 顶栏下拉偏移 | 紧贴按钮下方（按钮高 32） | `titlebar_windows.go:239` |
| 气泡偏移 | `+(14, 20)`；右边距 4；上翻时 `−8`；下限 4 | `cmd/gui/tips.go:130-143` |

圆角汇总（一眼看清"几档"）：

| 对象 | 圆角 | 来源 |
|---|---|---|
| 按钮 / 输入框 / 选中 | **8** | `theme.go` Size 覆盖（ButtonRadius、InputRadius、SelectionRadius） |
| 卡片 | **10** | `cmd/gui/ui.go` 自绘矩形（不走 `SizeNameCardRadius`，Fyne 默认 5） |
| 对话框 | **10** | Fyne 默认 `SizeNameDialogRadius`（未覆盖） |
| 弹层 / 气泡 | **5** | Fyne 默认 `SizeNamePopupRadius`（未覆盖） |
| 菜单 | **3** | Fyne 默认 `SizeNameMenuRadius`（未覆盖） |
| 滚动条 | **3** | Fyne 默认 `SizeNameScrollBarRadius`（未覆盖） |

仓库**有意不覆盖**、因而保持 Fyne 默认的尺寸（改之前先问为什么当初没覆盖）：
`SizeNameCardRadius=5`、`SizeNameDialogRadius=10`、`SizeNamePopupRadius=5`、`SizeNameMenuRadius=3`、
`SizeNameScrollBar=12 / Small=3 / ScrollBarRadius=3`、`SizeNameInnerPadding=8`、
`SizeNameHeadingText=24`、`SizeNameInnerWindowRadius=5`（无边框窗口用不到）。
