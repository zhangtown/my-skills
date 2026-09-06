---
name: fyne-gui-dev-cn
description: Fyne 跨平台 GUI 应用开发。当用户需要创建、修改、调试、或理解 Fyne GUI 应用时使用此技能。触发场景：提到 fyne、GUI 桌面应用、跨平台界面、自定义 Widget、fyne 布局、数据绑定、widget.New*/container.New*/app.New* 等 Fyne API、Go 语言图形界面开发。即使用户没有明确说"fyne"，只要在做 Go GUI 开发就应该考虑此技能。
---

# Fyne GUI 应用开发

Fyne 是纯 Go 实现的跨平台 GUI 框架，基于 OpenGL ES 2.0 硬件加速渲染。
核心设计：**声明式 Widget + 响应式数据绑定**，同一套 API 覆盖 Windows/macOS/Linux/iOS/Android/WebAssembly。

## Fyne 生态系统

核心框架 `fyne.io/fyne/v2` 提供跨平台 GUI 基础能力。以下周边仓库按需选用：

| 仓库 | 用途 | go module |
|------|------|-----------|
| **fyne-x** | 社区扩展包：额外 Widget（FileTree、CompletionEntry、AnimatedGif、Map、HexWidget、NumericalEntry）、ResponsiveLayout、About 对话框、Adwaita 主题 | `fyne.io/x/fyne` |
| **fyne-cross** | Docker 交叉编译：一条命令将 Fyne 应用打包到 Windows/macOS/Linux/Android/iOS/FreeBSD | `github.com/fyne-io/fyne-cross` |
| **terminal** | 终端模拟器 Widget：ANSI 转义序列、鼠标、选择/复制、交替屏幕缓冲 | `github.com/fyne-io/terminal` |
| **systray** | 跨平台系统托盘（无 GTK 依赖）：图标、菜单、点击事件 | `fyne.io/systray` |
| **tools** | fyne CLI：`go run fyne.io/tools/v2/cmd/fyne` — 构建、打包、资源嵌入 | `fyne.io/tools/v2` |
| **refyne** | UI 序列化：JSON 导入/导出、Go 代码生成、属性编辑器 | `github.com/fyne-io/refyne` |
| **gl-js** | OpenGL ES 2 绑定（WebGL 后端 + Windows 支持）— 内部依赖，通常不直接使用 | `github.com/fyne-io/gl-js` |
| **defyne** | 实验性 IDE（已由 Apptrix.ai 取代），JSON 序列化工作已拆分到 refyne | `github.com/fyne-io/defyne` |

如需浏览本地源码，用 `go list -m -json fyne.io/fyne/v2` 查找模块路径。

## 核心原则

1. **容器组合 > 绝对定位** — 使用 `container.New*` 系列函数构建布局
2. **数据绑定优先** — 优先用 `binding` 包实现 UI 自动更新，而非手动操作 Widget
3. **线程安全** — 所有 UI 操作必须在主 goroutine 中，通过 `fyne.Do()` / `fyne.DoAndWait()` 调度
4. **Widget 与 Renderer 分离** — Widget 持有状态，Renderer 负责绘制
5. **测试优先** — 使用 `fyne.io/fyne/v2/test` 包进行内存中的 UI 测试

## 最小应用

```go
package main

import (
    "fyne.io/fyne/v2"
    "fyne.io/fyne/v2/app"
    "fyne.io/fyne/v2/container"
    "fyne.io/fyne/v2/widget"
)

func main() {
    a := app.New()              // 或 app.NewWithID("com.example.app")
    w := a.NewWindow("Title")
    w.SetContent(container.NewVBox(
        widget.NewLabel("Hello"),
        widget.NewButton("Click", func() {
            // handle click
        }),
    ))
    w.Resize(fyne.NewSize(400, 300))
    w.ShowAndRun()              // show + app.Run()
}
```

## 框架接口（理解并可能实现）

Fyne 的核心是一套接口合约。内置组件全部实现了这些接口，自定义组件也需要实现它们。理解这些接口是正确使用 Fyne 的基础。

