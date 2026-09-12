# Windows 窗口层：无边框 + DWM 系统投影

目标形态：**无系统边框**（自己画 46px 顶栏）+ **DWM 系统投影**（四边柔和）+ Win11 圆角 +
内容铺满整个窗口矩形（客户区 == 窗口矩形）。

## 为什么不能只做 `WS_POPUP`

Fyne 的 `Decorated=false` 在 win32 上落到 `WS_POPUP`：有任务栏按钮（`WS_EX_APPWINDOW`），
但**既没有系统描边也没有 DWM 阴影**，在浅色桌面上窗口边界完全消失。
DWM 只给"有框窗口"画投影——所以解法是**给无边框窗口补回 `WS_THICKFRAME`，
再用 `WM_NCCALCSIZE` 把边框吃掉**。这和 Electron（`thickFrame`）、Tauri 在 Win11 上的做法同源。

## 实现位置（三层，缺一不可）

### 1. Fyne 侧：无边框开关

`cmd/gui/titlebar_windows.go`：

```go
const (
	windowTitle  = "RemoteNet"          // 原生标题栏与自绘顶栏共用
	envFrameless = "REMOTENET_FRAMELESS"

	titleBarH     = 46 // 顶栏高度
	barSidePad    = 10 // 顶栏左右内边距
	barLogoSize   = 28 // 顶栏 logo（系统标题栏只有 16px，太小的自制栏会显得廉价）
	gripThickness = 5  // 右/下边缘缩放热区厚度
	gripCorner    = 14 // 右下角缩放热区边长
)

// 必须在 NewWindow 之前调用
func enableFrameless() { _ = os.Setenv(envFrameless, "1") }
```

`vendor/fyne.io/fyne/v2/internal/driver/glfw/window_desktop.go` 的 `create()` 读这个环境变量，
决定 `glfw.Decorated`（复用的是 splash 窗口早就存在的 decorate=false 通道）。

### 2. glfw C 侧：补 `WS_THICKFRAME` + 吃掉边框 + 圆角

`vendor/github.com/go-gl/glfw/v3.4/glfw/glfw/src/win32_window.c`：

```c
// 无边框窗口真正下发到 Win32 的样式：补 WS_THICKFRAME 让 DWM 画投影。
// 只能在这里补：getWindowStyle() 的返回值会被二十多处 AdjustWindowRectEx 拿去算
// 「客户区 → 窗口矩形」，那些地方的边框宽度必须按 0 算（客户区铺满窗口矩形）。
static DWORD getNativeWindowStyle(const _GLFWwindow* window)
{
    DWORD style = getWindowStyle(window);
    if (!window->monitor && !window->decorated)
        style |= WS_THICKFRAME;
    return style;
}

// 算「客户区 → 窗口矩形」时用：边框按 0 算，否则 SetWindowPos 出来的客户区会大出 2x 边框宽
static DWORD getFrameCalcStyle(const _GLFWwindow* window, DWORD style)
{
    if (!window->monitor && !window->decorated)
        style &= ~(WS_THICKFRAME | WS_CAPTION);
    return style;
}
```

- `createNativeWindow()`：`CreateWindowExW(..., getNativeWindowStyle(window), ...)`；
- `windowProc()`：`if (wParam && !window->monitor && !window->decorated) return 0;`（`WM_NCCALCSIZE`），
  返回 0 表示**客户区 == 窗口矩形**——这是 Chromium/Electron 无边框窗口的同款做法；
- `updateWindowStyles()`：`style |= getNativeWindowStyle(window) & WS_THICKFRAME;`
  （`WS_THICKFRAME` 是 `WS_OVERLAPPEDWINDOW` 的一部分，会被上一行的清除操作抹掉），
  两处 `AdjustWindowRectEx*` 改用 `getFrameCalcStyle(window, style)`；
- 建窗后设圆角与描边：

```c
DWORD corner = DWMWCP_ROUND;            // 2
DWORD border = DWMWA_COLOR_NONE;        // 0xFFFFFFFE
DwmSetWindowAttribute(hwnd, DWMWA_WINDOW_CORNER_PREFERENCE, &corner, sizeof(corner)); // 33
DwmSetWindowAttribute(hwnd, DWMWA_BORDER_COLOR, &border, sizeof(border));             // 34
```

