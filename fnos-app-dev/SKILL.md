---
name: fnos-app-dev
version: "1.1.0"
description: 把服务或工具做成飞牛 fnOS 应用（fpk 包）并装进应用中心：manifest 与 cmd 生命周期脚本、无端口内嵌应用（走飞牛统一网关 + unix socket）、带端口的桌面应用、图标设计（飞牛官方浅底玻璃风格 + Go 像素渲染一键生成多尺寸）、PIN 与令牌鉴权（含移动端 WebView 第三方 Cookie 被拦的坑）、多用户数据隔离、pack.sh/install.sh 一键打包升级，以及「装了没生效 / 图标不刷新 / 版本号不登记 / PIN 一直重输」的排查。当用户要做飞牛应用、写 fpk 包、给飞牛应用做图标与桌面入口、把现有服务搬进飞牛 NAS 应用中心、或遇到飞牛应用的安装升级鉴权问题时使用。即使对方没说「飞牛」「fnOS」「fpk」，只要是在飞牛系统上做可安装的应用包、走应用中心安装与升级，也应该加载本技能。产出一律用中文（含注释与用户可见文案）。若任务其实是「制作/评测/迭代一个 agent 技能本身」，那是 skills-dev 技能的事，不要用本技能。
---

# 飞牛 fnOS 应用开发

把服务做成飞牛应用，成功的判据只有一条：**用户在应用中心装上、从桌面点开就能用，而且升级之后看到的确实是新版本**。
大部分坑都出在最后半句——包做出来容易，让升级真的生效、让图标和名字在每一层都一致，才是花时间的地方。

> 本文默认你已经有一个能跑的本地程序（Go / Node / Python / 静态站都行）。飞牛应用的本质是
> **一个目录树 + 一份 manifest + 一组生命周期脚本**，用 `fnpack` 打成 `.fpk`，由应用中心安装到
> `/vol1/@appcenter/<app>`，数据放 `/vol1/@appdata/<app>`。

**怎么用这份技能**：先回答下面三个问题（一）→ 按七步把包目录填出来（二）→ 对照八个高频坑避开返工（三）→
卡住了再从参考资料索引（四）里挑对应文件深入。文中凡是**实测得到的数字/字段/命令**都尽量原样给出，
凭分析推断而未在真机上验证的会明确写「未实测」——引用之前先看这个标注，别把推断当结论抄进线上脚本。

**和 `skills-dev` 的分工**：本技能是「做飞牛应用」；如果你要做的其实是**制作或评测一个 agent 技能**
（写 SKILL.md、跑评测集、优化技能描述触发率），那是 `skills-dev` 技能，加载它。两者都会碰「打包脚本」
和「图标生成器」，但目的不同：这里是把产品装进 NAS，那边是把方法论固化成技能。

## 一、动手前先定三个问题

这三个决定会贯穿整个工程，先想清楚能省掉一轮返工。具体字段与取舍见 `references/app-modes.md`。

| 问题 | 选项 | 怎么选 |
|---|---|---|
| **应用形态** | 无端口内嵌（`gatewayPrefix` + `gatewaySocket`，走飞牛统一网关） | 有网页界面、想直接复用飞牛的登录态、不想让用户输密码/管端口 → 选它。**多数自用应用应该选这个** |
| | 带端口的独立应用（`service_port` + `checkport`） | 需要从局域网其它设备直接访问、或本身就是独立服务（同步/下载/媒体类） |
| **数据模型** | 每个飞牛账号一份（按 uid 隔离） | 多人各用各的笔记/文档/书签 → 选它。靠网关透传的用户身份区分 |
| | 全机共用一份 | 全局配置、任务队列、家庭共享库（如下载器、管家类） |
| **鉴权** | 完全交给网关（推荐起点） | 内嵌应用默认如此：用户在飞牛桌面已登录，网关带身份进来 |
| | 应用自建 PIN/密码 | 需要"打开应用再确认一次"、或带端口的应用要挡住局域网。**注意移动端 WebView 的 Cookie 坑**（见 `references/auth-and-users.md`） |

