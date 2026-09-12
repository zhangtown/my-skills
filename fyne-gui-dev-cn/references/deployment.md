# 编译、打包与分发

## 目录

- [1. 编译标签 (Build Tags)](#1-编译标签-build-tags)
- [2. 交叉编译](#2-交叉编译)
- [3. 桌面打包](#3-桌面打包)
- [4. 移动端打包](#4-移动端打包)
- [5. Web 打包](#5-web-打包)
- [6. 应用商店分发](#6-应用商店分发)

---

## 1. 编译标签 (Build Tags)

Fyne 提供多个编译标签控制行为和驱动选择：

| 标签 | 说明 |
|------|------|
| `debug` | 显示调试信息，包括可视化布局边界辅助理解布局 |
| `flatpak` | Linux Flatpak 沙盒优化 |
| `gles` | 强制使用嵌入式 OpenGL (GLES)，通常由目标设备自动控制 |
| `hints` | 显示开发者优化建议，如不遵循 Material Design 会 log 警告 |
| `mobile` | 在桌面端模拟移动端窗口，方便预览移动端效果 |
| `no_animations` | 禁用内置组件的非必要动画 |
| `no_emoji` | 不嵌入 emoji 字体，减小二进制体积 |
| `no_metadata` | 禁用 FyneApp.toml 元数据运行时查找（release 构建时始终禁用） |
| `no_native_menus` | macOS 下不使用原生菜单，菜单显示在应用窗口内（用于模拟 Windows/Linux 行为） |
| `wayland` | Linux/BSD 下使用 Wayland 窗口协议代替 X11 |

使用方式：

```bash
go run -tags mobile main.go              # 桌面端模拟移动端
go run -tags "hints,debug" main.go       # 同时使用多个 tag
go test -tags ci ./...                   # CI 环境测试
```

---

## 2. 交叉编译

Fyne 使用 CGo 进行图形渲染，交叉编译需要目标平台的 C 编译器。

### 2.1 从开发机直接编译

需要设置 `CGO_ENABLED=1` 和正确的 CC 编译器：

| 目标 GOOS | CC 编译器 | 获取方式 |
|-----------|-----------|----------|
| `darwin` | `o32-clang` | [osxcross](https://github.com/tpoechtrager/osxcross)（需 macOS SDK） |
| `windows` | `x86_64-w64-mingw64-gcc` | mingw64（macOS: `brew install mingw-w64`） |
| `linux` | `gcc` 或 `x86_64-linux-musl-gcc` | musl-cross（macOS: `brew install musl-cross`），需安装 X11/mesa 头文件 |

### 2.2 使用 fyne-cross（推荐）

`fyne-cross` 通过 Docker 镜像封装了所有交叉编译环境，一条命令即可完成：

```bash
# 安装
go install github.com/fyne-io/fyne-cross@latest

# 编译各平台
fyne-cross linux
fyne-cross windows -arch=*
fyne-cross darwin
fyne-cross android -arch=arm64
fyne-cross ios           # 仅 macOS 宿主机
fyne-cross freebsd -arch=amd64

# 指定输出名和子包
fyne-cross linux -output myapp ./cmd/myapp
```

支持的平台：darwin(amd64/386)、linux(amd64/386/arm64/arm)、windows(amd64/386)、android(amd64/386/arm64/arm)、ios、freebsd(amd64/arm64)

---

## 3. 桌面打包

使用 `fyne` CLI 工具自动处理图标转换、元数据嵌入和平台特定格式：

```bash
# 安装 CLI 工具
go install fyne.io/tools/cmd/fyne@latest

# macOS → .app bundle
fyne package -os darwin -icon myapp.png

# Linux → .tar.gz（包含 usr/local/ 目录结构）
fyne package -os linux -icon myapp.png

# Windows → .exe（嵌入图标和元数据）
fyne package -os windows -icon myapp.png

# Release 模式（去除调试符号，减小体积）
fyne package -os windows -icon myapp.png -release

# 直接安装到本机系统
fyne install -icon myapp.png
```

所有命令支持默认图标文件名 `Icon.png`，放置于项目根目录可省略 `-icon` 参数。

### 3.1 FyneApp.toml 配置（v2.1+）

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

有了 `FyneApp.toml` 后 `fyne package` 可省略许多参数。

---

## 4. 移动端打包

Fyne 代码可直接编译为 Android/iOS 应用，但需要额外的 SDK 和工具：

**环境要求：**
- Android：Android SDK + NDK，`adb` 在 PATH 中
- iOS：macOS + Xcode + Command Line Tools

**打包命令：**

```bash
# Android (.apk)
fyne package -os android -app-id com.example.myapp -icon mobileIcon.png

# iOS (.app)
fyne package -os ios -app-id com.example.myapp -icon mobileIcon.png

# iOS 模拟器
fyne package -os iossimulator -app-id com.example.myapp -icon mobileIcon.png
```

**安装命令：**

```bash
# Android 安装到设备
adb install myapp.apk

# iOS 安装到模拟器
xcrun simctl install booted myapp.app
```

iOS 真机安装通过 Xcode → Window → Devices and Simulators → 拖入 `.app`。

---

## 5. Web 打包

Fyne 应用也可通过 WebAssembly 在浏览器中运行：

```bash
# 本地开发测试
fyne serve                    # 启动 http://localhost:8080

# 打包为 Web 文件
fyne package -os web          # 生成 wasm 及相关文件
```

**已知限制 (v2.5.0)：**
- 文件打开/保存对话框暂不支持
- Documents 存储暂不支持

在线演示：[demo.fyne.io](https://demo.fyne.io/)

---

## 6. 应用商店分发

`fyne release` 命令处理打包后的签名和商店准备步骤。

### 6.1 macOS App Store

前提条件：macOS + Xcode、Apple Developer 账号、Mac App Store 证书、Apple Transporter

```bash
fyne release -appID com.example.myapp -appVersion 1.0 -appBuild 1 -category games
# 然后将 .pkg 拖入 Transporter，在 AppStore Connect 提交审核
```

### 6.2 iOS App Store

前提条件：macOS + Xcode、Apple Developer 账号、iOS 分发证书、Apple Transporter

```bash
fyne release -os ios -appID com.example.myapp -appVersion 1.0 -appBuild 1
# 将 .ipa 拖入 Transporter，在 AppStore Connect 提交审核
```

### 6.3 Google Play Store (Android)

前提条件：Google Play Console 账号、分发 keystore

```bash
fyne release -os android -appID com.example.myapp -appVersion 1.0 -appBuild 1
# 关闭 Google Play 的 "Play app signing"，手动上传 .apk
```
