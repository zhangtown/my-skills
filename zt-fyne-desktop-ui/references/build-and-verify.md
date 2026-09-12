# 构建、发布、验证

## 三条构建路径（按目的选）

```bash
cd <客户端仓库>
export PATH="/c/Users/ELEX-ZT/go-sdk/go/bin:$PWD/.toolchain/root/ucrt64/bin:$PATH"
```

1. **只要看界面效果（开发中最常用）**
   ```bash
   go build -ldflags "-H windowsgui" -o dist/RemoteNet-Portable/gui.new.exe ./cmd/gui
   powershell -NoProfile -ExecutionPolicy Bypass -File "$TEMP/swap_gui.ps1"
   ```
   先写成 `gui.new.exe`（正在跑的 `gui.exe` 有文件锁，直接覆写会失败），再由脚本换名重启。

2. **正式打包**：`build.bat`。产物 `dist\RemoteNet-Portable\gui.exe`（+ zip、router、nas）。
   它会停掉 `reverse.exe`、给 `gui.exe` 写 exe 图标、把 `remotenet-gui.json` 运行配置
   暂存后还原、最后清掉 `dist\` 里的散装产物。**GUI 构建失败会把完整日志打进
   `dist\gui-build.log` 并暂停**，所以"build 没出 gui.exe"时第一件事是看那份日志，
   而不是反复重跑。

3. **只想跑测试**：`go test ./cmd/gui/`（设计约束的可执行版本，见 layout-and-interaction）。

## 三个必踩的坑

### 1. 改了 vendored glfw 的 C 代码，不重编

Go 的构建缓存按**文件内容**哈希（不是 mtime），只覆盖 `.go` 文件；glfw 的 C 源码是通过
`c_glfw_windows.go` 里的 `#include "glfw/src/*.c"` 进来的，所以**改 `.c` 不会触发重编**，
`touch *.go` 也没用。upstream 的解法是在 `glfw_tree_rebuild.go` 里维护一个
`const upstreamTreeSHA` 常量（C 树一变，常量变，包构建键就变）。

因为 `go mod vendor` 把 upstream 的 `scripts/` 裁掉了，本仓库自己写了一个：

```bash
go run ./tools/glfwmarker -write   # 重新计算 C 树哈希并写回常量（-c 只检查，exit 1 表示已过期）
```

`build.bat` 在编 GUI 之前会自动跑一次。手工单编时**必须自己跑**，否则你会得到
"代码改了、行为没变"的假象，并在运行时用 `GCL_STYLE` 之类的探测得出错误结论。

### 2. `go build ... | head` 会把退出码吃掉

任何把 build 输出接进管道的写法都会让 `$?` 变成 `head` 的退出码，于是**失败也会打 "BUILD-OK"**。
要么直接跑（不接管道），要么 `set -o pipefail`。

### 3. 硬杀 GUI 会把系统代理留在"开着"的状态

客户端会把系统代理设成 `127.0.0.1:1080`（`internal/sysproxy`），
清理只在正常退出（`Clear()`）时发生。`taskkill /F` 之后浏览器会连不上网——
所以换 exe 的脚本要尽量避免硬杀，硬杀之后要么重启 GUI 让它自己清，要么手工恢复直连。

## 验证改动真的生效

**代码写完 ≠ 生效**。这三类证据按可用性排序：

### 窗口级（PowerShell + P/Invoke，最可靠）

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\wininfo.ps1 -TargetPid <pid>
```

打印窗口矩形、客户区矩形、`GWL_STYLE`、`GWL_EXSTYLE`、`GCL_STYLE`（类样式）。
无边框窗口要看的期望值见 `windows-chrome.md`。

### 像素级（间距、投影、颜色）

| 脚本 | 用途 |
|---|---|
| `scripts/gap_analyze.ps1` | 截窗口图，按某一列扫"深色卡底 → 背景缝 → 白卡顶"，报出实际缝宽 |
| `scripts/shadow_probe.ps1` | 建一个浅色背景窗口当"桌面"，把目标窗口摆上去，打印四边向外 16px 的像素 |
| `scripts/hscan.ps1` | 打印指定 y 行的横向色段（用来找卡片左右边界） |

要点：

- 像素验证**必须在解锁状态下做**：屏幕锁着时截图拿到的是锁屏壁纸，会得出"什么都没变"的结论。
- 采样点要避开卡片中央内容：贴边采样（如 `x = 图像宽 − 18`）比取"整列最后一个深色像素"稳。
- **PowerShell 的两个坑**：`$Pid` / `$PID` 是只读自动变量（参数名用 `-TargetPid` 之类）；
  给自定义函数传负数位置参数会被当成参数名解析（`-1` → `Cannot convert value "-1-1" to Int32`），
  所以位置参数改传方向字串 `'L'/'R'/'T'/'B'`。

### 行为级（测试）

`go test ./cmd/gui/`。改 vendor 里的 Fyne 渲染代码（菜单/按钮）之后也要跑。

## 提交

用 conventional commits（`feat(gui):` / `fix(glfw):` / `build(glfw):` / `refactor:` …），
正文写清**为什么**，因为下一个人（或下一次会话）只能从 commit message 里知道某个数字
是因为哪条反馈定下来的。示例：

```
fix(glfw): 无边框窗口改用 DWM 系统投影（WS_THICKFRAME + WM_NCCALCSIZE）