```
层次:                    你做什么:
──────────────────────────────────────────
fyne.App          — 应用程序入口         调用 app.New()
fyne.Window       — 窗口管理             调用 w.SetContent() / w.Show()
fyne.Canvas       — 画布（焦点、缩放）    调用 c.Focus() / c.SetOnTypedKey()
fyne.Layout       — 布局算法             内置布局直接用，自定义布局实现此接口
fyne.Container    — 容器（对象的集合）    调用 container.New*()，通常不直接使用
fyne.Widget       — 组件接口             继承 BaseWidget，实现 CreateRenderer()
fyne.WidgetRenderer — 渲染器接口         实现 Destroy/Layout/MinSize/Objects/Refresh
fyne.CanvasObject — 最底层基础接口       所有可绘制对象必须实现（MinSize/Position/Size/Visible...）
```

**Widget 必须实现的功能接口**（按需选择，不是都要实现）：
`Tappable` → 点击 | `DoubleTappable` → 双击 | `SecondaryTappable` → 右键
`Focusable` → 键盘输入 | `Scrollable` → 滚轮 | `Draggable` → 拖拽
`Disableable` → 启用/禁用 | `Shortcutable` → 快捷键响应

## 内置组件（开箱即用）

以下均由框架提供，直接调用构造函数即可。它们内部实现了上述框架接口。

### 基础 Widget（完整列表见 `references/api-reference.md`）

```go
// 最常用的 10 个
widget.NewLabel("text")                    // .Selectable = true 可选文本 (v2.6+)
widget.NewButton("text", func() {})
widget.NewEntry()                          // .Text, .OnChanged
widget.NewCheck("label", func(bool) {})    // .Partial = true 半选 (v2.6+)
widget.NewSelect([]string{"a","b"}, func(string) {})
widget.NewSlider(min, max)
widget.NewProgressBar()
widget.NewRichText(segments...)            // 多段样式富文本
widget.NewRichTextFromMarkdown(content)    // Markdown → RichText
widget.NewCard(title, subtitle, content)
```

表单（`widget.NewForm`）、工具栏（`widget.NewToolbar`）、日历（`NewCalendar` v2.6+）、Markdown 渲染（`NewMarkdown`）等其他 Widget 见 `references/api-reference.md`。

### 虚拟滚动（大数据集，必须使用）

```go
list := widget.NewList(
    func() int { return rowCount },                     // 行数
    func() fyne.CanvasObject { return widget.NewLabel("template") }, // 模板
    func(id widget.ListItemID, obj fyne.CanvasObject) { // 更新行
        obj.(*widget.Label).SetText(fmt.Sprintf("Row %d", id))
    })
// 类似：widget.NewTable / widget.NewTree
```

### 数据绑定 Widget（响应式 UI）

```go
data := binding.NewString()
widget.NewEntryWithData(data)       // 输入 ↔ data
widget.NewLabelWithData(data)       // data → 自动更新
widget.NewCheckWithData("label", binding.NewBool())
widget.NewSliderWithData(min, max, binding.NewFloat())
widget.NewListWithData(dataList, createFn, updateFn)
```

## 容器与布局

```go
import "fyne.io/fyne/v2/container"

// 最常用容器（完整列表见 references/api-reference.md）
container.NewVBox(objs...)                   // 垂直
container.NewHBox(objs...)                   // 水平
container.NewBorder(top, bottom, left, right, center...) // 边框
container.NewGridWithColumns(cols, objs...)  // 按列网格
container.NewAdaptiveGrid(rowcols, objs...)  // 自适应网格
container.NewStack(objs...)                  // 堆叠
container.NewCenter(objs...)                 // 居中
container.NewPadded(objs...)                 // 标准 padding

// 特殊功能
container.NewScroll(content)                 // 滚动
container.NewHSplit(left, right)             // 水平分割
container.NewVSplit(top, bottom)             // 垂直分割
container.NewAppTabs(items...)               // 标签页
container.NewNavigation(content)             // 导航（返回按钮）(v2.7+)
container.NewClip(content)                   // 裁剪溢出 (v2.7+)
```

弹性占位符：
```go
container.NewHBox(layout.NewSpacer(), widget.NewButton("OK", fn))
```

GridWrap / RowWrap / Max / DocTabs 等见 `references/api-reference.md`。

## 数据绑定

```go
import "fyne.io/fyne/v2/data/binding"

// goroutine-safe — 可在任何 goroutine 中读写
s := binding.NewString()               // .Get() / .Set(val)
b := binding.NewBool()
i := binding.NewInt()

// 外部绑定：绑定到已有变量（修改变量后需调用 .Reload()）
binding.BindString(&myVar)

// 转换
binding.IntToString(intBinding)
binding.SPrintf("Count: %d", intBinding)
```