## 二、从零到装上：七步

每一步的产出都指向同一个包目录，最后一步才是打包。**别一上来就打 fpk**——先在本地把包目录填对。

1. **建包目录**（结构见 `references/package-anatomy.md`）
   ```
   packaging/fnos/<app>/          # 或 deploy/fnos-app/<app>/
   ├── manifest                   # 应用身份：名字/版本/端口/网关/介绍
   ├── ICON.PNG  ICON_256.PNG     # 应用中心与桌面图标
   ├── icon.png                   # 浏览器标签页图标（有网页界面时）
   ├── cmd/                       # 生命周期脚本：main + {install,config,upgrade,uninstall}_{init,callback}
   ├── config/{privilege,resource}
   ├── wizard/                    # 安装向导（**非交互安装会踩坑，见下**）
   └── app/                       # 真正装到 NAS 上的东西
       ├── bin/<可执行文件>        # 或 app/server/...（带端口模式）
       └── ui/{config,images/}     # 桌面入口定义 + 图标
   ```
2. **写 `cmd/main`**：这是飞牛调用的唯一入口，必须正确处理
   `start|stop|status|restart|install_init|install_callback|config_init|config_callback|upgrade_init|upgrade_callback|uninstall_init|uninstall_callback`，
   用 `$TRIM_APPDEST`（程序目录）、`$TRIM_PKGVAR`（数据目录）、`$TRIM_TEMP_LOGFILE`（给用户看的报错）。
   可抄现成的：`scripts/lifecycle-main.embedded.sh`（socket 模式）/ `scripts/lifecycle-main.port.sh`（端口模式）。
   **socket 模式必须等 socket 出现再退出**（网关要靠它注册），建完 `chmod 666`。
3. **写 `app/ui/config`**：定义桌面入口（title / icon / url / gatewayPrefix / gatewaySocket / allUsers）。
   这是"看起来装上了但桌面点不开"的头号原因——字段名和路径必须逐字对。
4. **做图标**：`tools/mkicon` 用 Go 直接画（`scripts/mkicon/main.go` 可改写），一次生成
   `ICON.PNG`(64) / `ICON_256.PNG`(256) / `app/ui/images/icon_{64,256}.png` / `icon.png`。
   **图标必须在编译之前生成**：如果程序用 `//go:embed icon.png` 供 favicon，生成顺序错了界面里永远是旧图标。
   设计风格、尺寸清单、每个出现位置见 `references/icons-and-branding.md`。
5. **写 `pack.sh`**：图标 → 前端构建（可选）→ 交叉编译（`CGO_ENABLED=0 GOOS=linux GOARCH=amd64`，
   `-ldflags="-s -w -X main.version=$VERSION"`）→ `fnpack build --directory <包目录>`。
   可直接改编 `scripts/pack.sh`。
6. **写 `install.sh`**：打包 → 上传 → 远端 `tar xzf` → `sudo appcenter-cli install-local -d <解包目录> -v <卷>` → 自检。
   可改编 `scripts/install.sh`（含 `MODE=socket|port` 两种自检）。连接信息放 `nas.env`（**不入仓库**）。
7. **验收**：本机逻辑测试 → 实机 `health` 版本号 → 图标 md5 逐字节对比 → 数据目录 mtime 不变 → 各层品牌一致。
   完整清单见 `references/pack-and-deploy.md` 末尾。

## 三、最容易翻车的八个点（每条都真实发生过）

1. **`appcenter-cli install-fpk` 对已安装的同名应用是空操作**——版本号更高也不换文件，只打印
   `Application [<app>] is installed.`。升级必须走 `install-local -d <解包目录> -v <卷>`（内部是
   停止 → 卸载 → 安装 → 启动）。这条不搞清，会出现"明明打包了、NAS 上还是旧的"。
