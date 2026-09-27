# 包结构与生命周期协议

## 一、仓库里的包目录（打包前）

`fnpack build --directory <包目录>` 读的就是这个目录。把它放进项目的 `packaging/fnos/<app>/` 或
`deploy/fnos-app/<app>/` 都行，只要 `pack.sh` 指得到。

```
<包目录>/
├── manifest                   # 应用身份（纯文本 key=value，不是 JSON）
├── ICON.PNG                   # 应用中心/桌面图标，64×64
├── ICON_256.PNG               # 同上，256×256
├── icon.png                   # 浏览器标签页图标（内嵌应用必须与程序里的 favicon 一致）
├── cmd/                       # 生命周期脚本，全部必须可执行（chmod +x）
│   ├── main                   # 唯一入口：start/stop/status/...
│   ├── install_init           # 安装前
│   ├── install_callback       # 安装后
│   ├── config_init            # 设置页打开前
│   ├── config_callback        # 设置页保存后
│   ├── upgrade_init           # 升级前
│   ├── upgrade_callback       # 升级后
│   ├── uninstall_init         # 卸载前
│   └── uninstall_callback     # 卸载后（唯一会删数据的地方）
├── config/
│   ├── privilege              # 以谁的身份跑：{"defaults":{"run-as":"root"}}
│   └── resource               # 资源限制，{} 表示不限制
├── wizard/                    # 安装/设置向导（可选；**非交互安装会失败，见 app-modes.md**）
│   ├── install  config  upgrade  uninstall
└── app/                       # 真正落到 NAS 上的内容
    ├── bin/<binary>            # 可执行文件（内嵌模式）
    ├── server/<binary>         # 可执行文件（端口模式；两种都行，自己脚本里指对就行）
    ├── ui/config               # 桌面入口定义（JSON，字段见 app-modes.md）
    └── ui/images/icon_{64,256}.png
```

`fnpack` 会把它压成一个 `.fpk`；**fpk 本身就是 tar.gz**（不是 zip），所以可以
`tar tzf x.fpk` 看内容、`tar xzf` 直接解开来手工安装：

```
app.tgz                 # = app/ 目录的 tar 包
cmd/…  config/…  wizard/…  manifest  ICON.PNG  ICON_256.PNG
```

## 二、manifest 字段

两种写法都被接受：`key=value`（紧凑，zt-note 用）或 `key = value`（带空格，quark-butler 用）。
字符串字段值若含非 ASCII 或多行，用 `"""…"""` 包起来。

| 字段 | 作用 | 实例值 |
|---|---|---|
| `appname` | 应用 id（**全局唯一**，也是 URL 路径的一部分） | `zt-note` |
| `version` | 版本号，`x.y.z`；既写进包也建议写进二进制 | `0.6.6` |
| `display_name` | 应用中心/桌面显示的名字（中文可直接写） | `云栖笔记` |
| `desc` | 应用中心里的介绍，可含 HTML（`<p>` `<b>`） | — |
| `changelog` | 更新说明字符串，升级时展示；建议带历史（新在前） | `0.6.6：… 0.6.5：…` |
| `source` | 来源类别 | `thirdparty` |
| `platform` | 架构 | `x86` |
| `maintainer` / `maintainer_url` | 维护者与主页 | — |
| `distributor` / `distributor_url` | 分发者 | — |
| `os_min_version` | 最低系统版本 | `1.1.3100` |
| `desktop_uidir` | 桌面入口定义所在子目录（相对 `app/`） | `ui` |
| `desktop_applaunchname` | 桌面入口的 key（必须等于 `app/ui/config` 里 `.url` 的那个键） | `zt-note.main` / `quark-butler.Application` |
| `ctl_stop` | 卸载/停止时是否有 stop 逻辑 | `true` |
| `service_port` | 端口模式：应用监听的端口 | `15100` |
| `checkport` | 端口模式：安装时检查端口占用 | `true` |
| `disable_authorization_path` | 端口模式：关掉网关强制鉴权的路径 | `false` |

内嵌（无端口）模式**不写** `service_port`/`checkport`，改用 `app/ui/config` 里的
`gatewayPrefix`/`gatewaySocket` 声明自己挂在哪个路径上。

## 三、生命周期协议

框架调用 `cmd/main`，**第一个参数是动作名**：