完整 API（集合绑定、列表绑定、树绑定、URI 绑定、Preference 绑定等）见 `references/api-reference.md` 数据绑定 API 部分。

## i18n 翻译

```go
import "fyne.io/fyne/v2/lang"

title := widget.NewLabel(lang.L("My App Title"))          // 默认值即 key
title := widget.NewLabel(lang.X("win.title", "My Title")) // 显式 key + 默认值
age := widget.NewLabel(lang.N("{% raw %}{{.Years}}{% endraw %} years old", n, map[string]any{"Years": n}))
```

翻译文件为 JSON，使用 `//go:embed` 嵌入后用 `lang.AddTranslationsFS` 加载。完整用法见 `references/best-practices.md` i18n 翻译章节。

## Canvas 原始图形

```go
import "fyne.io/fyne/v2/canvas"

canvas.NewRectangle(color)              // 矩形（常用作背景）
canvas.NewCircle(color)
canvas.NewLine(color)                   // 必须用 *canvas.Line（指针！）
canvas.NewText("text", color)           // 必须用 *canvas.Text（指针！）
canvas.NewImageFromFile(path)
canvas.NewLinearGradient(start, end)
```

**v2.7+ 新增**：`NewSquare`、`NewArc`/`NewPieArc`/`NewDoughnutArc`、`NewPolygon`、Rectangle 圆角（`CornerRadius`/`Aspect`）、Image 填充模式（`FillMode`/`CornerRadius`）。完整列表和属性见 `references/api-reference.md` Canvas 原始图形 + Rectangle 属性 + ImageFill 模式部分。

## 自定义 Widget

```go
type MyWidget struct {
    widget.BaseWidget
    Text string
}

func NewMyWidget(text string) *MyWidget {
    w := &MyWidget{Text: text}
    w.ExtendBaseWidget(w)  // 必须！设置内部 impl 指针
    return w
}

func (w *MyWidget) CreateRenderer() fyne.WidgetRenderer {
    bg := canvas.NewRectangle(theme.Color(theme.ColorNameButton))
    label := canvas.NewText(w.Text, theme.Color(theme.ColorNameForeground))
    return &myRenderer{bg: bg, label: label, w: w,
        objs: []fyne.CanvasObject{bg, label}}
}

type myRenderer struct {
    bg, label fyne.CanvasObject
    w         *MyWidget
    objs      []fyne.CanvasObject
}

func (r *myRenderer) Destroy() {}
func (r *myRenderer) Layout(size fyne.Size) { r.bg.Resize(size) }
func (r *myRenderer) MinSize() fyne.Size    { return fyne.NewSize(100, 30) }
func (r *myRenderer) Objects() []fyne.CanvasObject { return r.objs }
func (r *myRenderer) Refresh() {
    r.label.(*canvas.Text).Text = r.w.Text
    r.label.Refresh()
}

// 可选实现 Tappable 等接口
func (w *MyWidget) Tapped(ev *fyne.PointEvent) { /* ... */ }
```

**5 条关键规则**：
1. 构造函数中 **必须** 调用 `ExtendBaseWidget(w)`
2. `Objects()` **必须** 返回非空、元素非 nil 的切片
3. 所有 Canvas 对象使用 **指针**（`*canvas.Line` 不是 `canvas.Line`）
4. **禁止** 在 `Layout()` 中调用 `Refresh()`
5. `MinSize()` 基于子对象计算，**不要硬编码**

## 线程模型

```go
// 后台 goroutine 安全更新 UI
go func() {
    result := expensiveWork()
    fyne.Do(func() {
        label.SetText(result)     // ✅ 安全
    })
}()

// 等待执行完成
var title string
fyne.DoAndWait(func() {
    title = window.Title()
})
```

数据绑定 API 在任何 goroutine 中安全，回调自动通过 `fyne.Do` 调度。

## 对话框

```go
dialog.ShowInformation("Title", "Msg", parent)
dialog.ShowConfirm("Title", "Msg", func(ok bool) {}, parent)
dialog.ShowError(err, parent)
dialog.ShowFileOpen(callback, parent)
// 其他：FileSave、FolderOpen、Custom、Form、Entry、ColorPicker、Progress
```

完整 API 列表见 `references/api-reference.md` 对话框 API 部分。

## 菜单与快捷键