2. **`wizard/` 里的向导项会让非交互安装直接失败**：向导声明的变量（如 `wizard_app_port`）在安装时由
   应用中心弹框注入，`install-local` 没法提供 → `[Error]Something wrong with environment variables.`，
   而且**它是先卸载再失败**，应用会从应用中心消失、服务停摆。要非交互安装就别放 `wizard/`（或把值
   在 `app/ui/config` 里写死），只在真正需要用户输入时才用向导。详见 `references/app-modes.md`。
3. **应用中心的版本号不读包里的 manifest**：手工部署（scp + 五步法）只换文件，应用中心仍显示旧版本号。
   想让版本号、图标、升级流程都对，必须走一次正规安装。
4. **图标 URL 不带版本参数**：`/app-center-static/serviceicon/<app>/ui/images/icon_{0}.png?size=256`
   是长缓存，换图标后用户（含手机 App 的 WebView）不会立刻看到。同理，**应用自己吐的静态资源也要
   主动声明缓存策略**（入口页 `no-cache`、带哈希的 JS/CSS 用 `immutable`），否则升级后用户还在跑旧界面。
   核对时用无痕窗口，别被缓存骗了。
5. **多层品牌要逐层核对**：应用 id、网关 prefix、display_name、桌面条目 title、页面 `<title>`、favicon、
   应用内首页标识……改一次名字要改七处。改名或换 logo 后按 `references/icons-and-branding.md` 的清单逐层查。
6. **移动端 WebView 会拦第三方 Cookie**：应用嵌在 iframe/WebView 里时，`Set-Cookie` 可能被丢，
   于是"PIN 输对了还是被要求重输"。令牌必须支持**三条通道**（Header / URL 参数 / Cookie），
   移动端走 URL 参数。详见 `references/auth-and-users.md`。
7. **卸载脚本里的"删数据"要真的删、开发期的"备份"要真的留**：`uninstall_callback` 里按向导选项
   决定是否 `rm -rf $TRIM_PKGVAR`。反向的坑是：`install-local` 的停止/卸载/安装**不会**动数据目录，
   所以升级前放心，但自己写部署脚本时别顺手 `rm -rf`。
8. **`sudo -n` 有白名单**：NAS 上能免密 sudo 的只有 `/usr/local/bin/appcenter-cli`、`cp`、`install` 这几个
   （**实测可用**；`ls` / `md5sum` / `cat` / `find` 不在内，一跑就失败）。把它们串进 `set -e` 的部署脚本会
   **中途中断、留下停着的应用**。要读应用数据就用自己的 socket API，要备份数据用 `sudo -n cp -a`。

## 四、参考资料索引

按"我卡在哪"取用，不必通读：

| 文件 | 什么时候看 |
|---|---|
| `references/package-anatomy.md` | 包目录里每个文件是干什么的、manifest 每个字段什么含义、生命周期脚本的调用协议与环境变量 |
| `references/app-modes.md` | 选内嵌还是带端口、两种 `app/ui/config` 的完整字段、wizard 向导的坑与替代做法 |
| `references/auth-and-users.md` | 做 PIN/密码/令牌、要按用户隔离数据、移动端登录不上 |
| `references/icons-and-branding.md` | 设计图标（飞牛官方风格）、生成多尺寸、核对品牌出现在哪七层 |
| `references/pack-and-deploy.md` | 打包与升级流程、版本号策略、回滚、部署后的验收清单 |
| `references/troubleshoot.md` | 症状 → 根因 → 验证：装了没生效、图标不刷新、版本不登记、PIN 循环、桌面点不开、静态资源 404 |
| `references/ui-pitfalls.md` | 应用界面自身的坑：右键菜单过长、移动端横向溢出、升级后用户看不到新界面 |
| `evals/RESULTS.md` | 本技能的一次真实对比实测：带技能 8/8 与 7/7，不带技能 6/8 与 5/7；漏掉的正是「图标要在 `go build` 前生成」「令牌要留 URL 参数通道」「`install-fpk` 是空操作」「fpk 嵌的是打包那刻的产物」 |