| 动作 | 何时调用 | 该做什么 | 退出码 |
|---|---|---|---|
| `start` | 用户点开应用 / 系统启动 / 安装完成后 | 启动进程；内嵌模式要等 socket 出现再返回 | 0 成功，非 0 失败 |
| `stop` | 用户关闭 / 系统关机 / 升级与卸载前 | 先 TERM 再 KILL；清 PID 与 socket | 0 成功，非 0 失败 |
| `status` | 应用中心/桌面查询状态 | 不打印内容，只看退出码 | **0 运行中，3 未运行** |
| `restart` | 部分场景直接调 | = stop + start | 0/非 0 |
| `install_init` / `upgrade_init` / `uninstall_init` | 各阶段之前 | 备份、停旧服务、清理临时状态 | 0 |
| `install_callback` / `upgrade_callback` | 各阶段之后 | 起服务；升级后可做数据迁移 | 0 |
| `config_init` / `config_callback` | 打开/保存"设置"时 | 需要读写入参变量时做；不需要就 `exit 0` | 0 |
| `uninstall_callback` | 卸载后 | **唯一允许删数据的地方**（按向导选项判断） | 0 |

每个 `*_init` / `*_callback` 都是独立脚本（框架分别调用），空实现就 `exit 0`。它们默认
`#!/bin/sh`，写几句日志方便排查：

```sh
#!/bin/sh
LOG_FILE="${TRIM_PKGVAR}/app.log"
echo "$(date '+%Y-%m-%d %H:%M:%S') - install_init" >> "$LOG_FILE" 2>/dev/null
exit 0
```

### 环境变量（框架注入）

| 变量 | 含义 | 典型值 |
|---|---|---|
| `TRIM_APPDEST` | 程序本体目录（`app/` 展开到这里） | `/var/apps/<app>/target` |
| `TRIM_PKGVAR` | **数据目录**（升级/卸载默认不动） | `/var/apps/<app>/var` → `/usr/local/apps/@appdata/<app>` |
| `TRIM_TEMP_LOGFILE` | 写用户可见报错的文件；出问题一定要往里写 | 临时文件路径 |
| `wizard_*` | 向导里用户填的值（**只有走向导安装时才有**） | 如 `wizard_app_port=15100` |

> 不要假设 `set -e` 下的命令都有权限。脚本以 root 身份跑（见 `config/privilege`），
> 但**部署脚本（在 NAS 上以普通用户 + `sudo -n` 执行的那种）完全没有这个待遇**，见
> `pack-and-deploy.md` 的白名单小节。

## 四、装上以后 NAS 上的样子

安装完成后，同一份内容在几个位置以不同角色出现（`<app>` = appname，卷号按实际）：

```
/usr/local/apps/@appcenter/<app>/     # 真身：app/ 展开（bin 或 server、ui、…）
/usr/local/apps/@appdata/<app>/       # 数据目录 = $TRIM_PKGVAR
/usr/local/apps/@appconf/<app>/       # 配置 = $TRIM_APPDEST 旁边的 etc
/usr/local/apps/@apphome/<app>/       # home
/vol1/@appmeta/<app>/                 # 元数据

/var/apps/<app>/                      # 桌面/应用中心读这里
├── cmd/  config/  manifest  ICON.PNG  ICON_256.PNG
├── target -> /usr/local/apps/@appcenter/<app>   # ⇒ $TRIM_APPDEST
├── var    -> /usr/local/apps/@appdata/<app>     # ⇒ $TRIM_PKGVAR
├── etc    -> /usr/local/apps/@appconf/<app>
├── home   -> /usr/local/apps/@apphome/<app>
├── tmp    -> /usr/local/apps/@apptemp/<app>
└── meta   -> /vol1/@appmeta/<app>
```

推论（都很实用）：

- **socket 的规范位置**是 `$TRIM_APPDEST/app.sock`，即 `/var/apps/<app>/target/app.sock`；
  权限要 `chmod 666`（`srw-rw-rw-`），否则网关进程连不上。
- 应用中心显示的图标从 `/var/apps/<app>/ICON*.PNG` 与 `ui/images/` 读，**不是**从 `@appcenter` 读。
- 应用中心显示的版本号来自它自己的登记记录，**不是** `/var/apps/<app>/manifest`（手工改这个文件没用）。
- 数据目录权限是 root 私有，普通账号 `ls` 会 Permission denied —— 想确认数据没丢，用应用自己的接口，
  别指望在部署脚本里 `sudo -n ls`。