```go
// 窗口菜单栏
item := fyne.NewMenuItem("Copy", nil)
item.Shortcut = &fyne.ShortcutCopy{Clipboard: w.Clipboard()}
w.SetMainMenu(fyne.NewMainMenu(
    fyne.NewMenu("File", fyne.NewMenuItem("Quit", func() { a.Quit() }))))

// 自定义快捷键
w.Canvas().AddShortcut(&desktop.CustomShortcut{
    KeyName: fyne.KeyS, Modifier: fyne.KeyModifierControl,
}, func(s fyne.Shortcut) {})
```

完整 API（ActionItem、Separator、DisabledItem、Shortcut 类型等）见 `references/api-reference.md` 菜单 API 和快捷键部分。

## 系统托盘

```go
if desk, ok := a.(desktop.App); ok {
    desk.SetSystemTrayMenu(fyne.NewMenu("Tray",
        fyne.NewMenuItem("Show", func() { w.Show() })))
}
w.SetCloseIntercept(func() { w.Hide() }) // 关闭隐藏，不退出
```

生命周期管理（自定义图标、隐藏/显示、退出处理）见 `references/best-practices.md` 系统托盘生命周期章节。

## 编译与部署

常用编译标签：`mobile`（模拟移动端）、`debug`（布局边界）、`hints`（优化建议）、`no_emoj`（减小体积）。完整列表见 `references/deployment.md`。

```bash
fyne package -os darwin -icon myapp.png   # 桌面打包
fyne package -os android -app-id com.e.ap # 移动端打包
fyne serve                                 # Web 本地测试
fyne-cross linux -output myapp ./          # 交叉编译（推荐）
```

完整交叉编译配置、应用商店分发（macOS/iOS/Android）见 `references/deployment.md`。

## 主题与样式

```go
// TextStyle
fyne.TextStyle{Bold: true, Italic: false, Monospace: false, TabWidth: 4}

// 自定义主题 — 实现 Theme 接口（Color / Font / Icon / Size），回退到 DefaultTheme()
type myTheme struct{}
func (t myTheme) Color(name fyne.ThemeColorName, v fyne.ThemeVariant) color.Color {
    if name == theme.ColorNamePrimary { return color.NRGBA{R:70, G:130, B:255, A:255} }
    return theme.DefaultTheme().Color(name, v)
}
app.Settings().SetTheme(&myTheme{})
container.NewThemeOverride(&myTheme{}, content) // 局部覆写
```

完整自定义主题模板、颜色/尺寸/字体/图标常量查询见 `references/api-reference.md` 样式与主题部分。

## 测试

```go
import "fyne.io/fyne/v2/test"

// 模拟交互
test.Tap(btn)
test.TapCanvas(c, pos)
test.Type(entry, "text")                // 先 FocusGained，再逐 rune 输入
test.Drag(c, pos, deltaX, deltaY)
test.Scroll(c, pos, deltaX, deltaY)
test.MoveMouse(c, pos)
test.FocusNext(c) / test.FocusPrevious(c)

// 验证渲染
r := test.WidgetRenderer(widget)
objs := r.Objects()                     // 检查渲染对象
markup := test.RenderObjectToMarkup(o)  // 快照 (v2.6+)

// 测试环境
c := test.NewCanvas()
a := test.NewApp()
// CI: go test -tags ci ./...
```

## 常见错误速查

| 问题 | 原因 | 解决 |
|------|------|------|
| Widget 不可见 | `Objects()` 空/nil，忘记 `ExtendBaseWidget` | 检查 CreateRenderer 和构造器 |
| 点击无响应 | 尺寸为 0，或未实现 `Tappable` | 手动 Resize 或实现 `Tapped` |
| `panic: Layout is nil` | `Resize()` 在 Renderer 初始化前调用 | 放入容器后再 Resize |
| `panic: Canvas is nil` | Widget 不在窗口层级中 | 先 `SetContent` / `Show` |
| 打包后资源 404 | 使用了文件系统路径 | `fyne bundle` 嵌入为 Go 代码 |
| Grid 有空白 | `Hide()` 的对象仍占格 | 从 `Objects` 中 `Remove` |
| 数据绑定不更新 | 外部变量修改后未 `Reload()` | 调用 `b.Reload()` |
| 非可见 Widget MinSize 为 0 | 框架优化：不可见 Widget 无渲染器 | 放入 Canvas 中再测试 |
| v2.6+ `fyne.Do called from main goroutine` | 在事件回调（已主 goroutine）中调了 `fyne.Do` | 去掉事件回调中的 `fyne.Do`，直接操作即可 |

