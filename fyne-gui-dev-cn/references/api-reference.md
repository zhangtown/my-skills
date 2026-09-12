# 完整 API 速查表

## 目录

**框架层（接口/约定，自定义 Widget 时必须理解）：**
- [CanvasObject 接口](#canvasobject-接口)
- [Widget 接口与 WidgetRenderer](#widget-接口与-widgetrenderer)
- [BaseWidget](#basewidget)
- [Layout 列表](#layout-列表)
- [事件接口](#事件接口)
- [数据绑定 API](#数据绑定-api)
- [App 接口](#app-接口)
- [Window 接口](#window-接口)
- [Canvas 接口](#canvas-接口)
- [OverlayStack](#overlaystack)
- [样式与主题 — Theme 接口](#样式与主题)
- [Geometry](#geometry) / [Device](#device) / [资源](#资源) / [存储](#存储) / [偏好存储](#偏好存储) / [动画](#动画)

**组件层（直接调用构造函数的成品）：**
- [Widget 列表](#widget-列表)
- [Container 列表](#container-列表)
- [Layout 列表](#layout-列表)
- [Canvas 原始图形](#canvas-原始图形)
- [对话框 API](#对话框-api)
- [菜单 API](#菜单-api)
- [快捷键](#快捷键)

**工具函数：**
- [关键函数](#关键函数)

---

## CanvasObject 接口

```go
type CanvasObject interface {
    MinSize() Size
    Move(Position)
    Position() Position
    Resize(Size)
    Size() Size
    Hide()
    Show()
    Visible() bool
    Refresh()
}
```

## Widget 接口与 WidgetRenderer

```go
type Widget interface {
    CanvasObject
    CreateRenderer() WidgetRenderer
}

type WidgetRenderer interface {
    Destroy()
    Layout(Size)
    MinSize() Size
    Objects() []CanvasObject
    Refresh()
}
```

`widget.NewSimpleRenderer(object)` 可用于只有一个 CanvasObject 的 Widget。

## BaseWidget

位于 `widget` 包，提供位置/大小/可见性/Refresh 的标准实现。

```go
type BaseWidget struct {
    size     fyne.Size
    position fyne.Position
    Hidden   bool
    // impl       fyne.Widget   // 内部字段
    // themeCache fyne.Theme    // 内部字段
}
```

关键方法：`ExtendBaseWidget(wid)` — 必须由扩展 Widget 的构造器调用。

`DisableableWidget` 扩展 BaseWidget，增加 `Enable()/Disable()/Disabled()`。

---

## 内置组件 (Component API)

以下均为框架内置的、可直接实例化的组件。它们内部实现了上述框架接口。

### Widget 列表

| Widget | 构造函数 | 数据绑定构造 | 说明 |
|--------|---------|------------|------|
| Label | `NewLabel(text)` | `NewLabelWithData(data)` | 文本标签 |
| Button | `NewButton(text, fn)` | `NewButtonWithData(name, icon, data, fn)` | 按钮 |
| Entry | `NewEntry()` | `NewEntryWithData(data)` | 单行输入 |
| MultiLineEntry | `NewMultiLineEntry()` | - | 多行输入 |
| PasswordEntry | `NewPasswordEntry()` | - | 密码输入 |
| EntryValidation | `NewEntryWithValidation(placeholder, validate)` | - | 验证输入, `.AlwaysShowValidationError` (v2.7+) |
| Select | `NewSelect(opts, fn)` | `NewSelectWithData(opts, data, fn)` | 下拉选择 |
| SelectEntry | `NewSelectEntry(opts)` | - | 可下拉输入 |
| Check | `NewCheck(label, fn)` | `NewCheckWithData(label, data)` | 复选框 |
| CheckGroup | `NewCheckGroup(opts, fn)` | - | 复选框组 |
| RadioGroup | `NewRadioGroup(opts, fn)` | - | 单选组 |
| Slider | `NewSlider(min, max)` | `NewSliderWithData(min, max, data)` | 滑块 |
| ProgressBar | `NewProgressBar()` | - | 进度条 |
| ProgressBarInfinite | `NewProgressBarInfinite()` | - | 无限进度 |
| Toolbar | `NewToolbar(items...)` | - | 工具栏 |
| Icon | `NewIcon(res)` | - | 图标 |
| Hyperlink | `NewHyperlink(text, url)` | - | 超链接 |
| Separator | `NewSeparator()` | - | 分割线 |
| Card | `NewCard(title, sub, content)` | - | 卡片 |
| Accordion | `NewAccordion(items...)` | - | 手风琴 |
| AccordionItem | `NewAccordionItem(title, detail)` | - | 手风琴项 |
| Form | `NewForm(items...)` | - | 表单 |
| FormItem | `NewFormItem(text, widget)` | - | 表单项 |
| List | `NewList(len, create, update)` | `NewListWithData(data, create, update)` | 虚拟列表 |
| Table | `NewTable(len, create, update)` | - | 虚拟表格 |
| Tree | `NewTree(childUIDs, isBranch, create, update)` | - | 树 |
| FileIcon | `NewFileIcon(uri)` | - | 文件图标 |
| TextGrid | `NewTextGrid()` | - | 文本网格 |
| Calendar | `NewCalendar(callback)` | - | 日历 |
| DateEntry | `NewDateEntry()` | - | 日期输入 |
| Activity | `NewActivity()` | - | 活动指示器 |
| Markdown | `NewMarkdown(content, onHyperlink)` | - | Markdown 渲染 |
| RichText | `NewRichText(segments...)` | - | 富文本（多段样式） |
| RichTextFromMarkdown | `NewRichTextFromMarkdown(content)` | - | Markdown → RichText |
| PopUp | `NewPopUp(content, canvas)` | - | 弹出层 |
| ModalPopUp | `NewModalPopUp(content, canvas)` | - | 模态弹出层（带遮罩） |
| PopUpMenu | `NewPopUpMenu(menu, canvas)` | - | 弹出菜单 |
| Selectable | - | - | `label.Selectable = true` 可选文本 (v2.6+) |
| PartialCheck | - | - | `check.Partial = true` 半选态 (v2.6+) |

### Container 列表

```go
// 基础容器
container.New(layout, objects...)
container.NewWithoutLayout(objects...)

// 布局容器
container.NewVBox(objects...)
container.NewHBox(objects...)
container.NewBorder(top, bottom, left, right, center...)
container.NewGridWithColumns(cols, objects...)
container.NewGridWithRows(rows, objects...)
container.NewGridWrap(size, objects...)
container.NewAdaptiveGrid(rowcols, objects...)
container.NewStack(objects...)
container.NewCenter(objects...)
container.NewPadded(objects...)
container.NewMax(obj1, obj2...)                   // v2.7+ 取最大 MinSize

// 特殊容器
container.NewScroll(content)
container.NewHSplit(left, right)          // offset 可调节
container.NewVSplit(top, bottom)
container.NewAppTabs(items...)
container.NewDocTabs(items...)
container.NewNavigation(content)          // v2.7+ 导航（带返回按钮）
container.NewNavigationWithTitle(content, title) // v2.7+ 带标题
container.NewClip(content)                // v2.7+ 裁剪超出内容
container.NewInnerWindow(title, content)

// TabItem
container.NewTabItem(text, content)
container.NewTabItemWithIcon(text, icon, content)
```

### Layout 列表

```go
layout.NewHBoxLayout()
layout.NewVBoxLayout()
layout.NewBorderLayout(top, bottom, left, right)
layout.NewGridLayout(cols)
layout.NewGridLayoutWithColumns(cols)
layout.NewGridLayoutWithRows(rows)
layout.NewGridWrapLayout(size)
layout.NewAdaptiveGridLayout(rowcols)
layout.NewFormLayout()
layout.NewPaddedLayout()
layout.NewCenterLayout()
layout.NewStackLayout()
layout.NewRowWrapLayout()                                // v2.7+ 水平换行
layout.NewRowWrapLayoutWithCustomPadding(hPad, vPad)     // v2.7+ 带自定义间距
layout.NewMaxLayout()                                    // v2.7+ 取子对象最大 MinSize
layout.NewSpacer()              // 弹性占位符（非 Layout，是 CanvasObject）
```

### Canvas 原始图形

```go
canvas.NewRectangle(color)
canvas.NewSquare(color)                                    // v2.7+ 正方形
canvas.NewCircle(color)
canvas.NewLine(color)                          // 必须 *canvas.Line
canvas.NewText("text", color)                  // 必须 *canvas.Text
canvas.NewImageFromResource(res)
canvas.NewImageFromFile(path)
canvas.NewImageFromImage(img)                  // 从 image.Image
canvas.NewImageFromReader(reader, name)
canvas.NewRaster(width, height, drawFn)
canvas.NewRasterWithDetails(w, h, pxColorFn)
canvas.NewLinearGradient(start, end)
canvas.NewHorizontalGradient(start, end)
canvas.NewVerticalGradient(start, end)
canvas.NewRadialGradient(center, radius)
canvas.NewCircleGradient(center, radius)
canvas.NewPolygon(sides, color)                            // v2.7+ 正多边形
canvas.NewRegularPolygon(sides, color)                     // v2.7+ 正多边形（居中）
canvas.NewArbitraryPolygon(points...)
canvas.NewArc(startAngle, endAngle, cutoutRatio, color)    // v2.7+ 圆弧（0=扇形, 0.5=环形, 1=缩为点）
canvas.NewPieArc(startAngle, endAngle, color)              // v2.7+ 扇形（cutout=0）
canvas.NewDoughnutArc(startAngle, endAngle, color)         // v2.7+ 环形（cutout=0.5）
canvas.NewBezierCurve(p0, p1, p2)             // 贝塞尔曲线
canvas.NewBlur(target)                         // 模糊效果（需 GPU 支持）
```

### Rectangle 属性 (v2.7+)

```go
rect := canvas.NewRectangle(color)
rect.CornerRadius = 10              // 统一圆角
rect.TopLeftCornerRadius = 8        // 四角独立圆角
rect.TopRightCornerRadius = 8
rect.BottomLeftCornerRadius = 4
rect.BottomRightCornerRadius = 4
rect.Aspect = 1.6                   // 宽高比约束（非零时约束最终尺寸）
// CornerRadius = min(width,height)/2 → "pill" 胶囊形
```

### ImageFill 模式 (v2.7+)

```go
img := canvas.NewImageFromFile("photo.jpg")
img.FillMode = canvas.ImageFillStretch    // 拉伸填充（默认）
img.FillMode = canvas.ImageFillContain   // 适配（保持比例，可能留白）
img.FillMode = canvas.ImageFillOriginal  // 原始尺寸（容器适配图片）
img.FillMode = canvas.ImageFillCover     // 覆盖（保持比例裁剪填满）
img.CornerRadius = 8                     // 图片圆角
```

## 数据绑定 API

### 值类型

```go
binding.NewBool()              → Bool
binding.NewFloat()             → Float
binding.NewInt()               → Int
binding.NewString()            → String
binding.NewURI()               → URI
binding.NewUntyped()           → Untyped (any)

// 方法：Get() / Set(val) / AddListener(l) / RemoveListener(l)
```

### 集合类型

```go
binding.NewBoolList()          → BoolList
binding.NewFloatList()         → FloatList
binding.NewIntList()           → IntList
binding.NewStringList()        → StringList

// 方法：Get() / Set([]T) / GetValue(index) / SetValue(index, val) / Append / Length
```

### 外部绑定

```go
binding.BindBool(&var)         → ExternalBool
binding.BindFloat(&var)        → ExternalFloat
binding.BindInt(&var)          → ExternalInt
binding.BindString(&var)       → ExternalString
binding.BindUntyped(&var)      → ExternalUntyped

// 注意：修改外部变量后需调用 .Reload() 通知监听器
```

### 集合外部绑定

```go
binding.BindBoolList(&var)
binding.BindFloatList(&var)
binding.BindIntList(&var)
binding.BindStringList(&var)
```

### 转换器

```go
binding.IntToString(Int)            → String
binding.FloatToString(Float)        → String
binding.BoolToString(Bool)          → String
binding.StringToInt(String)         → Int
binding.StringToFloat(String)       → Float
binding.StringToBool(String)        → Bool
binding.URIToString(URI)            → String
binding.StringToURI(String)         → URI
binding.FormatFloat(Float, format)  → String
binding.FormatInt(Int, format)      → String
binding.SPrintf(format, args...)    → String (通用格式化)
```

### Preferences 绑定

```go
binding.BindPreferenceBool(key, prefs)  → Bool (与 Preferences 双向同步)
binding.BindPreferenceFloat(key, prefs) → Float
binding.BindPreferenceInt(key, prefs)   → Int
binding.BindPreferenceString(key, prefs)→ String
```

### 树/映射绑定

```go
binding.NewStringTree()
binding.NewStringMap()
```

## 事件接口

```go
// 指针事件
Tappable          interface { Tapped(*PointEvent) }
DoubleTappable    interface { DoubleTapped(*PointEvent) }
SecondaryTappable interface { TappedSecondary(*PointEvent) }

// 键盘事件
Focusable         interface { FocusGained(); FocusLost(); TypedRune(rune); TypedKey(*KeyEvent) }
Tabbable          interface { AcceptsTab() bool }

// 其他
Scrollable        interface { Scrolled(*ScrollEvent) }
Draggable         interface { Dragged(*DragEvent); DragEnd() }
Disableable       interface { Enable(); Disable(); Disabled() bool }
Shortcutable      interface { TypedShortcut(Shortcut) }
```

### 事件结构体

```go
type PointEvent struct {
    AbsolutePosition Position
    Position         Position    // 相对触发对象的坐标
}

type KeyEvent struct {
    Name     KeyName            // 跨平台键名
    Physical HardwareKey
}

type ScrollEvent struct {
    PointEvent
    Scrolled Delta
}

type DragEvent struct {
    PointEvent
    Dragged Delta
}
```

### KeyName 常量

方向键：`KeyUp, KeyDown, KeyLeft, KeyRight`
功能键：`KeyF1..KeyF12, KeyEscape, KeyReturn, KeyTab, KeyBackspace, KeyInsert, KeyDelete`
导航键：`KeyPageUp, KeyPageDown, KeyHome, KeyEnd, KeySpace, KeyEnter`
字母键：`KeyA..KeyZ`
数字键：`Key0..Key9`
符号键：`KeyApostrophe, KeyComma, KeyMinus, KeyPeriod, KeySlash, KeyBackslash, KeyLeftBracket, KeyRightBracket, KeySemicolon, KeyEqual, KeyBackTick`

### KeyModifier

```go
KeyModifierShift   = 1 << iota
KeyModifierControl
KeyModifierAlt
KeyModifierSuper
```

## 快捷键

```go
type Shortcut interface { ShortcutName() string }
type KeyboardShortcut interface {
    Shortcut
    Key() KeyName
    Mod() KeyModifier
}

// 内置快捷键
&ShortcutCopy{Clipboard}
&ShortcutPaste{Clipboard}
&ShortcutCut{Clipboard}
&ShortcutSelectAll{}
&ShortcutUndo{}
&ShortcutRedo{}

// Canvas 级快捷键
canvas.AddShortcut(shortcut, handler)
canvas.RemoveShortcut(shortcut)
```

## 对话框 API

```go
// 信息类
dialog.ShowInformation(title, msg, parent)
dialog.ShowError(err, parent)
dialog.ShowConfirm(title, msg, callback, parent)

// 输入类
dialog.ShowEntry(title, msg, parent)
dialog.ShowText(title, msg, parent)
dialog.ShowForm(title, submit, cancel, items, callback, parent)
dialog.ShowCustom(title, dismiss, content, parent)

// 文件类
dialog.ShowFileOpen(callback, parent)
dialog.ShowFileSave(callback, parent)
dialog.ShowFolderOpen(callback, parent)

// 颜色
dialog.ShowColorPicker(title, msg, callback, parent)

// 进度
dialog.NewProgress(title, msg, parent)
dialog.NewProgressInfinite(title, msg, parent)
```

## 菜单 API

```go
// 菜单项
fyne.NewMenuItem(label, action)
fyne.NewMenuItemWithIcon(label, icon, action)
fyne.NewMenuItemSeparator()

// MenuItem 属性
item.ChildMenu = subMenu
item.Icon = iconResource
item.Shortcut = shortcut
item.Disabled = true
item.Checked = true
item.IsQuit = true

// 菜单
fyne.NewMenu(label, items...)
menu.Refresh()

// 主菜单栏
mainMenu := fyne.NewMainMenu(menus...)
window.SetMainMenu(mainMenu)
mainMenu.Refresh()
```

## 菜单/对话框关闭时信号（v2.6+）

```go
menuItem.Action = func() { ... }
// 未设置 Action 时，带 Shortcut 的菜单项会自动触发对应 Shortcut
```

## App 接口

```go
app.New()                                    // 创建应用
app.NewWithID("com.example.app")            // 带唯一 ID

// App 方法
app.NewWindow(title) Window
app.Run()                                    // 阻塞，启动事件循环
app.Quit()
app.Driver() Driver
app.Settings() Settings
app.Preferences() Preferences
app.Storage() Storage
app.Lifecycle() Lifecycle
app.Clipboard() Clipboard
app.Cache() Cache
app.OpenURL(url) error
app.SendNotification(*Notification)
app.ScheduleNotification(*Notification, time.Time) (*ScheduledNotification, error)
app.CancelScheduledNotification(id string) error
app.SetIcon(Resource)
app.Icon() Resource
app.CloudProvider() CloudProvider
app.SetCloudProvider(CloudProvider)
app.Metadata() AppMetadata
app.UniqueID() string
```

## Window 接口

```go
window.Title() string
window.SetTitle(string)
window.FullScreen() bool
window.SetFullScreen(bool)
window.Resize(Size)
window.RequestFocus()
window.FixedSize() bool
window.SetFixedSize(bool)
window.CenterOnScreen()
window.Padded() bool
window.SetPadded(bool)
window.Icon() Resource
window.SetIcon(Resource)
window.SetMaster()
window.MainMenu() *MainMenu
window.SetMainMenu(*MainMenu)
window.SetOnClosed(func())
window.SetCloseIntercept(func())          // 拦截关闭，需手动 window.Close()
window.SetOnDropped(func(Position, []URI))  // 拖放回调
window.Show()
window.Hide()
window.Close()
window.ShowAndRun()                       // Show() + Run()
window.Content() CanvasObject
window.SetContent(CanvasObject)
window.Canvas() Canvas
window.Clipboard() Clipboard              // Deprecated: 用 App.Clipboard()
```

## Canvas 接口

```go
canvas.Content() CanvasObject
canvas.SetContent(CanvasObject)
canvas.Refresh(CanvasObject)
canvas.Focus(Focusable)
canvas.FocusNext()
canvas.FocusPrevious()
canvas.Unfocus()
canvas.Focused() Focusable
canvas.Size() Size
canvas.Scale() float32                       // 当前显示器的缩放因子（120DPI 基准）
canvas.Overlays() OverlayStack
canvas.OnTypedRune() func(rune)
canvas.SetOnTypedRune(func(rune))
canvas.OnTypedKey() func(*KeyEvent)
canvas.SetOnTypedKey(func(*KeyEvent))
canvas.AddShortcut(shortcut, handler)
canvas.RemoveShortcut(shortcut)
canvas.Capture() image.Image                 // 截取 Canvas 为 image
canvas.PixelCoordinateForPosition(Position) (int, int) // 物理像素转换
canvas.InteractiveArea() (Position, Size)   // v1.4+
```

## OverlayStack

```go
type OverlayStack interface {
    Add(overlay CanvasObject)
    List() []CanvasObject
    Remove(overlay CanvasObject)
    Top() CanvasObject
}

canvas.Overlays().Add(widget.NewPopUp(...))
```

### PopUp 组件

```go
// Modal 弹窗（遮罩 + 点击外部自动关闭）
pop := widget.NewModalPopUp(content, canvas)
pop.Show()

// 普通 PopUp（无遮罩，需手动 Hide）
pop := widget.NewPopUp(content, canvas)
pop.Show()
pop.Hide()

// 弹出菜单（在指定位置显示）
menu := fyne.NewMenu("", fyne.NewMenuItem("Action", func() {}))
pop := widget.NewPopUpMenu(menu, canvas)
pop.ShowAtPosition(fyne.NewPos(100, 200))
```

### 桌面扩展 (driver/desktop)

```go
import "fyne.io/fyne/v2/driver/desktop"

// Hoverable 接口（MouseIn / MouseOut / MouseMoved）
// 自定义 Widget 实现此接口即可响应鼠标悬停
func (w *MyWidget) MouseIn(ev *desktop.MouseEvent)   { /* 鼠标进入 */ }
func (w *MyWidget) MouseOut()                         { /* 鼠标离开 */ }
func (w *MyWidget) MouseMoved(ev *desktop.MouseEvent) { /* 鼠标移动 */ }

// 自定义桌面快捷键
canvas.AddShortcut(&desktop.CustomShortcut{
    KeyName:  fyne.KeyS,
    Modifier: desktop.KeyModifierControl | desktop.KeyModifierShift,
}, func(shortcut fyne.Shortcut) { /* Save As... */ })

// 系统托盘
if desk, ok := app.(desktop.App); ok {
    desk.SetSystemTrayMenu(fyne.NewMenu("Tray",
        fyne.NewMenuItem("Show", func() { w.Show() }),
        fyne.NewMenuItem("Quit", func() { app.Quit() }),
    ))
}
```

### 迁移检查

```bash
# 扫描已废弃 API
rg "NewContainer\b" .                  # → container.New / NewWithoutLayout
rg "NewContainerWithLayout\b" .        # → container.New
rg "DarkTheme\|LightTheme" .           # → theme.DefaultTheme()（v3.0 移除）
rg "fyne\.Do\b" .                      # v2.6+ 检查是否在主 goroutine 误用
```

## Geometry

```go
type Position struct { X, Y float32 }
func NewPos(x, y float32) Position
func NewSquareOffsetPos(length float32) Position  // v2.4+
(p Position) Add(Vector2) Position
(p Position) AddXY(x, y float32) Position
(p Position) Subtract(Vector2) Position
(p Position) SubtractXY(x, y float32) Position
(p Position) Components() (float32, float32)
(p Position) IsZero() bool

type Size struct { Width, Height float32 }
func NewSize(w, h float32) Size
func NewSquareSize(side float32) Size            // v2.4+
(s Size) Max(Vector2) Size
(s Size) Min(Vector2) Size
(s Size) Add(Vector2) Size
(s Size) Subtract(Vector2) Size
(s Size) AddWidthHeight(w, h float32) Size
(s Size) SubtractWidthHeight(w, h float32) Size
(s Size) Components() (float32, float32)
(s Size) IsZero() bool

type Delta struct { DX, DY float32 }
```

## Device

```go
type Device interface {
    Orientation() DeviceOrientation
    IsMobile() bool
    IsBrowser() bool
    HasKeyboard() bool
    SystemScaleForWindow(Window) float32
    Locale() Locale
}

fyne.CurrentDevice()

// DeviceOrientation
OrientationVertical / OrientationVerticalUpsideDown
OrientationHorizontalLeft / OrientationHorizontalRight

fyne.IsVertical(orient) bool
fyne.IsHorizontal(orient) bool
```

## 资源

```go
type Resource interface {
    Name() string
    Content() []byte
}

type ThemedResource interface {      // v2.5+
    Resource
    ThemeColorName() ThemeColorName
}

// 创建资源
fyne.NewStaticResource(name, content []byte)
fyne.LoadResourceFromPath(path)
fyne.LoadResourceFromURLString(url)
fyne.CacheResourceFromURLString(url) // v2.8+ 自动缓存

// 主题适配资源（图标在不同主题色下的变体）
theme.NewThemedResource(res)           // 前景色
theme.NewDisabledThemedResource(res)   // 禁用色
theme.NewErrorThemedResource(res)      // 错误色
theme.NewInvertedThemedResource(res)   // 反转色（浅色前景）
theme.NewPrimaryThemedResource(res)    // 主色

// 嵌入资源
//go:generate fyne bundle -o bundled.go icon.png
```

## 偏好存储

```go
prefs := app.Preferences()
prefs.Bool(key) / SetBool(key, val) / BoolWithFallback(key, fallback)
prefs.Int(key) / SetInt(key, val) / IntWithFallback(key, fallback)
prefs.Float(key) / SetFloat(key, val) / FloatWithFallback(key, fallback)
prefs.String(key) / SetString(key, val) / StringWithFallback(key, fallback)
// v2.4+ 列表
prefs.BoolList(key) / SetBoolList(key, val) / BoolListWithFallback(key, fallback)
prefs.FloatList(key) / SetFloatList(key, val) / FloatListWithFallback(key, fallback)
prefs.IntList(key) / SetIntList(key, val) / IntListWithFallback(key, fallback)
prefs.StringList(key) / SetStringList(key, val) / StringListWithFallback(key, fallback)
prefs.RemoveValue(key)
prefs.AddChangeListener(func())
prefs.ChangeListeners() []func()
```

## 存储

```go
type Storage interface {
    RootURI() URI
    Create(name string) (URIWriteCloser, error)
    Open(name string) (URIReadCloser, error)
    Save(name string) (URIWriteCloser, error)
    Remove(name string) error
    RemoveAll(name string) error  // v2.7+ 递归删除
    List() []string
}
```

## 动画

```go
type Animation struct {
    AutoReverse bool
    Curve       AnimationCurve
    Duration    time.Duration
    RepeatCount int
    Tick        func(float32)
}

fyne.NewAnimation(duration, tickFn)
anim.Start() / anim.Stop()

// 内置曲线
fyne.AnimationLinear
fyne.AnimationEaseIn
fyne.AnimationEaseOut
fyne.AnimationEaseInOut  // 默认
fyne.AnimationRepeatForever // = -1
```

## 关键函数

```go
// 线程调度
fyne.Do(fn)              // 非阻塞，调度到主 goroutine
fyne.DoAndWait(fn)       // 阻塞，等待 fn 执行完

// 应用
fyne.CurrentApp() App
fyne.CurrentDevice() Device

// 日志
fyne.LogError(reason, err)

// 通知
fyne.NewNotification(title, content)

// 数学
fyne.Min(a, b float32) float32
fyne.Max(a, b float32) float32
```

## 样式与主题

### TextStyle — 文本样式

```go
type TextStyle struct {
    Bold          bool  // 粗体
    Italic        bool  // 斜体
    Monospace     bool  // 等宽字体
    Symbol        bool  // 符号字体（v2.2+）
    TabWidth      int   // Tab 宽度（空格数，v2.1+）
    Underline     bool  // 下划线（v2.5+）
    Strikethrough bool  // 删除线（v2.8+）
}
```

### TextAlign — 文本对齐

```go
TextAlignLeading  / TextAlignCenter / TextAlignTrailing
```

### TextWrap — 文本换行

```go
TextWrapOff      // 不换行，撑开宽度
TextWrapBreak    // 按字符换行
TextWrapWord     // 按单词换行
```

### TextTruncation — 文本截断（v2.4+）

```go
TextTruncateOff       // 不截断（默认）
TextTruncateClip      // 裁切
TextTruncateEllipsis  // 结尾加省略号
```

### fyne.MeasureText — 测量文本尺寸

```go
size := fyne.MeasureText("Hello", 14, fyne.TextStyle{Bold: true})
// 返回 fyne.Size{Width, Height}
```

### Theme 接口

```go
type Theme interface {
    Color(ThemeColorName, ThemeVariant) color.Color
    Font(TextStyle) Resource
    Icon(ThemeIconName) Resource
    Size(ThemeSizeName) float32
}
```

### ThemeVariant

```go
theme.VariantLight  // 浅色
theme.VariantDark   // 深色
```

### 获取当前主题

```go
theme.Current()                // 获取当前应用主题
theme.CurrentForWidget(w)      // 获取指定 Widget 的主题（考虑 ThemeOverride）
```

### 主题便捷函数（v2.5+，可直接用，无需获取 Theme 对象）

```go
theme.Color(name)              // 当前主题颜色
theme.ColorForWidget(name, w)  // 指定 Widget 主题颜色
theme.Size(name)               // 当前主题尺寸
theme.SizeForWidget(name, w)   // 指定 Widget 主题尺寸
theme.Font(style)              // 当前主题字体
```

### 预定义主题

```go
theme.DefaultTheme()    // 自适应浅色/深色（推荐）
theme.LightTheme()      // 浅色（Deprecated, v3.0 移除）
theme.DarkTheme()       // 深色（Deprecated, v3.0 移除）
```

### Primary 色彩名称常量

```go
theme.ColorRed     theme.ColorOrange   theme.ColorYellow
theme.ColorGreen   theme.ColorBlue     theme.ColorPurple
theme.ColorBrown   theme.ColorGray

// 获取所有可选颜色名称
theme.PrimaryColorNames()  // []string
```

通过 `app.Settings().PrimaryColor()` 获取/设置用户偏好的主色调。

### 完整 ThemeColorName 常量列表

```go
// 基础
theme.ColorNamePrimary              // 主色调
theme.ColorNameBackground           // 背景
theme.ColorNameForeground           // 前景（文字/图标）
theme.ColorNameForegroundOnPrimary  // 主色调上的对比色（v2.5+）
theme.ColorNameForegroundOnError    // 错误色上的对比色（v2.5+）
theme.ColorNameForegroundOnSuccess  // 成功色上的对比色（v2.5+）
theme.ColorNameForegroundOnWarning  // 警告色上的对比色（v2.5+）

// 交互状态
theme.ColorNameButton               // 按钮色
theme.ColorNameDisabledButton       // 禁用态按钮
theme.ColorNameDisabled             // 禁用态前景
theme.ColorNameHover                // 悬停高亮
theme.ColorNamePressed              // 按下高亮
theme.ColorNameFocus                // 焦点高亮
theme.ColorNameSelection            // 选中高亮（v2.1+）

// 输入组件
theme.ColorNameInputBackground      // 输入框背景
theme.ColorNameInputBorder          // 输入框边框（v2.3+）
theme.ColorNamePlaceHolder          // 占位符文字

// 语义色
theme.ColorNameError                // 错误
theme.ColorNameSuccess              // 成功（v2.3+）
theme.ColorNameWarning              // 警告（v2.3+）
theme.ColorNameHyperlink            // 超链接（v2.4+）

// 组件色
theme.ColorNameScrollBar            // 滚动条
theme.ColorNameScrollBarBackground  // 滚动条背景（v2.6+）
theme.ColorNameShadow               // 阴影
theme.ColorNameSeparator            // 分割线（v2.3+）
theme.ColorNameHeaderBackground     // 表格/列表头部背景（v2.4+）
theme.ColorNameMenuBackground       // 菜单背景（v2.3+）
theme.ColorNameOverlayBackground    // 浮层背景（对话框等）（v2.3+）

// 内嵌窗口（v2.8+）
theme.ColorNameInnerWindowBorder           // 内嵌窗口边框
theme.ColorNameInnerWindowBorderInactive   // 非活跃内嵌窗口边框
```

### 完整 ThemeSizeName 常量列表

```go
// 文字尺寸
theme.SizeNameText            // 正文 14px
theme.SizeNameHeadingText     // 标题 24px（v2.1+）
theme.SizeNameSubHeadingText  // 副标题 18px（v2.1+）
theme.SizeNameCaptionText     // 辅助文字 11px

// 间距
theme.SizeNamePadding              // 外边距 4px
theme.SizeNameInnerPadding         // 内边距 8px（v2.3+）
theme.SizeNameLineSpacing          // 行间距 4px（v2.3+）
theme.SizeNameInlineIcon           // 内嵌图标 20px
theme.SizeNameSeparatorThickness   // 分割线粗细 1px

// 输入组件
theme.SizeNameInputBorder          // 输入边框 1px
theme.SizeNameInputRadius          // 输入圆角 5px（v2.4+）
theme.SizeNameSelectionRadius      // 选中圆角 3px（v2.4+）

// 滚动条
theme.SizeNameScrollBar            // 滚动条 12px
theme.SizeNameScrollBarSmall       // 小滚动条 3px
theme.SizeNameScrollBarRadius      // 滚动条圆角 3px（v2.5+）

// 按钮（v2.8+）
theme.SizeNameButtonRadius         // 按钮圆角 5px

// 内嵌窗口（v2.6+）
theme.SizeNameWindowButtonHeight   // 窗口按钮高度 16px
theme.SizeNameWindowButtonRadius   // 窗口按钮圆角 8px
theme.SizeNameWindowButtonIcon     // 窗口按钮图标 14px
theme.SizeNameWindowTitleBarHeight // 标题栏高度 26px
theme.SizeNameInnerWindowRadius    // 窗口圆角 5px（v2.8+）

// 其它
theme.SizeNameSplitThickness       // 分割面板厚度（v2.8+）
theme.SizeNameModalBlurRadius      // 弹窗模糊半径（v2.7+）
```

### 尺寸便捷函数

```go
theme.Padding()              // 外边距
theme.InnerPadding()         // 内边距
theme.TextSize()             // 正文字号
theme.TextHeadingSize()      // 标题字号
theme.TextSubHeadingSize()   // 副标题字号
theme.CaptionTextSize()      // 辅助文字字号
theme.IconInlineSize()       // 内嵌图标尺寸
theme.ScrollBarSize()        // 滚动条尺寸
theme.ScrollBarSmallSize()   // 小滚动条尺寸
theme.InputBorderSize()      // 输入边框尺寸
theme.InputRadiusSize()      // 输入圆角尺寸
theme.SelectionRadiusSize()  // 选中圆角尺寸
theme.LineSpacing()          // 行间距
theme.SeparatorThicknessSize() // 分割线粗度
```

### 完整 ThemeIconName 常量列表

```go
// 导航/操作
theme.IconNameCancel        theme.IconNameConfirm      theme.IconNameDelete
theme.IconNameSearch        theme.IconNameSearchReplace theme.IconNameMenu
theme.IconNameMenuExpand

// 表单控件
theme.IconNameCheckButton              // 未选中复选框
theme.IconNameCheckButtonChecked       // 已选中复选框
theme.IconNameCheckButtonFill          // 填充复选框（v2.5+）
theme.IconNameCheckButtonPartial       // 半选（v2.6+）
theme.IconNameRadioButton              // 未选中单选
theme.IconNameRadioButtonChecked       // 已选中单选
theme.IconNameRadioButtonFill          // 填充单选（v2.5+）

// 颜色
theme.IconNameColorAchromatic   theme.IconNameColorChromatic   theme.IconNameColorPalette

// 内容操作
theme.IconNameContentAdd     theme.IconNameContentRemove    theme.IconNameContentCut
theme.IconNameContentCopy    theme.IconNameContentPaste     theme.IconNameContentClear
theme.IconNameContentRedo    theme.IconNameContentUndo

// 状态
theme.IconNameInfo          theme.IconNameQuestion       theme.IconNameWarning
theme.IconNameError         theme.IconNameBrokenImage    // v2.4+

// 文档
theme.IconNameDocument        theme.IconNameDocumentCreate
theme.IconNameDocumentPrint   theme.IconNameDocumentSave

// 邮件
theme.IconNameMailAttachment  theme.IconNameMailCompose   theme.IconNameMailForward
theme.IconNameMailReply       theme.IconNameMailReplyAll  theme.IconNameMailSend

// 媒体
theme.IconNameMediaMusic       theme.IconNameMediaPhoto       theme.IconNameMediaVideo
theme.IconNameMediaFastForward theme.IconNameMediaFastRewind
theme.IconNameMediaPause       theme.IconNameMediaPlay
theme.IconNameMediaSkipNext    theme.IconNameMediaSkipPrevious
theme.IconNameMediaRecord      theme.IconNameMediaReplay
theme.IconNameMediaStop

// 导航
theme.IconNameNavigateBack     theme.IconNameNavigateNext
theme.IconNameArrowDropDown    theme.IconNameArrowDropUp
theme.IconNameMoreHorizontal   theme.IconNameMoreVertical

// 文件
theme.IconNameFile             theme.IconNameFileApplication
theme.IconNameFileAudio        theme.IconNameFileImage
theme.IconNameFileVideo        theme.IconNameFileText

// 视图
theme.IconNameViewFullScreen   theme.IconNameViewRefresh
theme.IconNameViewZoomFit      theme.IconNameViewZoomIn
theme.IconNameViewZoomOut

// 账户
theme.IconNameAccount          theme.IconNameLogin
theme.IconNameLogout

// 列表
theme.IconNameList             theme.IconNameGrid

// 内嵌窗口（v2.5+）
theme.IconNameDragCornerIndicator

// 其他
theme.IconNameComputer         theme.IconNameDownload
theme.IconNameFavorite         theme.IconNameHelp
theme.IconNameHome             theme.IconNameMove
theme.IconNameSettings         theme.IconNameStorage
theme.IconNameUpload           theme.IconNameVisibility
theme.IconNameVisibilityOff    theme.IconNameVolumeDown
theme.IconNameVolumeMute       theme.IconNameVolumeUp
```

### 图标便捷函数（返回 fyne.Resource）

```go
theme.CancelIcon()               theme.ConfirmIcon()
theme.DeleteIcon()               theme.SearchIcon()
theme.MenuIcon()                 theme.MenuExpandIcon()
theme.CheckButtonIcon()          theme.CheckButtonCheckedIcon()
theme.RadioButtonIcon()          theme.RadioButtonCheckedIcon()
theme.InfoIcon()                 theme.QuestionIcon()
theme.WarningIcon()              theme.ErrorIcon()
theme.DocumentIcon()             theme.DocumentCreateIcon()
theme.DocumentPrintIcon()        theme.DocumentSaveIcon()
theme.MailComposeIcon()          theme.MailSendIcon()
theme.MediaPlayIcon()            theme.MediaPauseIcon()
theme.MediaRecordIcon()          theme.MediaStopIcon()
theme.MediaFastForwardIcon()     theme.MediaFastRewindIcon()
theme.ContentAddIcon()           theme.ContentRemoveIcon()
theme.ContentCutIcon()           theme.ContentCopyIcon()
theme.ContentPasteIcon()         theme.ContentUndoIcon()
theme.ContentRedoIcon()          theme.NavigateBackIcon()
theme.NavigateNextIcon()         theme.ViewFullScreenIcon()
theme.ViewRefreshIcon()          theme.AccountIcon()
theme.LoginIcon()                theme.LogoutIcon()
theme.SettingsIcon()             theme.HomeIcon()
theme.HelpIcon()                 theme.DownloadIcon()
theme.UploadIcon()               theme.ComputerIcon()
theme.StorageIcon()              theme.FileIcon()
theme.FileApplicationIcon()      theme.FileAudioIcon()
theme.FileImageIcon()            theme.FileVideoIcon()
theme.FileTextIcon()             theme.FavoriteIcon()
theme.ListIcon()                 theme.GridIcon()
theme.VisibilityIcon()           theme.VisibilityOffIcon()
```

### 字体便捷函数

```go
theme.TextFont()                // 常规字体
theme.TextBoldFont()            // 粗体
theme.TextItalicFont()          // 斜体
theme.TextBoldItalicFont()      // 粗斜体
theme.TextMonospaceFont()       // 等宽字体
theme.SymbolFont()              // 符号字体
theme.DefaultEmojiFont()        // Emoji 字体

// 默认字体资源
theme.DefaultTextFont()
theme.DefaultTextBoldFont()
theme.DefaultTextBoldItalicFont()
theme.DefaultTextItalicFont()
theme.DefaultTextMonospaceFont()
theme.DefaultSymbolFont()
```

### 自定义字体（环境变量）

```bash
FYNE_FONT=/path/to/font.ttf         # 主字体
FYNE_FONT_MONOSPACE=/path/to/mono.ttf  # 等宽字体
FYNE_FONT_SYMBOL=/path/to/symbol.ttf   # 符号字体
```

### 完整自定义主题模板

```go
type MyTheme struct{}

func (t MyTheme) Color(name fyne.ThemeColorName, v fyne.ThemeVariant) color.Color {
    switch name {
    case theme.ColorNamePrimary:
        return color.NRGBA{R: 70, G: 130, B: 255, A: 255}
    case theme.ColorNameBackground:
        if v == theme.VariantLight {
            return color.White
        }
        return color.NRGBA{R: 0x17, G: 0x17, B: 0x18, A: 255}
    default:
        return theme.DefaultTheme().Color(name, v) // 回退到默认
    }
}

func (t MyTheme) Font(style fyne.TextStyle) fyne.Resource {
    if style.Monospace {
        return resourceMyMonoFont  // 自定义等宽字体
    }
    return theme.DefaultTheme().Font(style)
}

func (t MyTheme) Icon(name fyne.ThemeIconName) fyne.Resource {
    return theme.DefaultTheme().Icon(name)
}

func (t MyTheme) Size(name fyne.ThemeSizeName) float32 {
    switch name {
    case theme.SizeNameText:
        return 16 // 自定义正文字号
    case theme.SizeNamePadding:
        return 6
    default:
        return theme.DefaultTheme().Size(name)
    }
}
```

### 应用主题

```go
// 全局主题
a.Settings().SetTheme(&MyTheme{})

// 局部主题覆写（仅影响容器内的子树）
container.NewThemeOverride(&MyTheme{}, content)
```