`DwmSetWindowAttribute` 是**动态加载**的：在 `win32_platform.h` 里加
`PFN_DwmSetWindowAttribute` typedef + `#define` + `dwmapi` 结构体字段，
在 `win32_init.c` 里 `_glfwPlatformGetModuleSymbol(..., "DwmSetWindowAttribute")`，
并把 `DWMWA_*` / `DWMWCP_*` / `DWMWA_COLOR_NONE` 用 `#ifndef` 兜底（老 SDK 头文件里没有）。

### 3. 拖动 / 缩放

- 拖动和缩放走 `SetWindowPos`，**不要**用 `DefWindowProc` 的移动/缩放循环：
  后者是模态循环，会卡住 Fyne 的事件循环，拖动时画面发花（踩过）。
- `WM_NCHITTEST` 返回热区：右/下边缘 `gripThickness=5`，右下角 `gripCorner=14`。
- 缩放热区在客户区之内（因为客户区 == 窗口矩形），所以要在布局里给它们留位置。

## 被实测否掉的做法（别再用）

| 做法 | 实测结果 |
|---|---|
| 类样式 `CS_DROPSHADOW`（`wc.style \|= CS_DROPSHADOW`） | 只有**右下 5px 硬边**：窗外 1..6px = 142/171/212/241/252/255，左边和上边**完全没有投影**；右下角也没有扩散。就是"这个阴影效果一般啊"的来源 |
| 自绘 1px 描边（底色矩形 + `CustomPaddedLayout(1,1,1,1)`） | 自绘描边会把界面整体压深一档（顶栏槽位 51px vs 栏体 46px，那 5px 空隙会从底色 `#EFF0F3` 变成描边色 `#D5D8DD`，形成一条横贯窗口的灰带）。用户明确否过 |
| `DwmExtendFrameIntoClientArea(1,1,1,1)` | 客户区被内缩 7px（420x740 窗口 → 406x726 客户区），内容跟着缩水 |
| `WS_THICKFRAME` 但不覆写 `WM_NCCALCSIZE` | 同上：客户区被真实 NC 边框吃掉 7px |

三种替代方案都能"看见阴影"，但只有 `WS_THICKFRAME + WM_NCCALCSIZE=0` 同时满足
**四边都有柔和投影 + 客户区铺满**。

## 验收（必须看窗口样式和像素，不能只看代码）

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\wininfo.ps1 -TargetPid <gui pid>
```

期望值：

- `GWL_STYLE` 里 `WS_THICKFRAME=True`、`WS_CAPTION=False`（RemoteNet 实测 `0x960E0000`）；
- **客户区 == 窗口矩形**（如 418x739 == 418x739），NC 边框 0；
- 类样式（`GCL_STYLE`）里**没有** `0x20000`（`CS_DROPSHADOW` 已退役）；
- `DWMWA_WINDOW_CORNER_PREFERENCE` 读回 `= 2`（圆角生效的硬证据）。

投影本身要采样像素：`scripts\shadow_probe.ps1`（白底窗口 + 窗外 16px 逐像素）。
**屏幕锁着时截图会拿到锁屏壁纸**——像素验证必须在解锁状态下做。

## 想验证新的窗口样式？用实验台，别改生产代码

`scripts/shadowlab/` 是一个独立的 Windows 窗口实验台（Go + 纯 Win32，无 Fyne 依赖）：

```bash
cd scripts/shadowlab && go build -o shadowlab.exe .
./shadowlab.exe -list          # 看有哪些窗口样式变体
./shadowlab.exe -v 2           # 跑第 2 个变体：贴白底背景、截图、打印像素报告
./shadowlab.exe -v 2 -hold     # 不自动关窗，肉眼观察
```

它会：建一个全屏白底窗口（当作"浅色桌面"）→ 在它上面按变体参数建窗口 →
`SetForegroundWindow` → 截图（含窗外边距）→ 打印窗口/客户区尺寸、`GWL_STYLE`、
四边向外 16px 的像素、四角放大图。一次跑多个变体就能横向对比（RemoteNet 选方案时跑了 6 个）。

**踩过的坑**：截图前必须 `SetForegroundWindow` + 泵一会儿消息，否则抓到的是**壁纸**
（窗口没上屏），会得出"没变化"的错误结论；判断方式是截图里找窗口外框像素，
找不到就说明窗口没真的显示出来。
