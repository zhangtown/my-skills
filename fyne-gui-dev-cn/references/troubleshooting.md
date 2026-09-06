# 排障思路与调试技巧

## 目录

- [快速诊断表](#快速诊断表)
- [1. Widget 不可见](#1-widget-不可见)
- [2. 创建 Renderer 失败](#2-创建-renderer-失败)
- [3. panic: fyne.Canvas is nil](#3-panic-fynecancas-is-nil)
- [4. panic: fyne.Layout is nil](#4-panic-fynelayout-is-nil)
- [5. 数据绑定不更新](#5-数据绑定不更新)
- [6. 布局问题](#6-布局问题)
- [7. 线程相关问题](#7-线程相关问题)
- [8. 构建和打包问题](#8-构建和打包问题)
- [9. 调试工具](#9-调试工具)
- [10. 常见误用模式](#10-常见误用模式)
- [11. 编译与安装问题](#11-编译与安装问题)
- [12. 获取帮助](#12-获取帮助)

---

## 快速诊断表

| 症状 | 首先检查 |
|------|---------|
| Widget 不显示 | `Objects()` 是否非空？`ExtendBaseWidget` 是否调用？ |
| 点击不触发 | Widget 尺寸是否 >0？是否实现 `Tappable` 接口？ |
| 布局错乱 | `MinSize()` 是否合理？`Layout()` 是否正确计算位置？ |
| panic | nil Layout？nil Canvas？`fyne.Do` 在主 goroutine 调用？ |
| 数据绑定不更新 | 外部绑定是否调用了 `Reload()`？ |
| 打包后加载失败 | 是否使用了文件路径而非嵌入资源？ |
| 帧率暴跌/UI 卡死 | 是否在循环中反复 Refresh？是否在 Layout 中调 Refresh？ |
| 无限递归/StackOverflow | 是否在 UpdateCell 中调用了 SetRowHeight？ |
| 内存泄漏 | 是否反复 SetContent 而未清理旧 Widget？ |
| 主题色不生效 | 是否使用了自定义 Theme 但未覆盖全部 Color/Size？ |
| v2.6+ `fyne.Do called from main goroutine` | 事件回调中调了 `fyne.Do` |

## 1. Widget 不可见

**最常出现的问题。**按以下顺序排查：

```
□ CreateRenderer() 返回了 nil？
□ Objects() 返回了空切片或包含 nil？
□ 构造器中是否调用了 ExtendBaseWidget(w)？
□ 是否用了值接收者而非指针（如 canvas.Line vs *canvas.Line）？
□ 无 Layout 容器中是否手动 Resize() 了？
```

### 调试方法

```go
// 检查 Renderer
r := test.WidgetRenderer(myWidget)
if r == nil {
    fmt.Println("Renderer is nil — CreateRenderer returned nil")
}

// 检查 Objects
objs := r.Objects()
fmt.Printf("Objects count: %d\n", len(objs))
for i, obj := range objs {
    fmt.Printf("  [%d] %T, visible=%v\n", i, obj, obj.Visible())
}

// 检查 MinSize
fmt.Printf("MinSize: %v, Size: %v\n", myWidget.MinSize(), myWidget.Size())
```

## 2. 创建 Renderer 失败

```
panic: runtime error: invalid memory address or nil pointer dereference
```

检查点：
- `CreateRenderer()` 是否返回了 nil？
- `cache.Renderer(impl)` 是否在 `impl` 为 nil 时被调用？（检查 `ExtendBaseWidget` 是否调用）
- Widget 是否在构造时立即调用了需要 Renderer 的方法？

## 3. panic: fyne.Canvas is nil

在 Widget 尚未加入 Window/Canvas 时调用了需要 Canvas 的操作。

```go
// ❌ 错误
selectWidget := widget.NewSelect(options, callback)
selectWidget.Tapped(ev)  // 内部需要 Canvas，此时为 nil

// ✅ 正确：先放入 Canvas
window.SetContent(selectWidget)
// 现在 Canvas 可用
```

## 4. panic: fyne.Layout is nil

Widget Renderer 尚未初始化，内部 Layout 为 nil。

```go
// ❌ 错误
list := widget.NewList(lenFn, createFn, updateFn)
list.Resize(fyne.NewSize(100, 100))  // Renderer 未创建

// ✅ 正确：放入容器后 Resize 容器
c := container.NewVBox(list)
window.SetContent(c)
c.Resize(fyne.NewSize(400, 300))
```

## 5. 数据绑定不更新

### 检查清单

```go
// 1. 外部绑定是否正确使用 Reload？
var count int
b := binding.BindInt(&count)
count = 10       // ❌ 直接修改不通知
b.Reload()       // ✅ 需要显式调用

// 2. 是否正确使用了 WithData 构造？
label := widget.NewLabelWithData(data)  // ✅ 自动绑定

// 3. 监听器是否注册？
data.AddListener(binding.NewDataListener(func() {
    fmt.Println("Changed!")  // 确认是否被调用
}))

// 4. 列表绑定是否正确更新？
list := binding.NewStringList()
list.Set(append(existing, "new"))  // ✅ 触发通知
```

## 6. 布局问题

### 6.1 子元素重叠或被截断

- 父容器尺寸是否足够？ `parent.Resize(largerSize)`
- `MinSize` 返回值是否过小？

### 6.2 Grid 中出现空白

隐藏的对象仍占据格子位置。解决：
```go
// ❌ 隐藏但占位
obj.Hide()

// ✅ 从容器中移除
container.Remove(obj)
```

### 6.3 Form 布局对齐问题

`layout.FormLayout` 要求每行是成对的对象（标签 + 输入）：
```go
formLayout := layout.NewFormLayout()
// 对象必须按 [label1, input1, label2, input2, ...] 排列
```

## 7. 线程相关问题

### 7.1 竞态

```go
// ❌ 错误
go func() {
    label.SetText("updated")  // 竞态风险
}()

// ✅ 正确
go func() {
    fyne.Do(func() {
        label.SetText("updated")
    })
}()
```

### 7.2 死锁

常见死锁场景：
- `FocusGained/FocusLost` 中操作 OverlayStack 或修改焦点
- `Layout` 中调用 `Refresh`
- `fyne.DoAndWait` 回调中再次调用 `fyne.DoAndWait`

## 8. 构建和打包问题

### 8.1 打包后资源 404

```go
// ❌ 打包后文件系统路径不可用
img := canvas.NewImageFromFile("/Users/me/project/icon.png")

// ✅ 嵌入资源
//go:generate fyne bundle -o bundled.go icon.png
img := canvas.NewImageFromResource(resourceIconPng)
```

### 8.2 交叉编译

```bash
# fyne-cross 作为工具使用
# 官方 docker 镜像支持 Windows/macOS/Linux 交叉编译
```

## 9. 调试工具

### 9.1 Debug 渲染

```bash
# 显示布局边界框和交互区域
go run -tags debug main.go
```

### 9.2 RenderToMarkup 调试

```go
import "fyne.io/fyne/v2/test"

// 获取 Widget 的文本化结构
markup := test.RenderObjectToMarkup(widget)
fmt.Println(markup)
```

### 9.3 遍历渲染树

```go
func printTree(obj fyne.CanvasObject, indent string) {
    fmt.Printf("%s%T pos=%v size=%v visible=%v\n",
        indent, obj, obj.Position(), obj.Size(), obj.Visible())

    if w, ok := obj.(fyne.Widget); ok {
        r := test.WidgetRenderer(w)
        for _, child := range r.Objects() {
            printTree(child, indent+"  ")
        }
    }
    if c, ok := obj.(*fyne.Container); ok {
        for _, child := range c.Objects {
            printTree(child, indent+"  ")
        }
    }
}
```

### 9.4 检查主题

```go
app := fyne.CurrentApp()
th := app.Settings().Theme()
fmt.Printf("Variant: %v, Scale: %.2f\n",
    app.Settings().ThemeVariant(), app.Settings().Scale())

// 重置为默认主题
app.Settings().SetTheme(theme.DefaultTheme())
```

## 10. 常见误用模式

### 10.1 Refresh 滥用 — 在 Layout 或 Resize 回调中调用 Refresh

**最隐蔽的性能问题**。`Resize()` 和 `Layout()` 被频繁调用，在其中调用 `Refresh()` 会造成指数级重绘。

```go
// ❌ 错误 — Layout 中调用 Refresh
func (r *myRenderer) Layout(size fyne.Size) {
    r.bg.Resize(size)
    r.w.Refresh()  // 触发新一轮 Layout → 死循环或性能崩溃
}

// ❌ 错误 — MinSize 中触发重绘
func (r *myRenderer) MinSize() fyne.Size {
    r.w.Refresh()  // MinSize 被频繁查询，每次查询都重绘
    return fyne.NewSize(100, 30)
}

// ✅ 正确 — Layout 只调整几何，不触发 Refresh
func (r *myRenderer) Layout(size fyne.Size) {
    r.bg.Resize(size)
}
```

### 10.2 Refresh vs Resize 混淆 — 频繁 Refresh 导致帧率崩溃

`Resize()` 只改变几何尺寸（便宜），`Refresh()` 做完全重绘（昂贵）。

```go
// ❌ 频繁 Refresh — 帧率从 60fps 崩到 10fps
for i := 0; i < 1000; i++ {
    progress.SetValue(float64(i) / 1000)
    progress.Refresh()  // 每秒 1000 次重绘！
}

// ✅ 批量更新 — 只在最后 Refresh 一次
for i := 0; i < 1000; i++ {
    progress.SetValue(float64(i) / 1000)
}
progress.Refresh()  // 一次到位
```

**更好的方案**：对于持续变化的场景，直接用数据绑定，框架会自动优化刷新：

```go
data := binding.NewFloat()
widget.NewProgressBarWithData(data)

go func() {
    for i := 0; i <= 100; i += 10 {
        time.Sleep(100 * time.Millisecond)
        data.Set(float64(i) / 100)  // 框架自动优化刷新频率
    }
}()
```

### 10.3 循环中逐个添加/删除容器子对象

```go
// ❌ 错误 — 每次 Add/Remove 都触发 layout
for _, item := range items {
    container.Add(widget.NewLabel(item))
}

// ✅ 正确 — 批量替换
widgets := make([]fyne.CanvasObject, len(items))
for i, item := range items {
    widgets[i] = widget.NewLabel(item)
}
container.Objects = widgets
container.Refresh()
```

### 10.4 在 UpdateCell/UpdateRow 回调中修改布局状态

`widget.List` 和 `widget.Table` 的更新回调在渲染循环内被调用，在其内部调用 `SetRowHeight` 或 `Resize` 会导致无限递归（stack overflow）。

```go
// ❌ 错误 — UpdateCell 中调用 SetRowHeight
table := widget.NewTable(
    func() (int, int) { return 10, 3 },
    func() fyne.CanvasObject { return widget.NewLabel("") },
    func(id widget.TableCellID, obj fyne.CanvasObject) {
        table.SetRowHeight(id.Row, 50)  // → 触发 re-layout → 再次进入 UpdateCell → 无限递归
    })

// ✅ 正确 — 在 UpdateCell 外部预设行高
table.SetRowHeight(0, 50)
```

### 10.5 主 goroutine 中也调用 fyne.Do（v2.6.0+）

v2.6.0 引入了严格的线程检查，在主 goroutine 中调用 `fyne.Do` 会报错：

```
*** Error in Fyne call thread, fyne.Do[AndWait] called from main goroutine ***
```

```go
// ❌ Fyne 回调已保证在主 goroutine，不需要 fyne.Do
btn.OnTapped = func() {
    fyne.Do(func() {
        label.SetText("clicked")  // v2.6.0+ 报错！
    })
}

// ✅ Fyne 回调直接操作即可
btn.OnTapped = func() {
    label.SetText("clicked")
}
```

**规则**：`fyne.Do` 仅用于手动创建的 `go func()` 后台 goroutine 中。Fyne 事件回调（`OnTapped`、`OnChanged`、`CreateRenderer`、Layout 等）已经保证在主 goroutine。

### 10.6 后台 goroutine 未通过 fyne.Do 直接操作 UI

```go
// ❌ 竞态风险（v2.6.0+ 直接报错）
go func() {
    time.Sleep(10 * time.Millisecond)
    canvas.Refresh(myWidget)  // 不在主 goroutine
}()

// ✅ 正确
go func() {
    time.Sleep(10 * time.Millisecond)
    fyne.Do(func() {
        canvas.Refresh(myWidget)
    })
}()
```

### 10.7 Image 大图同步解码阻塞 UI

`canvas.NewImageFromFile()` 同步解码图片。大文件（>2MB）会阻塞主线程 30ms+。

```go
// ❌ 阻塞主 goroutine
img := canvas.NewImageFromFile("large-photo.jpg")

// ✅ 后台解码，解码后回到主 goroutine
go func() {
    file, _ := os.Open("large-photo.jpg")
    decoded, _, _ := image.Decode(file)
    file.Close()
    fyne.Do(func() {
        img := canvas.NewImageFromImage(decoded)
        container.Add(img)
    })
}()
```

### 10.8 用 Hide() 代替 Remove() 导致空白

隐藏的对象不显示但**仍占据布局空间**，Grid/FixedGridLayout 中尤其明显。

```go
// ❌ 隐藏但空占格子
obj.Hide()

// ✅ 从容器中彻底移除
container.Remove(obj)
```

### 10.9 CanvasForObject 返回值未做 nil 检查

Widget 尚未加入 Canvas 时，`CanvasForObject()` 返回 nil。

```go
// ❌ 可能 nil panic
c := fyne.CurrentApp().Driver().CanvasForObject(myWidget)
c.Refresh(myWidget)

// ✅ 先检查，或直接用 w.Refresh()（内部已处理）
if c != nil {
    c.Refresh(myWidget)
}
// 更简单：
myWidget.Refresh()  // BaseWidget.Refresh 内部已做 nil 检查
```

### 10.10 非可见 Widget 的 MinSize 可能为 0

非可见 Widget 没有渲染器，`MinSize()` 可能返回 {0, 0}。测试时需先放入 Canvas。

```go
// ❌ 测试中直接测 MinSize 可能不准确
w := NewMyWidget()
min := w.MinSize()  // 可能为 {0, 0}

// ✅ 先放入测试 Canvas
c := test.NewCanvas()
c.SetContent(w)
c.Resize(fyne.NewSize(400, 300))
min = w.MinSize()  // 现在正确
```

### 10.11 SetContent 后旧内容未清理导致内存泄漏

反复 `SetContent()` 时，旧 Widget 树仍保留在内存中。若旧树持有数据绑定监听器或事件回调，会阻止 GC 回收。

```go
// ❌ 内存泄漏
w.SetContent(page1)
w.SetContent(page2)  // page1 及其所有子 Widget 泄漏

// ✅ 方案 1：用 Stack 容器切换，Hide 旧页面
pages := container.NewStack(page1, page2)
w.SetContent(pages)
page1.Hide()
page2.Show()
// page1 仍在内存但不泄漏，可再次 Show

// ✅ 方案 2：清理监听器后切换
func switchPage(w fyne.Window, newPage fyne.CanvasObject) {
    old := w.Content()
    if cleanable, ok := old.(interface{ Cleanup() }); ok {
        cleanable.Cleanup()
    }
    w.SetContent(newPage)
}
```

### 10.12 忽略 Dialog 的 parent 参数

Dialog 需要 parent Window 来确定位置和生命周期。传 nil 会导致对话框显示位置异常或事件传递问题。

```go
// ❌ parent 为 nil
dialog.ShowInformation("Title", "Msg", nil)

// ✅ 始终传入有效的 Window
dialog.ShowInformation("Title", "Msg", myWindow)
```

## 11. 编译与安装问题

### 11.1 `command not found: fyne`

`go install fyne.io/tools/cmd/fyne@latest` 后出现此错误，通常是 GOPATH/bin 不在 PATH 中：

```bash
# 检查 GOPATH/bin 是否在 PATH 中
echo $PATH | grep "$(go env GOPATH)/bin"

# 如缺失，添加到 ~/.zshrc 或 ~/.bashrc
export PATH="$(go env GOPATH)/bin:$PATH"
```

### 11.2 交叉编译时 `build constraints exclude all Go files`

跨平台编译时 Go 默认关闭 CGo。设置 `CGO_ENABLED=1` 解决：

```bash
CGO_ENABLED=1 GOOS=windows GOARCH=amd64 go build
```

详见 `references/deployment.md` 交叉编译章节。

### 11.3 Windows 编译 `64-bit mode not compiled in`

Windows 编译提示 64 位模式不可用，通常是安装了错误的编译器。使用 MSYS2 时，确保使用 "MSYS2 MinGW 64-bit" 启动菜单项打开终端。

### 11.4 macOS 提示应用已损坏

下载的 `.app` 被 macOS 隔离标记拦截（尤其 M1/M2 机型无法通过"系统设置"放行）。运行以下命令移除隔离标记：

```bash
sudo xattr -r -d com.apple.quarantine MyApp.app
```

如果应用已签名（Apple Developer 证书），此问题不会出现。

### 11.5 图片在应用中显示过小

Fyne 使用设备无关坐标系（基线 120DPI），像素图片的物理大小取决于屏幕密度。默认加载的图片 `MinSize` 为 0，会被布局压缩。解决方案：

```go
img := canvas.NewImageFromFile("photo.jpg")
img.SetMinSize(fyne.NewSize(200, 150))  // 设置设备无关的最小尺寸
img.FillMode = canvas.ImageFillContain  // 控制填充模式
```

### 11.6 如何手动控制元素位置

如果需要完全控制元素的位置和大小，使用 `container.NewWithoutLayout()`：

```go
obj1 := canvas.NewRectangle(color.NRGBA{R: 255, A: 255})
obj1.Resize(fyne.NewSize(100, 50))
obj1.Move(fyne.NewPos(10, 10))

obj2 := widget.NewButton("Click", nil)
obj2.Resize(fyne.NewSize(120, 40))
obj2.Move(fyne.NewPos(20, 80))

c := container.NewWithoutLayout(obj1, obj2)
w.SetContent(c)
```

**注意**：手动定位的容器不会随窗口大小自适应，也不提供最小尺寸。正式应用中推荐使用自定义 Layout（见 `references/best-practices.md` 自定义布局章节）。

### 11.7 FYNE_SCALE 环境变量

设置应用缩放比例，覆盖系统默认值：

```bash
FYNE_SCALE=1.5 ./myapp    # 放大 50%
FYNE_SCALE=0.8 ./myapp    # 缩小 20%
```

Fyne 自动根据系统 DPI 缩放。移动窗口到不同显示器时会自动调整。默认缩放值可通过 `app.Settings().Scale()` 查询。

## 12. 获取帮助

- 官方文档：https://docs.fyne.io
- API 文档：https://pkg.go.dev/fyne.io/fyne/v2
- 论坛：https://github.com/fyne-io/fyne/discussions
- Issue Tracker：https://github.com/fyne-io/fyne/issues

### 查找 Fyne 源码路径

```bash
# 方法1：go doc（无需知道路径，直接查 API）
go doc fyne.io/fyne/v2/widget
go doc fyne.io/fyne/v2/widget.Label

# 方法2：找到 Fyne 模块路径
FYNE_DIR=$(go list -m -json fyne.io/fyne/v2 | grep '"Dir"' | cut -d'"' -f4)
echo "$FYNE_DIR/widget/"

# 方法3：GOMODCACHE 回退
ls "$(go env GOMODCACHE)/fyne.io/fyne/v2@v2.5.0"

# 方法4：搜索特定符号
rg "func.*CreateRenderer" "$(go env GOMODCACHE)/fyne.io/fyne/v2@*/widget/"
```

### Fyne 核心包结构（按 import path）

| import | 说明 |
|--------|------|
| `fyne.io/fyne/v2` | 核心接口：App, Window, Canvas, CanvasObject, Widget, Layout |
| `fyne.io/fyne/v2/app` | App 实现 |
| `fyne.io/fyne/v2/widget` | 内置 Widget（Button, Label, Entry, List, ...） |
| `fyne.io/fyne/v2/container` | 容器构造函数（NewVBox, NewBorder, ...） |
| `fyne.io/fyne/v2/layout` | 布局算法（HBoxLayout, VBoxLayout, GridLayout, ...） |
| `fyne.io/fyne/v2/canvas` | 原始图形对象（Rectangle, Text, Image, Line, ...） |
| `fyne.io/fyne/v2/dialog` | 对话框 |
| `fyne.io/fyne/v2/data/binding` | 数据绑定 |
| `fyne.io/fyne/v2/test` | 测试工具包 |
| `fyne.io/fyne/v2/theme` | 主题：颜色、字体、图标、尺寸 |
| `fyne.io/fyne/v2/driver/desktop` | 桌面特有功能（Hoverable, CustomShortcut） |
| `fyne.io/fyne/v2/storage` | 存储抽象 |
| `fyne.io/fyne/v2/internal/cache` | 内部缓存（Renderer 缓存、主题缓存） |
