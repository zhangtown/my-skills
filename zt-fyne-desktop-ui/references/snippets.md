# 可直接复制的代码片段

每条都标注了落地状态：**已落地**（在仓库里，照抄即可）、**建议**（值已定，动到相关控件时一并加）。

## 1. 按钮悬停「叠色不换色」— 已落地（commit `3132ab1`）

Fyne 的悬停是**在底色上 blend 一个背景色**：`blendColor` 在覆盖色 alpha = `0xFF` 时会退化成
"整块替换"，于是浅灰把红 CTA 罩成灰、白字对比度从 6.75:1 掉到 1.2:1——看起来像按钮失效。
修法：给半透明黑，让它在任意底色上都只是"加深"。

```go
// cmd/gui/theme.go
// colBtnHover 重要按钮 hover 的叠加色：黑 14%（半透明 → 叠在原底色上＝底色加深）。
colBtnHover = color.NRGBA{0x00, 0x00, 0x00, 0x24}

// 颜色映射里：
case widget.ButtonHoverDeepColorName:      // 或项目里的等价分支
    return colBtnHover // 重要按钮（红 CTA）悬停：底色加深，不再变灰
```

```go
// vendor/fyne.io/fyne/v2/widget/button.go（vendored 补丁）
const ButtonHoverDeepColorName fyne.ThemeColorName = "remotenetButtonHoverDeep"
// ButtonRenderer 里：hover 时把 backgroundBlend 指向这个令牌
backgroundBlend = ButtonHoverDeepColorName
```

> 同一个公式适用于任何"要变深"的控件（列表行 hover、菜单项 hover）：**加深就用半透明黑叠色，
> 不要用不透明浅灰覆盖**——覆盖只在"白底 + 深字"时才是加深，遇到深色面板就变成变浅/发灰。

## 2. 按压 / 焦点 —— 建议（未落地）

沿用同一套令牌，只是叠得更深；不要为每个状态各配一种颜色：

```go
// theme.go
colBtnPress = color.NRGBA{0x00, 0x00, 0x00, 0x3D} // 黑 24%，按压：比悬停再深一档
colBtnFocus = color.NRGBA{0x00, 0x00, 0x00, 0x2E} // 黑 18%，键盘焦点
```

```go
// vendor/fyne.io/fyne/v2/widget/button.go —— 找到悬停令牌的绑定处，按压/焦点同法改绑
//   按压分支 → ButtonPressedDeepColorName（映射到 colBtnPress）
//   焦点分支 → ButtonFocusDeepColorName（映射到 colBtnFocus）
```

- 焦点态**只在键盘 Tab 到达时**出现；鼠标点击不要留焦点底色（否则点一下就"脏"一块）
- 三个值都是"黑 X%"，这样白卡与深色面板上都成立

## 3. 禁用态 —— 建议（值已定）

禁用要同时满足"更淡"和"能读清"：

```go
// theme.go（次级按钮）
// 可用：#EBEDF0 底 + 深灰字；禁用：#F7F8FA 底 + #6B7280 字（对比度 4.6:1）
colBtnDisabledText = color.NRGBA{0x6B, 0x72, 0x80, 0xFF} // #6B7280
colBtnDisabledBg   = color.NRGBA{0xF7, 0xF8, 0xFA, 0xFF} // #F7F8FA
```

> 校验口径：白卡上正文对比度 ≥ 4.5:1；"禁用"和"可用"的底色差要肉眼可辨（本项目 #EBEDF0 vs #F7F8FA 刚好够）。

## 4. 勾选/单选的焦点大圆刻意透明 — 已落地（vendored 改动，勿"修复"）

```go
// vendor/fyne.io/fyne/v2/widget/check.go:175
focusIndicator := canvas.NewCircle(th.Color(theme.ColorNameBackground, v))
```

Fyne 默认用 `ColorNamePrimary` 画一个实心大圆，在浅灰底上像一块脏斑。项目改成背景色 → 视觉上不出现，
键盘 Tab 仍会用文字/描边给出反馈。**不要把它改回 Primary**。

## 5. 无边框窗口的系统投影 — 已落地（commit `8ab3cbe`）

```c
// vendor/github.com/go-gl/glfw/v3.4/glfw/glfw/src/win32_window.c
// 补一个 WS_THICKFRAME，让 DWM 认为这是"有边框窗口"从而投下四周对称的系统阴影
style |= WS_THICKFRAME;
// 再由 windowProc 的 WM_NCCALCSIZE 返回 0 把 NC 边框吃掉（客户区 == 窗口矩形）
```

- **旧方案 CS_DROPSHADOW 已废弃**：实测只有右下 5px 硬边、左边上边完全没有投影，不对称
- `WS_THICKFRAME` 只能在 `createNativeWindow()` 那处补；`getWindowStyle()` 的返回值被二十多处引用，
  加在那里会连带影响布局判断
- 改完 C 代码**必须**跑一次：

```bash
cd /d/ProgramData/projects/ZtRemoteNet
./tools/glfwmarker            # 看哈希是否落后
./tools/glfwmarker -write     # 改过 C 就写回常量，否则 cgo 不会重编（Go 只按文件内容哈希打包）
```

## 6. 设计约束测试骨架（新增/改样式时补一条）

```go
// cmd/gui/theme_constraints_test.go
func TestControlColorsComeFromTokens(t *testing.T) {
    // 断言：控件用的颜色等于 theme.go 的令牌值，而不是新写的字面量
    if got := colorOfPrimaryButton(); got != colAccent {
        t.Fatalf("主按钮底色走了字面量：%v，应为 colAccent", got)
    }
}

func TestCardGapComesFromThemePadding(t *testing.T) {
    // 断言：卡片缝 = theme.Padding()，没有在 VBox 里插占位对象
    if gap := cardGapPx(); gap != theme.Padding() {
        t.Fatalf("卡片缝 %d，应为 theme.Padding()=%d", gap, theme.Padding())
    }
}
```

## 7. 像素级验证脚本（改完视觉必须量一次）

```powershell
# 横向色段（定位控件/卡片左右边界与颜色）
powershell -NoProfile -ExecutionPolicy Bypass -File "$env:USERPROFILE\.pi\agent\skills\zt-fyne-desktop-ui\scripts\hscan.ps1"
# 卡片缝（深色卡底 → 背景 → 白卡顶，正列查找）
... \scripts\gap_analyze.ps1
# 窗口投影（白底上把窗口挪位，量窗外 16px）
... \scripts\shadow_probe.ps1
# 窗口样式/客户区（验证无边框 + 投影补丁真的生效）
... \scripts\wininfo.ps1
```

- 采样要**沿同一列/行取多段**再下结论：单点采样会把别的窗口、抗锯齿边缘误判成"样式变了"
- PowerShell 里给自定义函数传负数位置参会当成参数名 → 改传 `'L'/'R'/'T'/'B'` 方向字串
