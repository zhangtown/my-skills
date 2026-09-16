# 测试完整指南

## 目录

- [测试环境创建](#测试环境创建)
- [模拟用户交互](#模拟用户交互)
- [验证渲染结果](#验证渲染结果)
- [完整测试示例](#完整测试示例)
- [CI 集成](#ci-集成)
- [测试最佳实践](#测试最佳实践)
- [特性测试示例](#特性测试示例)

---

`fyne.io/fyne/v2/test` 包提供纯内存中的 UI 测试能力，无需图形驱动。

## 测试环境创建

```go
import "fyne.io/fyne/v2/test"

// 创建内存 Canvas
c := test.NewCanvas()
c.SetContent(myWidget)
c.Resize(fyne.NewSize(400, 300))

// 创建内存 App（含 Preferences、Storage、Clipboard）
a := test.NewApp()
w := a.NewWindow("Test")
```

## 模拟用户交互

### 点击

```go
// 对 Tappable 对象点击
test.Tap(btn)

// 指定位置点击
test.TapAt(widget, fyne.NewPos(10, 10))

// Canvas 绝对坐标点击
test.TapCanvas(canvas, fyne.NewPos(100, 50))

// 双击
test.DoubleTap(btn)

// 右键点击
test.TapSecondary(widget)
test.TapSecondaryAt(widget, fyne.NewPos(5, 5))
```

### 键盘输入

```go
// 先 FocusGained，再逐字符输入
test.Type(entry, "Hello World")

// Canvas 级别的输入（触发 OnTypedRune）
test.TypeOnCanvas(canvas, "text")
```

### 拖动与滚动

```go
// 从 pos 开始拖动 deltaX, deltaY
test.Drag(canvas, fyne.NewPos(50, 50), 30, 10)

// 滚动
test.Scroll(canvas, fyne.NewPos(100, 100), 0, -50) // 向上滚动
```

### 鼠标移动

```go
// 模拟鼠标移动（触发 Hoverable.MouseIn/MouseMoved/MouseOut）
test.MoveMouse(canvas, fyne.NewPos(100, 100))
```

### 焦点控制

```go
test.FocusNext(canvas)
test.FocusPrevious(canvas)
```

## 验证渲染结果

### 通过 WidgetRenderer

```go
func TestLabelText(t *testing.T) {
    label := widget.NewLabel("Hello")
    r := test.WidgetRenderer(label)

    // 检查渲染对象数量
    objs := r.Objects()
    if len(objs) != 1 {
        t.Fatalf("expected 1 object, got %d", len(objs))
    }

    // 检查渲染对象内容
    text := objs[0].(*canvas.Text)
    if text.Text != "Hello" {
        t.Errorf("expected 'Hello', got '%s'", text.Text)
    }
}
```

### RenderToMarkup（v2.6.0+）

```go
// 对象级别快照
markup := test.RenderObjectToMarkup(myWidget)
if !strings.Contains(markup, "expected text") {
    t.Error("text not found in markup")
}

// Canvas 级别快照
snapshot := test.RenderToMarkup(canvas)
```

### 检查布局结果

```go
// LaidOutObjects 返回经过 Layout 后的所有子对象
objects := test.LaidOutObjects(container)
for _, obj := range objects {
    t.Logf("pos=%v size=%v visible=%v", obj.Position(), obj.Size(), obj.Visible())
}
```

## 完整测试示例

### Widget 功能测试

```go
func TestButton_Tap(t *testing.T) {
    clicked := false
    btn := widget.NewButton("Click me", func() {
        clicked = true
    })

    test.Tap(btn)

    if !clicked {
        t.Error("callback should have been triggered")
    }
}
```

### Widget 渲染测试

```go
func TestButton_Layout(t *testing.T) {
    btn := widget.NewButton("Submit", nil)
    r := test.WidgetRenderer(btn)

    // 验证最小尺寸
    min := r.MinSize()
    if min.Width <= 0 || min.Height <= 0 {
        t.Error("MinSize should be positive")
    }

    // 设置尺寸后验证
    r.Layout(fyne.NewSize(200, 40))
    objs := r.Objects()
    // objs[0] 是背景，objs[1] 是文本
    if objs[0].Size().Width != 200 {
        t.Error("background should fill widget")
    }
}
```

### 自定义 Widget 测试

```go
func TestMyWidget_Rendering(t *testing.T) {
    w := NewMyWidget("test", nil)

    c := test.NewCanvas()
    c.SetContent(w)
    c.Resize(fyne.NewSize(200, 100))

    r := test.WidgetRenderer(w)
    objs := r.Objects()

    // 验证背景
    bg := objs[0].(*canvas.Rectangle)
    if bg.Size().Width != 200 {
        t.Error("background should fill")
    }

    // 验证文字
    for _, obj := range objs {
        if text, ok := obj.(*canvas.Text); ok {
            if text.Text != "test" {
                t.Errorf("expected 'test', got '%s'", text.Text)
            }
        }
    }
}
```

### 数据绑定测试

```go
func TestEntryWithData(t *testing.T) {
    data := binding.NewString()
    data.Set("initial")

    entry := widget.NewEntryWithData(data)

    test.Type(entry, "new value")

    got, _ := data.Get()
    if got != "new value" {
        t.Errorf("data should be 'new value', got '%s'", got)
    }
}
```

### 焦点链测试

```go
func TestFocusChain(t *testing.T) {
    e1 := widget.NewEntry()
    e2 := widget.NewEntry()

    c := test.NewCanvas()
    c.SetContent(container.NewVBox(e1, e2))

    test.FocusNext(c)
    first := c.Focused()
    test.FocusNext(c)
    second := c.Focused()

    if first == second {
        t.Error("focus should have moved")
    }
    if first.(fyne.Focusable) != e1 {
        t.Error("first focused should be e1")
    }
}
```

### 布局测试

```go
func TestVBoxLayout(t *testing.T) {
    l1 := widget.NewLabel("Item 1")
    l2 := widget.NewLabel("Item 2")

    box := container.NewVBox(l1, l2)

    c := test.NewCanvas()
    c.SetContent(box)
    c.Resize(fyne.NewSize(400, 200))

    // 验证 l1 在 l2 上方
    if l1.Position().Y >= l2.Position().Y {
        t.Error("l1 should be above l2")
    }
}
```

### 隐藏/显示测试

```go
func TestHideShow(t *testing.T) {
    label := widget.NewLabel("visible")
    if !label.Visible() {
        t.Fatal("should be visible by default")
    }

    label.Hide()
    if label.Visible() {
        t.Fatal("should be hidden")
    }

    label.Show()
    if !label.Visible() {
        t.Fatal("should be visible again")
    }
}
```

### 禁用测试

```go
func TestDisable(t *testing.T) {
    btn := widget.NewButton("Click", func() { t.Log("clicked") })
    btn.Disable()

    if !btn.Disabled() {
        t.Fatal("should be disabled")
    }

    test.Tap(btn) // 禁用的按钮不应触发回调

    btn.Enable()
    if btn.Disabled() {
        t.Fatal("should be enabled")
    }
}
```

## CI 集成

```bash
# 使用 ci tag 在 CI 环境运行测试（无图形驱动）
go test -tags ci ./...

# 或仅运行 Fyne 相关测试
go test -tags ci -run "TestWidget" ./...
```

## 测试最佳实践

1. **使用 test.NewCanvas()** — 比真实窗口快得多，不需要图形环境
2. **通过 WidgetRenderer 检查** — 验证渲染对象内容而非手动截图
3. **测试 MinSize** — 确保在不同布局中都有合理的尺寸
4. **测试布局行为** — 将 Widget 放入容器，验证 Layout 后的位置和尺寸
5. **不要用 time.Sleep** — 测试框架中所有操作是同步的
6. **给测试挂上 ci tag** — `//go:build ci` 确保在 CI 中也能运行
7. **每个 Widget 至少写 3 类测试**：构造/渲染、交互（Tap/Type）、状态变更（Show/Hide/Enable）

## 特性测试示例

### Label.Selectable (v2.6+)

```go
func TestLabel_Selectable(t *testing.T) {
    label := widget.NewLabel("select me")
    label.Selectable = true

    c := test.NewCanvas()
    c.SetContent(label)
    c.Resize(fyne.NewSize(200, 50))

    selected := label.SelectedText()
    if selected != "" {
        t.Error("no text should be selected initially")
    }

    // 模拟选择操作后验证
    // 注意：Selection 操作需要完整的焦点和拖拽交互
}
```

### Check.Partial半选态 (v2.6+)

```go
func TestCheck_Partial(t *testing.T) {
    check := widget.NewCheck("Select All", nil)
    
    // 设置为半选态
    check.Partial = true
    check.Refresh()

    // 验证状态
    if !check.Partial {
        t.Error("check should be in Partial state")
    }

    // 点击应清除 Partial，切换到 Checked
    test.Tap(check)
    if check.Partial {
        t.Error("tapping should clear Partial state")
    }
    if !check.Checked {
        t.Error("check should be checked after tap")
    }
}
```
