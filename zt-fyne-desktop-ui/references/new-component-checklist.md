# 新控件接入 checklist

给 RemoteNet 客户端**新增任何控件或交互元素**时，按这份清单逐条走一遍。每一步都对应仓库里已有的做法，
照抄即可；跳过任何一步，视觉上就会"跑偏"，而跑偏之后用户是看得出来的。

> 约定：`ui.go` = `cmd/gui/ui.go`（界面组装），`theme.go` = `cmd/gui/theme.go`（色板/度量），
> 测试 = `cmd/gui/*_test.go`（设计约束测试，改样式必须同步改）。

## 0. 先分类，再动手

| 控件族 | 典型用途 | 既有构造（照用） |
|---|---|---|
| 主行动按钮 | 连接、启动 | `accentButton` / `a.btnConnect` |
| 危险操作按钮 | 清理代理、删除配置 | `a.btnDelete`（`colDanger` 描边，非实心） |
| 次级文本按钮 | 刷新、复制、打开 | `textButton`（`labelSizeSmall`，无底色） |
| 数据输入 | 服务地址、端口、证书路径 | `widget.Entry` + `labelCo()` 造标签行 |
| 布尔选择 | 开机自启、跳过校验 | `widget.Check` / `widget.RadioGroup` |
| 只读数据/展示 | 状态点、日志行、说明文字 | `monoText` / `hintText` + 卡片 |

**不要新造一套外观**：一族里已有控件怎么画，新控件就怎么画；族里没有先例的，按第 2-6 步定值后再落地。

## 1. 形状与尺寸（照抄，不要重算）

- 高度：输入框 / 下拉框 / 按钮 = **36px**；复选框、单选框行 = **32px**；菜单项 = **40px**（文字量 14px，是被压过的，别再改）
- 圆角：控件 **8px**；卡片 **10px**
- 内边距：控件左右 **12px**、上下 **8px**；卡片内 = `cardPadV` / `cardPadH`
- 图标/复选框图形：**16px**，与文字基线对齐

## 2. 六种状态，一个都不能少

| 状态 | 做法 | 出处 |
|---|---|---|
| 正常 | 用令牌取色，不写字面量 | `theme.go` |
| 悬停 | **叠色不换色**：半透明黑 14%（`colBtnHover`）叠在原底色上；禁止不透明浅灰覆盖 | `theme.go:37`、`vendor/.../widget/button.go:371-392` |
| 按压 | 比悬停再深一档（黑 24%）；主按钮才做 | 建议值，见 `snippets.md` |
| 焦点 | 键盘 Tab 到达时才有视觉反馈；**勾选/单选的焦点大圆刻意透明**，别"修复" | `vendor/.../widget/check.go:175` |
| 禁用 | 底色更淡（`#F7F8FA`）+ 文字灰（`#6B7280`），对比度 ≥ 4.5:1，且要和"可用"区分得开 | `theme.go` 次级按钮注释 |
| 选中 | 主色 8% 底（`colAccentBg`）+ 主色文字/描边 | `theme.go:39` |

## 3. 光标

- 可点的（按钮、超链接、可点文字、状态点气泡触发区）→ `desktop.CursorPointer`
- 可编辑的 → `desktop.CursorText`；其余保持箭头
- 光标要挂到**外层容器**上（挂到内部 `Label` 上会有一部分区域不响应悬停）

## 4. 间距（最容易翻车的地方）

- 卡片**内**：改 `cardPadV` / `cardPadH`（`ui.go` 的 `cardSlot`），不要动别处
- 标签与控件之间：`labelGap`（`ui.go` 的 `labelCo()`）
- 卡片**之间**：间距来自 `theme.Padding()`（= 5px），是全应用统一的；想在某两卡之间更大，
  用 `heroSlot()` / `cardSlot()` 那种"槽位补差额"的写法（`extra = 目标 − theme.Padding()`），
  **绝不要**在 `VBox` 里插一个高度占位对象——那会多出一整行行距，实测会从 8px 变 13px
- 卡片通栏 vs 缩进：状态卡（hero）刻意比白卡两侧各宽 5px，新卡片默认按白卡内缩，别改

## 5. 字阶

- 控件里的数据/命令（地址、端口、日志、代码）：**13 号等宽**（`labelSizeName` + monospace）
- 说明/次要文字：12 号；小标题：13 号加粗；卡片标题：15 号加粗
- 不要依赖 Fyne 默认按 role 取字号——本项目覆盖了度量，一律用 `theme.go` 的常量

## 6. 颜色

- 只允许用 `theme.go` 的令牌；确实需要新颜色时：先加令牌（含注释说明用途）、再在文档里登记，最后才用
- 新增/修改颜色后必须检查：白卡上的对比度 ≥ 4.5:1、深色面板上的对比度 ≥ 4.5:1
- 一个颜色不要同时承担两种语义（例如"错误红"和"主色红"要分开）

## 7. 窗口尺寸

- 默认窗口只**加高**：改 `bodyMinHeight()` / `fitBody()` 会自然长高；不要为了新控件改默认宽度
- 新增最小高约束写在 `titlebar_windows.go` 的窗口最小尺寸处
- 内容变长要能滚动（`container.NewVScroll`），不要把窗口撑爆

## 8. 键盘与可访问性

- Tab 顺序 = 视觉顺序；`Esc` 关闭浮层/取消；`Enter` 触发主行动
- 只读信息要能被读屏拿到（用 `widget.Label` 而不是纯 `canvas.Text`）
- 危险操作要有确认（`a.confirm` / `dialog.ShowConfirm`），文案里写清后果

## 9. 测试（改样式必须同步）

```bash
export PATH="/c/Users/ELEX-ZT/go-sdk/go/bin:$PWD/.toolchain/root/ucrt64/bin:$PATH"
go test ./cmd/gui/
```

- 设计约束测试在 `cmd/gui/*_test.go`（标签只读、卡片槽位、间距、字体、颜色令牌……）
- 新增控件至少要有一条：**字体/颜色/间距用了令牌而不是字面量**、**没有在 VBox 插占位对象**

## 10. 验证与交付

```bash
go build -ldflags "-H windowsgui" -o dist/RemoteNet-Portable/gui.new.exe ./cmd/gui
powershell -NoProfile -ExecutionPolicy Bypass -File "$TEMP/swap_gui.ps1"   # 杀→换名→重启，不动系统代理
```

- 像素复核：`scripts/hscan.ps1`（量横向色段）、`scripts/gap_analyze.ps1`（量卡片缝）、`scripts/shadow_probe.ps1`（量投影）
- 换 exe 前确认新版真跑起来了（`scripts/wininfo.ps1` 看窗口样式/客户区）
- 提交按主题分开（一个主题一个 commit，`conventional commits` 风格）