## 无从下手？先读这些

当 references 覆盖不到、需要探索 Fyne 源码时，使用以下方法自行查找答案。

### 包路径 → 文件系统映射

Go 包路径 `fyne.io/fyne/v2/widget` 对应的文件系统路径通过以下两种方式找到：

```bash
# 方式一：go list（精准，推荐）
FYNE_DIR=$(go list -m -json fyne.io/fyne/v2 | grep '"Dir"' | cut -d'"' -f4)

# 方式二：GOMODCACHE（简单直接，支持通配符）
FYNE_DIR=$(echo $(go env GOMODCACHE)/fyne.io/fyne/v2@*)
# 如果有多个版本，取最新的或指定版本：
FYNE_DIR=$(go env GOMODCACHE)/fyne.io/fyne/v2@v2.5.0
```

获取 `$FYNE_DIR` 后，包路径的后半段就是子目录。例如 `fyne.io/fyne/v2/widget` → `$FYNE_DIR/widget/`，`fyne.io/fyne/v2/canvas` → `$FYNE_DIR/canvas/`。

### 查找 API

```bash
# go doc（首选，无需知道源码路径）
go doc fyne.io/fyne/v2/widget
go doc fyne.io/fyne/v2/widget.Button

# rg 搜索
rg "func.*New.*Pop" "$FYNE_DIR/widget/"
rg "type.*Renderer" "$FYNE_DIR/widget/"
```

### 学习内置 Widget 的实现

找到 `$FYNE_DIR` 后，阅读内置 Widget 源码是最好的学习方式。例如看 `widget` 包下各组件的 `CreateRenderer` 实现：

```bash
rg "ExtendBaseWidget" "$FYNE_DIR/widget/"
rg "CreateRenderer" "$FYNE_DIR/widget/" | head -20
```

### Fyne 代码约定

理解这些约定后，可以从内置 Widget 源码中自行推断未文档化的 API：

- **Widget 构造器**：`New<Name>(requiredParams...) *<Name>`，内部调用 `ExtendBaseWidget(self)`
- **声明式 Widget 和 Renderer 分离**：Widget struct 持有状态，Renderer struct 持有 CanvasObject
- **Renderer 在 `CreateRenderer()` 中创建**并缓存在 `internal/cache` 中
- **命名约定**：`On<Event>` 是回调字段，`Set<Property>` 是 setter，`<Property>()` 是 getter
- **Refresh 触发链**：`widget.Refresh()` → `cache.Renderer(w).Refresh()` → 更新 CanvasObject 状态 → `canvas.Refresh(w)`
- **布局触发链**：`widget.Resize(size)` → `cache.Renderer(w).Layout(size)` → 排列子对象

## 参考资料（按场景查阅）

| 场景 | 查阅文件 | 重点章节 |
|------|---------|---------|
| 不确定用哪个 Widget/API | `references/api-reference.md` | 完整 Widget 列表、Container 列表 |
| 需要完整颜色/图标/字体列表 | `references/api-reference.md` | 样式与主题部分（末尾 TOC） |
| 布局不对/需要响应式设计 | `references/best-practices.md` | 布局模式 |
| 数据绑定不工作 | `references/best-practices.md` | 数据绑定模式 |
| Widget 不显示/崩溃/性能差 | `references/troubleshooting.md` | 先查快速诊断表，再查对应章节 |
| 写自定义 Widget | `references/custom-widget.md` | 完整模板 + 5 条关键规则 |
| 扩展已有 Widget（添加行为） | `references/best-practices.md` | 扩展已有 Widget |
| 实现自定义布局 | `references/best-practices.md` | 自定义布局 |
| 添加应用翻译 (i18n) | `references/best-practices.md` | i18n 翻译 |
| 系统托盘/窗口生命周期 | `references/best-practices.md` | 系统托盘生命周期 + 多窗口进阶 |
| Preferences 持久化设置 | `references/best-practices.md` | Preferences 进阶 |
| 编译标签/交叉编译/打包/分发 | `references/deployment.md` | 对应章节 |
| 单元测试怎么写 | `references/testing.md` | 模拟交互、渲染验证示例 |

上述 references 都覆盖不到时，按照上一节"无从下手？先读这些"的方法探索源码。如果探索源码后仍然无法解决，**向用户报告具体情况并寻求帮助，不得静默猜测。**
