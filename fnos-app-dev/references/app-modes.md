# 两种应用形态：内嵌（无端口）与带端口

飞牛应用都能在桌面点开，但"点开后它是怎么被打开的"有两种完全不同的机制。选错了会在
**鉴权、端口、局域网暴露面**上多绕很多弯。

## 一、对比

| | 内嵌（走统一网关） | 带端口（独立服务） |
|---|---|---|
| manifest | 不写 `service_port`/`checkport` | `service_port = <port>` + `checkport = true` |
| `app/ui/config` 关键字段 | `gatewayPrefix` + `gatewaySocket` | `protocol` + `port` + `url` |
| 通信方式 | 应用监听 **unix socket**，网关反代 | 应用监听 `0.0.0.0:<port>` |
| 访问路径 | `https://<NAS域名>/app/<appname>/` | 由桌面用 iframe 打开 `http://<NAS>:<port>/` |
| 鉴权 | **由飞牛登录态兜底**；应用可完全不鉴权 | 局域网任何设备都能直连 → **必须自己加密码** |
| 跨设备访问 | 走 NAS 域名/远程访问即可 | 需自己开端口、配反代与证书 |
| 适合 | 有网页界面的自用工具、笔记、面板 | 同步器、下载器、媒体服务、需要被其它程序调用的服务 |

**默认建议内嵌**：少一个端口要管、少一套密码要记、天然复用飞牛的登录与远程访问。只有当
"别的设备/别的程序要直接连它"时才选带端口。

## 二、内嵌模式（`app/ui/config` + socket）

`app/ui/config` 完整示例（这是真实跑通的配置）：

```json
{
  ".url": {
    "zt-note.main": {
      "title": "云栖笔记",
      "icon": "images/icon_{0}.png",
      "type": "iframe",
      "protocol": "",
      "gatewayPrefix": "/app/zt-note",
      "gatewaySocket": "app.sock",
      "url": "/app/zt-note/",
      "allUsers": true,
      "control": { "accessPerm": "readonly" }
    }
  }
}
```

| 字段 | 含义 | 注意 |
|---|---|---|
| `.url` 的键 | 桌面入口 id | **必须等于 manifest 的 `desktop_applaunchname`** |
| `title` | 桌面/应用中心显示名 | 与 manifest `display_name` 保持一致 |
| `icon` | 图标模板，`{0}` 会被替换成尺寸（64/256） | 需要 `app/ui/images/icon_64.png` 与 `icon_256.png` |
| `type` | `iframe`（内嵌网页） | 桌面把它嵌进窗口 |
| `gatewayPrefix` | 网关对外暴露的路径前缀 | **一般等于 `/app/<appname>`**；改这里等于改所有对外 URL |
| `gatewaySocket` | socket 文件名（相对应用目录） | 与程序里实际创建的 socket 文件名一致 |
| `url` | 桌面打开时 iframe 的起始 URL | 通常是 `/app/<appname>/` |
| `allUsers` | 是否所有 NAS 账号可见 | `true` 全可见；`false` 只有管理员 |
| `control.accessPerm` | 访问权限声明 | `readonly` 表示只需要读（不改系统状态） |

### 应用侧要满足的约定

1. **监听 unix socket，不监听 TCP**：`-sock $TRIM_APPDEST/app.sock` 这类参数即可（Go 的
   `http.Server` + `net.Listen("unix", path)` 即可）。
2. **socket 建好后 `chmod 666`**：网关以另一个用户身份连接，权限不够会表现为"桌面点开一片空白"。
3. **启动脚本必须等到 socket 出现再返回**，否则网关还没注册就被判断成启动失败：
   ```sh
   i=0; while [ ! -S "$SOCKET_PATH" ] && [ "$i" -lt 50 ]; do i=$((i+1)); sleep 0.2; done
   [ -S "$SOCKET_PATH" ] || { log_msg "ERROR: socket not created"; exit 1; }
   chmod 666 "$SOCKET_PATH"
   ```
4. **所有静态资源用挂在 prefix 下的相对路径**：页面里写 `./static/index-xxx.js` 而不是 `/static/...`，
   否则换个 `gatewayPrefix` 就全 404。SPA 还要给未知路径回落到 `index.html`（但 `/api/*` 必须回落成 404，
   否则前端会把 HTML 当成 JSON 解析，报一堆莫名其妙的错）。
5. **忘记 `gatewayPrefix` 也能自测**：本机 `curl --unix-socket <sock> http://localhost/api/health` 是
   最快验证方式，不需要经过网关。

## 三、带端口模式

`app/ui/config` 完整示例：

```json
{
  ".url": {
    "quark-butler.Application": {
      "title": "夸克管家",
      "desc": "云盘 → NAS 本地自动补齐",
      "icon": "images/icon_{0}.png",
      "type": "iframe",
      "protocol": "http",
      "port": 15100,
      "url": "/",
      "allUsers": false,
      "width": 1280,
      "height": 860
    }
  }
}
```

- `protocol` + `port` + `url` 决定 iframe 打开什么地址；`width`/`height` 是窗口初始尺寸。
- `allUsers: false` 常用于"只有管理员能用"的服务（下载器/管家类）。
- **必须在应用侧做鉴权**：端口一旦监听 `0.0.0.0`，局域网任何设备都能直连。常见做法是
  访问密码（空密码 = 局域网友好），密码来源按优先级：应用设置 > 历史环境变量文件 > 空。
- 端口从哪来：可以是向导里填的（`wizard_app_port`），也可以写死。**写死更省事**，但要与
  manifest 的 `service_port`、`app/ui/config` 的 `port` 三处一致——不一致的表现是
  "桌面点开是空白/连接被拒"。

## 四、致命坑：`wizard/` 会让非交互安装直接失败

向导（`wizard/install` 等）声明的字段在**应用中心交互安装**时由弹框注入成环境变量，比如：

```json
[{ "stepTitle": "基础设置", "items": [
  { "type": "text", "field": "wizard_app_port", "label": "服务端口", "initValue": "15100",
    "rules": [ { "required": true, "message": "请输入端口" } ] },
  { "type": "password", "field": "wizard_admin_password", "label": "访问密码" }
]}]
```

而 `appcenter-cli install-local -d <解包目录> -v <卷>` 是**非交互**的，没有地方提供这些值，
于是安装阶段直接报错：

```
[Info]Application [quark-butler] uninstall success
[Error]Something wrong with environment variables.
```

**它是先卸载再失败**：应用从应用中心消失、服务停摆，直到你手工装回去。而且这个错误退出码
可能是 0，`set -e` 的脚本不会中止，容易以为成功了。

### 三种处理方式

1. **不需要用户输入就不要放 `wizard/`**（推荐）：把端口等写死在 `app/ui/config` 与 `cmd/main` 的默认值里。
   想要"少数人改"，让应用自己在设置页面里写进数据目录即可。
2. **必须用向导**：那就只能走应用中心 UI 安装/升级，别用 `install-local` 自动化（或者安装时
   自己把向导变量当成环境变量传进去，但这条没在真实环境验证过，风险自负）。
3. **折中**：向导文件移出包目录，**模板留档**在同级 `packaging/fnos/<app>-wizard/`，并在这个
   模板目录里写一段 README 说明"为什么移出去、怎么临时加回来"——下次想改向导不至于重新发明。

验证包里的向导确实移干净了：

```bash
tar tzf deploy/fnos-app/<app>.fpk | grep -c wizard    # 期望 0
```
