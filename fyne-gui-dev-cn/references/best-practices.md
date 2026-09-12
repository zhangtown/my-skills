# 最佳实践与使用模式

## 目录

- [1. 项目结构](#1-项目结构)
- [2. 布局模式](#2-布局模式)
- [3. 数据绑定模式](#3-数据绑定模式)
- [4. 异步操作模式](#4-异步操作模式)
- [5. 自定义 Widget 深入](#5-自定义-widget-深入)
- [6. 性能优化](#6-性能优化)
- [7. 平台适配](#7-平台适配)
- [8. 窗口管理](#8-窗口管理)
- [9. 资源管理](#9-资源管理)
- [10. 对话框模式](#10-对话框模式)
- [11. Navigation 导航模式](#11-navigation-导航模式)
- [12. Canvas 样式模式](#12-canvas-样式模式)
- [13. Label 可选文本](#13-label-可选文本)
- [14. RowWrap 布局](#14-rowwrap-布局)
- [15. i18n 翻译](#15-i18n-翻译)
- [16. 自定义布局](#16-自定义布局)
- [17. 扩展已有 Widget](#17-扩展已有-widget)
- [18. Preferences 进阶](#18-preferences-进阶)
- [19. 系统托盘生命周期](#19-系统托盘生命周期)
- [20. 多窗口进阶](#20-多窗口进阶)
- [21. 动画](#21-动画)
- [22. 缩放与设备适配](#22-缩放与设备适配)

---

## 1. 项目结构

推荐的 Fyne 项目结构：

```
myapp/
├── main.go              # 入口，app 初始化
├── FyneApp.toml         # 元数据（ID、版本、图标、构建设置）
├── ui/
│   ├── views/           # 页面/屏幕
│   ├── widgets/         # 自定义可复用组件
│   └── theme/           # 自定义主题
├── model/               # 数据模型和业务逻辑
├── bindings/            # 响应式数据绑定
└── go.mod
```

### FyneApp.toml

```toml
[Details]
  ID = "com.example.myapp"
  Name = "My Application"
  Version = "1.0.0"
  Build = 1
  Icon = "Icon.png"

[Migrations]
  fyneDo = true   # v2.6.0+：启用新线程模型
```

## 2. 布局模式

### 2.1 基本页面结构

```go
func mainPage() fyne.CanvasObject {
    header := widget.NewLabel("App Title")
    sidebar := widget.NewList(/* ... */)
    body := widget.NewLabel("Content")
    footer := widget.NewLabel("Status: Ready")

    return container.NewBorder(
        header,               // top
        footer,               // bottom
        sidebar,              // left
        nil,                  // right (不填)
        body,                 // center
    )
}
```

### 2.2 表单布局

```go
func formPage() fyne.CanvasObject {
    nameEntry := widget.NewEntry()
    emailEntry := widget.NewEntry()
    passwordEntry := widget.NewPasswordEntry()

    form := &widget.Form{
        Items: []*widget.FormItem{
            {Text: "Name", Widget: nameEntry},
            {Text: "Email", Widget: emailEntry},
            {Text: "Password", Widget: passwordEntry},
        },
        OnSubmit: func() {
            // 验证并提交
        },
    }
    return form
}
```

### 2.3 自适应网格（响应式）

```go
// rowcols 是横屏时的列数，竖屏时自动变为行数
grid := container.NewAdaptiveGrid(4,
    widget.NewButton("A", nil),
    widget.NewButton("B", nil),
    // ...
)
```

### 2.4 弹性空间

```go
// 利用 layout.Spacer 将按钮推到右侧
toolbar := container.NewHBox(
    layout.NewSpacer(),
    widget.NewButton("Save", saveFn),
    widget.NewButton("Cancel", cancelFn),
)
```

### 2.5 固定大小的 sidebar

```go
sidebar := widget.NewList(/* ... */)
content := widget.NewLabel("Body")

// 左栏固定宽度，右栏占据剩余
split := container.NewHSplit(sidebar, content)
split.Offset = 0.2  // 左栏占 20%
```

## 3. 数据绑定模式

### 3.1 双向绑定（输入 ↔ 显示）

```go
data := binding.NewString()
data.Set("initial")

// 三个 Widget 共享同一个 data source
input := widget.NewEntryWithData(data)
preview := widget.NewLabelWithData(data)
count := widget.NewLabelWithData(
    binding.SPrintf("Length: %d", binding.StringToInt(data)))
```

### 3.2 列表绑定

```go
items := binding.NewStringList()

list := widget.NewListWithData(items,
    func() fyne.CanvasObject {
        return widget.NewLabel("template")
    },
    func(item binding.DataItem, obj fyne.CanvasObject) {
        label := obj.(*widget.Label)
        label.Bind(item.(binding.String))
    })

// 在后台线程更新数据（安全）
go func() {
    results := fetchData()
    items.Set(results)  // 安全——自动通过 fyne.Do 通知
}()
```

### 3.3 外部绑定（绑定到已有变量）

```go
type Model struct {
    Name  string
    Count int
}
m := &Model{Name: "Alice", Count: 5}

nameBinding := binding.BindString(&m.Name)
countBinding := binding.BindInt(&m.Count)

widget.NewLabelWithData(nameBinding)
widget.NewLabelWithData(binding.IntToString(countBinding))

// 外部代码修改 m 后，需要通知：
m.Name = "Bob"
nameBinding.Reload()  // 重要！
```

### 3.4 偏好绑定

```go
a := app.NewWithID("com.example.app")
prefs := a.Preferences()

// 与 Preferences 自动双向同步
themeBinding := binding.BindPreferenceString("theme", prefs)
widget.NewSelectWithData(
    []string{"light", "dark"},
    themeBinding,
    func(val string) {
        // switch theme
    })
```

## 4. 异步操作模式

### 4.1 后台任务 + UI 更新

```go
func loadData(progress *widget.ProgressBar, label *widget.Label) {
    go func() {
        for i := 0; i <= 100; i += 10 {
            time.Sleep(100 * time.Millisecond)
            fyne.Do(func() {
                progress.SetValue(float64(i) / 100.0)
                label.SetText(fmt.Sprintf("Loading... %d%%", i))
            })
        }

        result := computeResult()
        fyne.Do(func() {
            label.SetText(result)
        })
    }()
}
```

### 4.2 使用数据绑定代替手动线程调度

```go
// 更简洁的方式：用数据绑定
progress := binding.NewFloat()
status := binding.NewString()

go func() {
    for i := 0; i <= 100; i += 10 {
        time.Sleep(100 * time.Millisecond)
        progress.Set(float64(i) / 100.0)
        status.Set(fmt.Sprintf("Loading... %d%%", i))
    }
    status.Set("Done!")
}()

// UI 组件自动响应
widget.NewProgressBarWithData(progress)
widget.NewLabelWithData(status)
```

## 5. 自定义 Widget 深入

### 5.1 支持数据绑定的自定义 Widget

```go
type ToggleWidget struct {
    widget.BaseWidget
    Label  string
    Active bool
    OnChanged func(bool)
}

func (w *ToggleWidget) CreateRenderer() fyne.WidgetRenderer {
    return newToggleRenderer(w)
}

func (w *ToggleWidget) Tapped(ev *fyne.PointEvent) {
    w.Active = !w.Active
    if w.OnChanged != nil {
        w.OnChanged(w.Active)
    }
    w.Refresh()  // 触发渲染器更新
}
```

### 5.2 支持自定义 Theme 的 Widget

```go
func (r *myRenderer) MinSize() fyne.Size {
    th := r.w.Theme()   // 获取当前 Theme（可能来自 ThemeOverride 容器）
    pad := th.Size(theme.SizeNamePadding)
    textSize := th.Size(theme.SizeNameText)
    return fyne.NewSize(textSize*10+pad*2, textSize+pad*2)
}

func (r *myRenderer) Refresh() {
    th := r.w.Theme()
    r.bg.FillColor = th.Color(theme.ColorNameBackground, fyne.ThemeVariantLight)
    r.bg.Refresh()
    canvas.Refresh(r.w)
}
```

### 5.3 使用 cache.Renderer 获取子 Widget 渲染器

```go
import "fyne.io/fyne/v2/internal/cache"

func (r *myRenderer) Layout(size fyne.Size) {
    childRenderer := cache.Renderer(r.w.childWidget)
    childRenderer.Layout(size)
}
```

## 6. 性能优化

### 6.1 虚拟滚动

大数据集（>100 行）**必须使用虚拟滚动**：

```go
// ✅ O(可见行数) 复杂度
list := widget.NewList(dataLen, createTemplate, updateRow)

// ❌ O(总行数) — 会一次性创建所有 Widget
for _, item := range items {
    container.Add(widget.NewLabel(item))
}
```

### 6.2 批量更新

```go
// ✅ 批量操纵后一次性 Refresh
data := binding.NewStringList()
newItems := fetchItems()
data.Set(newItems)  // 一次触发

// ❌ 循环内逐个触发
for _, item := range items {
    data.Append(item)  // 每次触发一次 Refresh
}
```

### 6.3 避免不必要的渲染

```go
// Widget 的 Resize 已经做了相等性检查
func (w *BaseWidget) Resize(size fyne.Size) {
    if size == w.Size() {
        return  // 尺寸没变，跳过
    }
    // ...
}
```

## 7. 平台适配

### 7.1 检测设备类型

```go
if fyne.CurrentDevice().IsMobile() {
    // 移动端特定布局
    w.SetContent(container.NewVBox(/* ... */))
} else {
    // 桌面端
    w.SetContent(container.NewHSplit(sidebar, content))
}

if fyne.CurrentDevice().IsBrowser() {
    // WebAssembly 特定处理
}
```

### 7.2 键盘设备判断

```go
if fyne.CurrentDevice().HasKeyboard() {
    // 注册键盘快捷键
    w.Canvas().SetOnTypedKey(func(ev *fyne.KeyEvent) {
        // ...
    })
}
```

## 8. 窗口管理

### 8.1 多窗口

```go
a := app.New()
mainWin := a.NewWindow("Main")
settingsWin := a.NewWindow("Settings")

// 默认：所有窗口关闭 → 退出
// 自定义：拦截关闭
settingsWin.SetCloseIntercept(func() {
    if hasUnsavedChanges {
        dialog.ShowConfirm("Quit?", "Unsaved changes!", func(ok bool) {
            if ok { settingsWin.Close() }
        }, settingsWin)
    } else {
        settingsWin.Close()
    }
})
```

### 8.2 System Tray（桌面功能）

```go
// 如果 driver 支持 desktop 特性
if desk, ok := a.(desktop.App); ok {
    menu := fyne.NewMenu("Tray",
        fyne.NewMenuItem("Show", func() { w.Show() }),
        fyne.NewMenuItem("Quit", func() { a.Quit() }),
    )
    desk.SetSystemTrayMenu(menu)
}
```

## 9. 资源管理

### 9.1 资源嵌入

```bash
# 命令行
fyne bundle -o bundled.go image.png font.ttf

# 或 go:generate
//go:generate fyne bundle -o bundled.go assets/*.png
```

```go
img := canvas.NewImageFromResource(resourceImagePng)
```

### 9.2 自定义主题

```go
type CustomTheme struct{}

func (t CustomTheme) Color(name fyne.ThemeColorName, variant fyne.ThemeVariant) color.Color {
    switch name {
    case theme.ColorNamePrimary:
        return color.NRGBA{R: 70, G: 130, B: 255, A: 255}
    default:
        return theme.DefaultTheme().Color(name, variant)
    }
}

func (t CustomTheme) Font(style fyne.TextStyle) fyne.Resource {
    if style.Monospace {
        return resourceMonospaceFont
    }
    return theme.DefaultTheme().Font(style)
}

func (t CustomTheme) Icon(name fyne.ThemeIconName) fyne.Resource {
    return theme.DefaultTheme().Icon(name)
}

func (t CustomTheme) Size(name fyne.ThemeSizeName) float32 {
    return theme.DefaultTheme().Size(name)
}

// 应用
a.Settings().SetTheme(&CustomTheme{})

// 局部主题覆写
container.NewThemeOverride(&CustomTheme{}, content)
```

## 10. 对话框模式

### 10.1 确认操作

```go
func deleteItem(id string, w fyne.Window) {
    dialog.ShowConfirm("Delete Item",
        fmt.Sprintf("Delete item #%s?", id),
        func(confirmed bool) {
            if confirmed {
                doDelete(id)
            }
        }, w)
}
```

### 10.2 进度对话框

```go
func processWithProgress(w fyne.Window) {
    prog := dialog.NewProgress("Processing", "Please wait...", w)

    go func() {
        for i := 0; i <= 100; i += 10 {
            time.Sleep(100 * time.Millisecond)
            fyne.Do(func() { prog.SetValue(float64(i) / 100.0) })
        }
        fyne.Do(func() {
            prog.Hide()
            dialog.ShowInformation("Done", "Processing complete", w)
        })
    }()

    prog.Show()
}
```

## 11. Navigation 导航模式

`container.NewNavigation` (v2.7+) 提供带返回按钮的页面导航栈，适合设置页、向导等多层级界面。

```go
func settingsPage() fyne.CanvasObject {
    general := widget.NewLabel("General Settings")
    advanced := widget.NewLabel("Advanced Settings")

    // 导航：push 新页面时自动出现返回按钮
    nav := container.NewNavigationWithTitle(general, "Settings")

    general.OnTapped = func() {
        nav.Push(advanced)  // 推入新页面，显示返回按钮
    }
    return nav
}
```

## 12. Canvas 样式模式

### 12.1 Rectangle 圆角与 aspect ratio

```go
// 胶囊形（pill）按钮背景
bg := canvas.NewRectangle(theme.Color(theme.ColorNamePrimary))
bg.CornerRadius = 20  // 设为高度一半 ≈ pill

// 仅顶部圆角
bg.TopLeftCornerRadius = 8
bg.TopRightCornerRadius = 8

// 固定宽高比
bg.Aspect = 1.6  // 宽度自动 = 高度 × 1.6
```

### 12.2 Image 填充模式

```go
// 头像：Cover 裁剪填满
avatar := canvas.NewImageFromFile("avatar.jpg")
avatar.FillMode = canvas.ImageFillCover
avatar.SetMinSize(fyne.NewSquareSize(48))

// 缩略图：Contain 适配不裁剪
thumb := canvas.NewImageFromFile("photo.jpg")
thumb.FillMode = canvas.ImageFillContain
thumb.SetMinSize(fyne.NewSize(200, 150))
```

## 13. Label 可选文本

v2.6+ 支持用户选中和复制 Label 文字：

```go
label := widget.NewLabel("Selectable text")
label.Selectable = true  // 用户可框选、Ctrl+C 复制

// 获取选中文本
selected := label.SelectedText()
```

## 14. RowWrap 布局

v2.7+ RowWrap 水平排列子元素，空间不够时自动换行，类似 CSS flex-wrap：

```go
// 配合 GridWrap container 使用（内部已用 RowWrap）
tags := container.NewGridWrap(fyne.NewSize(80, 30),
    widget.NewButton("Go", nil),
    widget.NewButton("Rust", nil),
    widget.NewButton("Python", nil),
    widget.NewButton("TypeScript", nil),
)

// 手动使用 RowWrap layout
c := container.New(layout.NewRowWrapLayout(), objs...)
// 或带自定义间距
c := container.New(layout.NewRowWrapLayoutWithCustomPadding(8, 4), objs...)
```

## 15. i18n 翻译

v2.5.0+ 内置翻译支持，使用 `fyne.io/fyne/v2/lang` 包。

### 15.1 标记可翻译字符串

```go
import "fyne.io/fyne/v2/lang"

// L — 默认值即为 key，未找到翻译时回退到此值
title := widget.NewLabel(lang.L("My App Title"))

// X (LocalizeKey) — 显式指定 key + 默认值（用于消歧义）
title := widget.NewLabel(lang.X("window.title", "My App Window Title"))
```

### 15.2 翻译文件

每语言一个 JSON 文件，放在 `translation/` 目录下。命名格式：`[前缀][语言子标签].json`。

```json
// translation/en.json
{
  "My App Title": "My App Title"
}

// translation/zh.json
{
  "My App Title": "我的应用标题"
}

// translation/fr.json
{
  "My App Title": "Titre de mon application"
}
```

### 15.3 嵌入并加载翻译

```go
import "fyne.io/fyne/v2/lang"

//go:embed translation
var translations embed.FS

func main() {
    a := app.New()
    lang.AddTranslationsFS(translations, "translation")
    // ...
}
```

### 15.4 复数形式

```go
// N (LocalizePlural) — 根据数量选择单复数
age := widget.NewLabel(lang.N("{% raw %}{{.Years}}{% endraw %} years old", years,
    map[string]any{"Years": years}))
```

翻译文件区分 "one" 和 "other"：

```json
{
  "{% raw %}{{.Years}}{% endraw %} years old": {
    "one": "1 year old",
    "other": "{% raw %}{{.Years}}{% endraw %} years old"
  }
}
```

## 16. 自定义布局

实现 `fyne.Layout` 接口即可创建自定义布局。接口只需两个方法：

```go
type Layout interface {
    Layout([]CanvasObject, Size)         // 排列子对象
    MinSize(objects []CanvasObject) Size // 计算最小尺寸
}
```

### 16.1 完整示例：对角线布局

```go
import "fyne.io/fyne/v2"

type diagonal struct{}

func (d *diagonal) MinSize(objects []fyne.CanvasObject) fyne.Size {
    w, h := float32(0), float32(0)
    for _, o := range objects {
        childSize := o.MinSize()
        w += childSize.Width
        h += childSize.Height
    }
    return fyne.NewSize(w, h)
}

func (d *diagonal) Layout(objects []fyne.CanvasObject, containerSize fyne.Size) {
    // 从左下角开始，每个子对象向右下偏移
    pos := fyne.NewPos(0, containerSize.Height-d.MinSize(objects).Height)
    for _, o := range objects {
        size := o.MinSize()
        o.Resize(size)
        o.Move(pos)
        pos = pos.Add(fyne.NewPos(size.Width, size.Height))
    }
}
```

使用方式：

```go
w.SetContent(container.New(&diagonal{},
    widget.NewLabel("topleft"),
    widget.NewLabel("Middle Label"),
    widget.NewLabel("bottomright"),
))
```

## 17. 扩展已有 Widget

通过 Go 类型嵌入扩展已有 Widget 的行为，无需从头创建。

### 17.1 为 Icon 添加点击

```go
type tappableIcon struct {
    widget.Icon
}

func newTappableIcon(res fyne.Resource) *tappableIcon {
    icon := &tappableIcon{}
    icon.ExtendBaseWidget(icon)  // 注意：不能用 widget.NewIcon，它已调用 ExtendBaseWidget
    icon.SetResource(res)
    return icon
}

func (t *tappableIcon) Tapped(_ *fyne.PointEvent) {
    log.Println("Icon tapped")
}
```

### 17.2 数值输入框（完整扩展示例）

通过覆写 `TypedRune`、`TypedShortcut`、`Keyboard` 实现仅允许输入数字的 Entry：

```go
import (
    "strconv"
    "fyne.io/fyne/v2/driver/mobile"
    "fyne.io/fyne/v2/widget"
)

type numericalEntry struct {
    widget.Entry
}

func newNumericalEntry() *numericalEntry {
    entry := &numericalEntry{}
    entry.ExtendBaseWidget(entry)
    return entry
}

// 过滤键盘输入 — 只允许数字和小数点
func (e *numericalEntry) TypedRune(r rune) {
    if (r >= '0' && r <= '9') || r == '.' || r == ',' {
        e.Entry.TypedRune(r)
    }
}

// 过滤粘贴 — 只有剪贴板内容可解析为数字时才放行
func (e *numericalEntry) TypedShortcut(shortcut fyne.Shortcut) {
    paste, ok := shortcut.(*fyne.ShortcutPaste)
    if !ok {
        e.Entry.TypedShortcut(shortcut)
        return
    }
    content := paste.Clipboard.Content()
    if _, err := strconv.ParseFloat(content, 64); err == nil {
        e.Entry.TypedShortcut(shortcut)
    }
}

// 移动端弹出数字键盘
func (e *numericalEntry) Keyboard() mobile.KeyboardType {
    return mobile.NumberKeyboard
}
```

**扩展 Widget 要点：**
- 构造函数调用 `ExtendBaseWidget(self)`，而非原 Widget 构造函数
- 覆写 `TypedRune` 过滤键盘输入、`TypedShortcut` 过滤快捷键/粘贴
- 不处理的输入调用原 Widget 的同名方法委托

## 18. Preferences 进阶

`Preferences` API 用于持久化用户设置，支持 `Bool`、`Float`、`Int`、`String` 及其列表类型。

### 18.1 基本用法

```go
// 必须使用唯一 ID 创建应用，确保独立的存储空间
a := app.NewWithID("com.example.tutorial.preferences")

// 每种类型有三个方法：Get、GetWithFallback、Set
a.Preferences().SetBool("darkMode", true)
a.Preferences().SetFloatList("recentScores", []float64{95.5, 88.0})

value := a.Preferences().IntWithFallback("luckyNumber", 21)
name := a.Preferences().String("username")  // 不存在返回 ""
```

### 18.2 完整示例：记住用户选择

```go
a := app.NewWithID("com.example.app")
w := a.NewWindow("Settings")

var timeout time.Duration

selector := widget.NewSelect([]string{"10 seconds", "30 seconds", "1 minute"},
    func(selected string) {
        switch selected {
        case "10 seconds":
            timeout = 10 * time.Second
        case "30 seconds":
            timeout = 30 * time.Second
        case "1 minute":
            timeout = time.Minute
        }
        a.Preferences().SetString("AppTimeout", selected)
    })

// 加载上次选择，无则回退
selector.SetSelected(a.Preferences().StringWithFallback("AppTimeout", "10 seconds"))
```

### 18.3 Preference 数据绑定

```go
prefs := a.Preferences()
themeBinding := binding.BindPreferenceString("theme", prefs)
// 选择后自动同步到 Preferences
widget.NewSelectWithData([]string{"light", "dark"}, themeBinding, func(s string) {})
```

## 19. 系统托盘生命周期

完整的系统托盘应用需要处理窗口生命周期，而非简单关闭。

### 19.1 关闭拦截 + 隐藏/显示

```go
func main() {
    a := app.New()
    w := a.NewWindow("SysTray")

    // 拦截关闭 → 隐藏而非销毁
    w.SetCloseIntercept(func() {
        w.Hide()
    })

    // 仅在桌面端设置托盘
    if desk, ok := a.(desktop.App); ok {
        m := fyne.NewMenu("MyApp",
            fyne.NewMenuItem("Show", func() {
                w.Show()  // 重新显示隐藏的窗口
            }))
        desk.SetSystemTrayMenu(m)
        desk.SetSystemTrayIcon(theme.FyneLogo())  // 可选：自定义图标
    }

    w.SetContent(widget.NewLabel("Fyne System Tray"))
    w.ShowAndRun()
}
```

**要点：**
- `SetCloseIntercept` 覆盖默认关闭行为（隐藏而非退出）
- 不需要重建窗口，`Show()` 比创建新窗口更高效
- 通过 `a.(desktop.App)` 类型断言判断是否支持桌面特性
- `app.NewWithID` 配合 `FyneApp.toml` 的 `[Details].Icon` 可设置托盘图标

## 20. 多窗口进阶

### 20.1 启动时打开多个窗口

```go
func main() {
    a := app.New()
    mainWin := a.NewWindow("Main")
    mainWin.SetContent(widget.NewLabel("Main Window"))
    mainWin.Show()

    settingsWin := a.NewWindow("Settings")
    settingsWin.SetContent(widget.NewLabel("Settings"))
    settingsWin.Resize(fyne.NewSize(300, 200))
    settingsWin.Show()

    a.Run()  // 所有窗口关闭后退出
}
```

### 20.2 设置主窗口

默认所有窗口关闭才退出，`SetMaster()` 指定关闭即退出的主窗口：

```go
mainWin.SetMaster()  // 关闭主窗口 → 应用退出
```

### 20.3 运行时打开新窗口

```go
openNew := widget.NewButton("Open Window", func() {
    w3 := a.NewWindow("Third")
    w3.SetContent(widget.NewLabel("Third Window"))
    w3.Show()
})
```

### 20.4 关闭拦截 + 未保存确认

```go
settingsWin.SetCloseIntercept(func() {
    if hasUnsavedChanges {
        dialog.ShowConfirm("Unsaved Changes",
            "Save before closing?",
            func(ok bool) {
                if ok { save(); settingsWin.Close() }
                // 不保存则不做任何事，窗口保持打开
            }, settingsWin)
    } else {
        settingsWin.Close()
    }
})
```

## 21. 动画

v2.0+ Fyne 内置动画框架，支持颜色、位置、尺寸的平滑过渡。

### 21.1 颜色动画

```go
obj := canvas.NewRectangle(color.Black)
red := color.NRGBA{R: 0xff, A: 0xff}
blue := color.NRGBA{B: 0xff, A: 0xff}

canvas.NewColorRGBAAnimation(red, blue, time.Second*2, func(c color.Color) {
    obj.FillColor = c
    canvas.Refresh(obj)  // 每帧触发重绘
}).Start()
```

### 21.2 位置动画 + 自动往复

```go
// 对象的方法签名匹配动画回调时，可直接传递方法名
move := canvas.NewPositionAnimation(
    fyne.NewPos(0, 0), fyne.NewPos(200, 0),
    time.Second,
    obj.Move,  // Move(Position) 签名匹配
)
move.AutoReverse = true  // 到达终点后自动反向
move.Start()
```

### 21.3 尺寸动画

```go
sizeAnim := canvas.NewSizeAnimation(
    fyne.NewSize(50, 50), fyne.NewSize(200, 100),
    time.Second,
    func(s fyne.Size) { obj.Resize(s); canvas.Refresh(obj) },
)
sizeAnim.Start()
```

### 21.4 组合多个动画

多个动画可以同时运行，互不干扰：

```go
// 同时执行颜色过渡和位置移动
canvas.NewColorRGBAAnimation(red, blue, time.Second*2, func(c color.Color) {
    obj.FillColor = c
    obj.Refresh()
}).Start()

canvas.NewPositionAnimation(
    fyne.NewPos(0, 0), fyne.NewPos(200, 0), time.Second, obj.Move,
).Start()
```

### 21.5 关键要点

- 动画需在 `ShowAndRun()` 之前启动（或通过 `fyne.Do` 调度）
- 使用 `container.NewWithoutLayout()` 放置需要手动动画的对象
- 内置曲线默认 `AnimationEaseInOut`，也可用 `AnimationLinear`/`AnimationEaseIn`/`AnimationEaseOut`（见 `references/api-reference.md` 动画部分）

## 22. 缩放与设备适配

### 22.1 坐标系统

Fyne 使用设备无关坐标，基线为 120DPI（对比 Material Design 的 160DPI）。这意味着：
- 120DPI 显示器上 1 单位 ≈ 1 像素
- HiDPI（如 Retina，~240DPI）上 1 单位 ≈ 2 像素
- 手机上可能更高

所有 `Size` 和 `Position` 值都使用设备无关坐标，框架自动处理缩放。

### 22.2 调整缩放比例

```bash
# 环境变量
FYNE_SCALE=1.5 ./myapp    # 放大 50%
FYNE_SCALE=0.8 ./myapp    # 缩小 20%

# 查询当前缩放
scale := app.Settings().Scale()
```

### 22.3 像素图像的适配

```go
// 默认情况下图片 MinSize 为 0，会被布局压缩
// 通过 SetMinSize 设置设备无关的最小尺寸
img := canvas.NewImageFromFile("photo.jpg")
img.SetMinSize(fyne.NewSize(200, 150))  // 在所有屏幕上显示一致大小

// 也可以配合 FillMode 控制缩放行为
img.FillMode = canvas.ImageFillCover   // 裁剪填满
img.FillMode = canvas.ImageFillContain // 等比适配
```

### 22.4 移动端检测

```go
if fyne.CurrentDevice().IsMobile() {
    // 竖屏：VBox 堆叠
    w.SetContent(container.NewVBox(items...))
} else {
    // 宽屏：HSplit 左右分栏
    w.SetContent(container.NewHSplit(sidebar, content))
}
```

`fyne.CurrentDevice().Orientation()` 返回 `fyne.OrientationVertical` 或 `fyne.OrientationHorizontal` 判断方向。
