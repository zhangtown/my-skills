# 排查手册：症状 → 根因 → 验证

## 万能排查顺序

出问题先别动客户端，按这个顺序**自证一半**：

1. **服务端文件对不对**：`tar tzf` 包内容、`/var/apps/<app>/` 与 `@appcenter` 里的文件 md5
   与本地构建产物比对。
2. **跑的东西对不对**：`health` 端点返回的版本、`appcenter-cli list` 的版本、进程命令行。
3. **有没有人请求过**：看网关/nginx 访问日志里有没有客户端请求新资源的记录。
   如果"最后一次请求图标是几小时前、之后一次都没有"——那就是客户端缓存，服务端再改也没用。
4. **才轮到客户端**：无痕窗口 / 杀进程重进 / 清缓存。

这条顺序能把"改了没生效"这类问题的时间从一小时压到五分钟。

## 症状表

| 症状 | 最可能的原因 | 怎么确认 | 怎么修 |
|---|---|---|---|
| 桌面点开一片空白 | socket 没建出来、或权限不是 666；`gatewaySocket` 文件名与实际不一致 | `ls -l /var/apps/<app>/target/*.sock`（应为 `srw-rw-rw-`） | 启动脚本里等 socket + `chmod 666`；核对 `app/ui/config` 的 `gatewaySocket` |
| 桌面入口直接点不开 | `desktop_applaunchname` 与 `app/ui/config` 里 `.url` 的键不一致；`url` 路径不对 | 比对 manifest 与 ui/config 两处字段 | 改成一致 |
| 应用中心显示"未运行"但进程在 | `status` 退出码写错（必须 0=运行中、3=未运行） | 手工 `cmd/main status; echo $?` | 改退出码 |
| 打包了但 NAS 上是旧的 | 用了 `install-fpk`（对已装应用是空操作） | 输出里有没有 `Application [<app>] is installed.` | 改用 `install-local -d <解包目录> -v <卷>` |
| 应用中心版本号不更新 | 手工部署/五步法只换文件，不更新登记记录 | `appcenter-cli list` 里的版本 | 走一次正规安装；手工改 `/var/apps/<app>/manifest` 无效 |
| 图标还是旧的 | 图标 URL 无版本参数 + 客户端长缓存；应用中心服务内存里还是旧清单 | 无痕窗口再看一次；看网关日志里图标最后被请求的时间 | 无痕确认服务端已新；重启 `trim_app_center` 让它重扫；用户端清缓存 |
| 名字改了但某处还显示旧的 | 多层品牌漏改（见 icons-and-branding.md 的七层表） | 逐层核对 | 逐层改 |
| PIN 输对了还让重输（桌面正常、手机不行） | 移动端 WebView 拦了第三方 Cookie | 后端日志里看解锁请求后有没有拿到令牌/Cookie；只有移动端失败 | 令牌走 Header + URL 参数，别依赖 Cookie |
| 页面能打开但所有按钮报错 | SPA 把 `/api/*` 也回落成了 `index.html`，前端把 HTML 当 JSON 解析 | `curl` 一个不存在的 `/api/xxx`，看返回的是 HTML 还是 JSON | 未匹配的 `/api/*` 返回 404 + JSON 错误体 |
| 图片/静态资源 404 | 用了根绝对路径（`/assets/...`）而不是相对路径；或前端构建产物目录名与后端已有的路由撞车 | devtools 看 404 的 URL；对照 `gatewayPrefix` | 改相对路径；换构建产物目录名 |
| 升级后应用停着没起 | 部署脚本中途失败（常见：`sudo -n` 不在白名单的命令） | 脚本输出最后一行；`systemctl status` / `appcenter-cli list` | 只用白名单命令；改成不依赖 sudo 的自检 |
| 用户在自己电脑上打开 NAS 上的文件说"没权限" | 应用以 root 跑，写出来的是 `root:root` | `ls -ld` 看属主/权限 | 按父目录对齐 uid/gid 与权限位（先 chown 后 chmod，只对齐不放大） |
| 卸载后数据没了 / 想让数据留下 | `uninstall_callback` 里删了 `$TRIM_PKGVAR` | 看脚本里 `wizard_data_action` 的判断 | 默认保留；只有用户显式选"删除"才删 |

## 常用命令

```bash
# 应用登记与版本
sudo -n /usr/local/bin/appcenter-cli list

# 内嵌（socket）模式的自检——不需要经过网关
SOCK=/var/apps/<app>/target/app.sock
curl -s --unix-socket $SOCK http://localhost/api/health
curl -s --unix-socket $SOCK -o /dev/null -w '%{http_code} %{content_type} %{size_download}B\n' \
  http://localhost/                                   # 入口页
curl -s --unix-socket $SOCK http://localhost/static/index-xxx.js | md5sum   # 与本地产物比对

# 端口模式
curl -s http://127.0.0.1:<port>/api/health

# 包内容
tar tzf deploy/fnos-app/<app>.fpk | head -30
tar tzf deploy/fnos-app/<app>.fpk | grep -c wizard        # 期望 0（没用向导时）

# 应用自身日志（脚本与程序都往这里写）
tail -50 /var/apps/<app>/var/app.log      # 需要权限；也可以让程序把日志写到别处

# 应用中心服务（图标/清单不刷新时重启它）
sudo -n systemctl restart trim_app_center
```

## "升级没生效"的分层判定表

这是最常见也最费时间的一类问题。**先判断是哪一层**，再动手：

| 层 | 判据 | 不通过时说明 |
|---|---|---|
| 包 | 本地 `tar tzf` 里有没有你的新文件 | 打包就没成功 |
| 部署 | `/var/apps/<app>/target/` 里文件的 md5 与本地一致 | 传上去/装上去失败（install-fpk 空操作是头号原因） |
| 运行 | `health` 版本 == manifest 版本；进程启动时间是最新的 | 装上了但没重启/没起来 |
| 登记 | `appcenter-cli list` 的版本 | 走的是手工部署，登记没更新 |
| 客户端 | 无痕窗口看到的界面是否为新 | 用户端缓存（图标几乎总是这一层） |

每一层都有独立的验证手段，别跳层猜。真实案例：用户说"NAS 上没更新"，
逐层查下来 1~4 层全绿（文件、版本、图标 md5 全部与本地一致），
最后一层才是原因——客户端缓存，而且在服务端日志里能看到"那个资源已经几小时没人请求了"。
