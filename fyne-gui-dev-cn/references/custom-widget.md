# 自定义 Widget 深入指南

## 目录

- [Widget/Renderer 分离模式](#widgetrenderer-分离模式)
- [完整实现模板](#完整实现模板)
- [关键规则详解](#关键规则详解)
- [扩展已有 Widget](#扩展已有-widget)
- [支持数据绑定](#支持数据绑定)
- [调试自定义 Widget](#调试自定义-widget)
- [常见错误](#常见错误)
- [内容内边距规范](#内容内边距规范)

---

## Widget/Renderer 分离模式

Fyne 中 Widget 采用声明-渲染分离模式：
- **Widget**：持有状态（文字、选中状态、数据绑定等），是声明式对象
- **WidgetRenderer**：每个 Widget 实例有一个渲染器，负责实际的 CanvasObject 绘制

`CreateRenderer()` 由框架在需要渲染时调用一次，结果被缓存。多次调用 `Refresh()` 不会重新创建 Renderer。

## 完整实现模板

```go
package mywidget

import (
    "image/color"

    "fyne.io/fyne/v2"
    "fyne.io/fyne/v2/canvas"
    "fyne.io/fyne/v2/theme"
    "fyne.io/fyne/v2/widget"
)

// 1. 声明式 Widget
type MyWidget struct {
    widget.BaseWidget

    Text  string
    Icon  fyne.Resource
    Color color.Color

    OnTapped func()
}

// 2. 构造器
func NewMyWidget(text string, tapped func()) *MyWidget {
    w := &MyWidget{
        Text:     text,
        OnTapped: tapped,
        Color:    theme.Color(theme.ColorNamePrimary),
    }
    w.ExtendBaseWidget(w) // 🔴 必须调用
    return w
}

// 3. CreateRenderer
func (w *MyWidget) CreateRenderer() fyne.WidgetRenderer {
    bg := canvas.NewRectangle(w.Color)
    icon := canvas.NewImageFromResource(w.Icon)
    label := canvas.NewText(w.Text, theme.Color(theme.ColorNameForeground))

    r := &myRenderer{
        bg:    bg,
        icon:  icon,
        label: label,
        w:     w,
    }
    r.objects = []fyne.CanvasObject{bg, icon, label}
    return r
}

// 4. 可选：实现功能接口
func (w *MyWidget) Tapped(ev *fyne.PointEvent) {
    if w.OnTapped != nil {
        w.OnTapped()
    }
}

// 5. Setter
func (w *MyWidget) SetText(text string) {
    w.Text = text
    w.Refresh()
}

func (w *MyWidget) SetColor(c color.Color) {
    w.Color = c
    w.Refresh()
}
```

```go
// 6. Renderer
type myRenderer struct {
    bg       *canvas.Rectangle
    icon     *canvas.Image
    label    *canvas.Text
    w        *MyWidget
    objects  []fyne.CanvasObject
}

func (r *myRenderer) Destroy() {
    // 清理资源（如动画、回调等）
}

func (r *myRenderer) Layout(size fyne.Size) {
    // 🔴 禁止在此方法中调用 r.w.Refresh()
    pad := theme.Padding()

    r.bg.Resize(size)

    // icon 左上角
    iconSize := fyne.NewSquareSize(size.Height - pad*2)
    r.icon.Resize(iconSize)
    r.icon.Move(fyne.NewPos(pad, pad))

    // label 在 icon 右边
    labelX := pad*2 + iconSize.Width
    r.label.Move(fyne.NewPos(labelX, pad))
    r.label.Resize(fyne.NewSize(size.Width-labelX-pad, size.Height-pad*2))
}

func (r *myRenderer) MinSize() fyne.Size {
    // 🔴 基于子对象计算，不要硬编码
    iconMin := r.icon.MinSize()
    labelMin := r.label.MinSize()
    pad := theme.Padding()

    w := iconMin.Width + labelMin.Width + pad*3
    h := fyne.Max(iconMin.Height, labelMin.Height) + pad*2
    return fyne.NewSize(w, h)
}

func (r *myRenderer) Objects() []fyne.CanvasObject {
    // 🔴 必须返回非空、无 nil 元素的切片
    return r.objects
}

func (r *myRenderer) Refresh() {
    // 🔴 将 Widget 的状态同步到绘制对象
    r.bg.FillColor = r.w.Color
    r.label.Text = r.w.Text
    r.icon.Resource = r.w.Icon

    // 刷新绘制对象
    r.bg.Refresh()
    r.label.Refresh()
    r.icon.Refresh()
}
```

## 关键规则详解

### 规则 1：必须调用 ExtendBaseWidget

```go
func NewMyWidget() *MyWidget {
    w := &MyWidget{}
    w.ExtendBaseWidget(w)  // 设置内部 impl 指针
    return w
}
```

不调用会导致：
- `Refresh()` 无效（无法找到 Renderer）
- 数据绑定监听器不触发
- `Theme()` 返回 nil
- 事件处理异常

### 规则 2：Objects() 不能返回空/nil

```go
// ❌ 错误
func (r *myRenderer) Objects() []fyne.CanvasObject {
    return []fyne.CanvasObject{}  // Widget 不可见
}

// ❌ 错误
func (r *myRenderer) Objects() []fyne.CanvasObject {
    return []fyne.CanvasObject{nil}  // 导致 panic
}

// ✅ 正确
func (r *myRenderer) Objects() []fyne.CanvasObject {
    return r.objects  // 至少 1 个有效对象
}
```

### 规则 3：使用指针接收者

```go
// ❌ canvas.Line 的值类型不满足 CanvasObject 接口
line := canvas.Line{}

// ✅ 必须用指针
line := &canvas.Line{}
```

同样适用于 `canvas.Text`, `canvas.Circle`, `canvas.Rectangle` 等。

### 规则 4：不在 Layout 中调用 Refresh

```go
// ❌ 错误 — 可能导致无限递归
func (r *myRenderer) Layout(size fyne.Size) {
    r.bg.Resize(size)
    r.w.Refresh()  // Refresh 可能触发 Layout
}

// ✅ 正确
func (r *myRenderer) Layout(size fyne.Size) {
    r.bg.Resize(size)
    // 只调整尺寸，不触发 Refresh
}
```

### 规则 5：MinSize 基于子对象

```go
// ❌ 硬编码
func (r *myRenderer) MinSize() fyne.Size {
    return fyne.NewSize(100, 30)  // 破坏自适应布局
}

// ✅ 基于子对象 minSize + padding
func (r *myRenderer) MinSize() fyne.Size {
    labelMin := r.label.MinSize()
    pad := theme.Padding()
    return fyne.NewSize(labelMin.Width+pad*2, labelMin.Height+pad*2)
}
```

## 扩展已有 Widget

### 扩展 Label

```go
type MyLabel struct {
    widget.Label
    Priority int  // 自定义字段
}

func NewMyLabel(text string, priority int) *MyLabel {
    l := &MyLabel{Priority: priority}
    l.ExtendBaseWidget(l)
    l.SetText(text)
    return l
}
```

在自定义 Layout 中访问扩展字段：
```go
func (l *myLayout) Layout(objects []fyne.CanvasObject, size fyne.Size) {
    for _, o := range objects {
        if myLabel, ok := o.(*MyLabel); ok {
            // 访问 myLabel.Priority
        }
    }
}
```

## 支持数据绑定

```go
type BoundWidget struct {
    widget.BaseWidget

    data     binding.String
    listener binding.DataListener
}

func NewBoundWidget(data binding.String) *BoundWidget {
    w := &BoundWidget{data: data}
    w.ExtendBaseWidget(w)

    w.listener = binding.NewDataListener(func() {
        w.Refresh()  // 数据变更 → 重绘
    })
    data.AddListener(w.listener)
    return w
}
```

## 调试自定义 Widget

1. 检查 Objects() 是否非空：`test.WidgetRenderer(w).Objects()`
2. 验证 MinSize 是否 >0
3. 用 `test.NewCanvas()` 创建测试环境
4. 用 `test.Tap(w)` 验证交互
5. 用 `test.RenderObjectToMarkup(w)` 查看渲染快照

## 常见错误

| 错误 | 后果 | 修复 |
|------|------|------|
| 忘记 `ExtendBaseWidget` | Widget 完全不工作 | 在构造器末尾调用 |
| `Objects()` 返回空 | Widget 不可见 | 至少返回 1 个对象 |
| `Objects()` 元素含 nil | panic | 确保所有元素非 nil |
| `canvas.Line` 值类型 | 编译错误 | 用 `*canvas.Line` |
| `MinSize` 硬编码 | 自适应布局被破坏 | 基于子对象计算 |
| `Layout` 中 `Refresh` | 无限递归 | 移除 Refresh 调用 |
| 多个 Widget 共享 Renderer | 状态混乱 | 每个 Widget 独立 Renderer |

## 内容内边距规范

为了让自定义 Widget 与内置组件视觉对齐，遵循 Fyne 的内边距标准：

```go
func (r *myRenderer) MinSize() fyne.Size {
    th := r.w.Theme()
    pad := th.Size(theme.SizeNamePadding)       // 标准间距 4
    innerPad := th.Size(theme.SizeNameInnerPadding) // 内容内边距 8

    // 内容区域 = 文字大小 + 两侧 innerPad
    textSize := fyne.MeasureText("Sample", th.Size(theme.SizeNameText), fyne.TextStyle{})
    return fyne.NewSize(textSize.Width+innerPad*2, textSize.Height+innerPad*2)
}

func (r *myRenderer) Layout(size fyne.Size) {
    th := r.w.Theme()
    innerPad := th.Size(theme.SizeNameInnerPadding)

    // 将文字定位在左边界 + innerPad 处，与 Label/Entry 对齐
    r.text.Move(fyne.NewPos(innerPad, innerPad))
    r.text.Resize(fyne.NewSize(size.Width-innerPad*2, size.Height-innerPad*2))
}
```

**关键数值**：
- `theme.SizeNamePadding`（默认 4）— 用于容器间元素间距
- `theme.SizeNameInnerPadding`（默认 8）— 用于控件内部内容的内边距

内置组件（Label、Entry、Button 等）统一使用这两个值，自定义 Widget 采用相同规范可保证视觉一致性。