CS_DROPSHADOW 只有右下 5px 硬边，左边上边完全没有投影；
自绘描边会把界面整体压深一档（用户否过）。
改成补 WS_THICKFRAME + WM_NCCALCSIZE 返回 0，让 DWM 按有框窗口画系统投影。
```

运行配置 `remotenet-gui.json`、证书、本地随手编出来的 `gui.exe` 都不要提交
（`.gitignore` 已排除 `/gui.exe`；正式产物在 `dist/`）。

## 改进本技能时怎么回归（评测）

本技能自带 7 个回归场景；工作区（不进仓库）：
`C:\Users\ELEX-ZT\.skills-manager\zt-fyne-desktop-ui-workspace\`

- 场景定义：技能内 `evals/evals.json`（`id` / `name` / `prompt` / `expected_output`）。
- 评分断言：`<工作区>\iteration-N\checks.json`（按 eval id 分组，每条一个正则）。
- 跑一次：给每个 `iteration-N/eval-*/(with_skill|without_skill)` 派一个 `worker` 子代理，
  两部分给**同一段用户原话**，只差“给不给技能目录”；提示里写明“只读仓库、只把方案写到该 run 的
  `outputs/plan.md`、不改仓库不跑构建”。
- 打分：`python <工作区>\bench.py iteration-N` → 每个 run 出 `grading.json`，
  目录级出 `benchmark.json` / `benchmark.md`。
- 看对照页（本地网页，含逐条证据）：
  `python C:\Users\ELEX-ZT\.skills-manager\skills\skill-creator\eval-viewer\generate_review.py <工作区根> --benchmark iteration-N/benchmark.json --skill-name zt-fyne-desktop-ui --port 3117`
- **断言必须有区分度**：两侧都满分说明断言在考"仓库里摆着的注释"，不是在考技能；
  把断言换成需要跨文件推理 + 无技能时容易漏的点（例如"改 vendored C 后要跑 `glfwmarker -write`"、
  "卡片行距来自 `theme.Padding()`"）。
- **断言必须可客观判断**：能用正则/计数/单位验证（提到某个常量、给出某个数值、是否引入字面量），
  不要写“写得好不好”这种判断。
- **负向断言只能考“行为”，不能考“字面”**：iteration-1~4 里曾有一条
  「没有引入新的颜色字面量（color.NRGBA{...}）」→ 其 pattern 就是 `color\.NRGBA\{`，
  结果它惩罚的不是“新造颜色”，而是**提到** `color.NRGBA{`：
  一边引用现有 `colBtnHover = color.NRGBA{0x00,0x00,0x00,0x24}` 讲根因、
  或者写“全仓 `color.NRGBA{` 只出现在 theme.go 里”，都会被判失败。
  实测后果：iteration-4 首算 with_skill 21/24 vs without 23/24（**-8.3pt**），
  逐条查才发现 3 个“失败”全是这一条导致的假阴性。
  → 已换成正向断言「颜色写进 theme.go 令牌区（给出 token 名或令牌区位置）」：
  `theme\.go[\s\S]{0,400}(令牌|col[A-Z])|(令牌|col[A-Z][A-Za-z]*)[\s\S]{0,400}theme\.go`，
  四条样本都验证过（令牌区新增 ✓ / 引用现有令牌 ✓ / UI 里写死字面量 ✗ / 只说 theme.go 不说颜色 ✗）。
  教训：负向断言写好后必须拿“一个好例子 + 一个坏例子”跑一遍，
  只在真实产出上看到“有人失败”就下结论，很容易把“提到”当成“干下”。
- **n 很小，别吹**：一个场景一侧只跑 1 个 run，报告里只写“共同场景上的差值”（如 +13.3pt，
  基于 2 个场景 15 条断言），不要写成“技能普遍提升 X%”。
- 两侧分数一样时先查断言：多半是断言在考仓库里现成的注释，不是在考技能。
- **派活时必须写两条执行纪律**（iteration-4 实测：6 个 run 里 4 个没交付）：
  ① “先用 rg/grep 精准取数，最多 8 分钟，然后**立刻把 plan.md 写出来**再回头补细节”；
  ② “**不要用任何上下文压缩工具**”——子代理一旦调 compress 且摘要被截断，就会反复重查事实、
  耗尽预算，最后什么都没写（4 个挂掉的 run 全部死在“summary got truncated，我重新核一遍”）。
  写文件就是最好的省上下文方式。