## 五、可复制脚本

`scripts/` 里是跑通过的模板，复制到新项目后改顶部几个变量即可：

| 文件 | 用途 |
|---|---|
| `scripts/pack.sh` | 图标 → 前端（可选）→ 交叉编译 → fnpack 打包 → 输出 `deploy/fnos-app/<app>.fpk` |
| `scripts/install.sh` | 打包 → 上传 → `install-local` → 自检（`health` 版本 / 图标 md5 / 数据 mtime），`MODE=socket\|port` |
| `scripts/nas.env.example` | NAS 连接信息模板（真实 `nas.env` 不入库） |
| `scripts/lifecycle-main.embedded.sh` | `cmd/main`：socket 模式（等 socket + chmod 666 + 优雅 stop） |
| `scripts/lifecycle-main.port.sh` | `cmd/main`：端口模式（PID 文件 + 端口环境变量 + 启动后探活） |
| `scripts/mkicon/main.go` | 图标生成器：SDF 逐像素 + 3 倍超采样，一次出四份尺寸，纯标准库 |

改完自己的项目后，**先在本机把 `pack.sh` 跑通再上传**——fpk 里的东西是打包那一刻的快照，
本地能看到的问题不要留到 NAS 上排查。

## 六、动手前五分钟：六个决定先写在纸上

这六件事每件都能省掉一轮返工，且都不需要写代码：

1. **应用 id**（小写、连字符，例：`my-notes`）——它同时是包目录名、`/vol1/@appcenter/<id>`、网关 prefix、
   图标接口路径 `/app-center-static/serviceicon/<id>/...` 的一部分。**定下来就别改**，改一次要动七处（见三·5）。
2. **显示名**（中文，例：`云栖笔记`）——与 id 无关，但要注意重名/商标风险，改名的代价比想象大。
3. **形态**：无端口内嵌（默认推荐）还是带端口（见一）。
4. **数据模型**：按 uid 隔离还是全机共享（见一）——它决定数据目录布局，后期改要迁移数据。
5. **端口**（选了带端口才需要）：**固定一个号写死**（例：`15100`），不要交给向导变量；
   同时避开 NAS 上已被占用的端口。
6. **图标先出**：先用一版能看的图标把流程跑通（尺寸清单见 `references/icons-and-branding.md`），
   不要等最后再画——图标参与编译（`//go:embed`），漏了会阻塞打包。

## 七、交付前自查清单

装到 NAS 之前逐项过一遍，任何一项答不上来都别发：

- [ ] `fnpack build` 成功，`deploy/fnos-app/<app>.fpk` 存在且**包内含图标与新版本号**（`tar tzf` 看顶层）
- [ ] 二进制里的版本号来自 manifest（`-X main.version=`），`/api/health` 返回的与 manifest 一致
- [ ] `cmd/main` 覆盖全部生命周期参数，`start` 之后 socket/PID 就绪才退出（socket 模式要等 socket 出现 + `chmod 666`）
- [ ] `app/ui/config` 的 title / icon / url / host / port 逐字对得上（这是「桌面点不开」的头号原因）
- [ ] 图标四份齐、尺寸正确、深浅底都能看清，且**生成在编译之前**
- [ ] 没有 `wizard/`（除非确实要用户在安装时输入）；要非交互安装就不能有
- [ ] `install.sh` 里没有 `sudo -n ls/md5sum/cat/find` 之类不在白名单的命令
- [ ] 升级后**数据目录 mtime 不变**（数据没被覆盖）、升级前有备份
- [ ] 卸载脚本删数据的行为与预期一致（要么真的删、要么明确保留）
- [ ] 各层品牌一致：应用中心名 / 桌面条目 / 页面标题 / favicon / 应用内标识
- [ ] 应用自身静态资源声明了缓存策略（入口页 `no-cache`，带哈希资源 `immutable`）
- [ ] `README` 写清数据在哪、怎么升级、怎么卸载、有什么安全边界
