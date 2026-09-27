# 打包、升级与验收

## 一、打包（`pack.sh`）

顺序不能调，每一步都有原因：

```bash
# 0) 可选：版本号 patch +1（写进 manifest，同时传给 -X main.version）
# 1) 生成图标  ← 必须在编译前，否则 //go:embed icon.png 嵌进去的还是旧的
go run ./tools/mkicon -out "$APP"
# 2) 前端（可选，产物直接落在 internal/webui/dist，由 go:embed 打进二进制）
( cd ui && npm run build )
#    ⚠ vite 默认把产物放 assets/ 且用绝对路径 —— 很容易撞你自己的数据路由
#    （比如正文图片就是 /assets/<图片名>），按下面固定配置，并加一条构建后门禁：
#    ui/vite.config.ts:  base:'./'  +  assetsDir:'static'
#    产物里出现 assets/ 目录就直接报错退出（写成 npm postbuild 脚本）
# 3) 交叉编译成 linux/amd64 静态二进制
CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build -trimpath \
  -ldflags="-s -w -X main.version=$VERSION" -o "$APP/app/bin/<binary>" ./cmd/<binary>
chmod +x "$APP/app/bin/<binary>"
# 4) 打包
fnpack build --directory "$APP"     # 在当前目录产出 <app>.fpk
mv -f ./*.fpk deploy/fnos-app/
```

`fnpack` 不在系统里，去官方静态地址下一个放进项目 `.toolchain/fnpack/`（**不要入库**）：

```
Windows: https://static2.fnnas.com/fnpack/fnpack-1.2.3-windows-amd64  → .toolchain/fnpack/fnpack.exe
Linux:   https://static2.fnnas.com/fnpack/fnpack-1.2.3-linux-amd64    → .toolchain/fnpack/fnpack
```

`.gitignore` 必须排掉：`*.fpk`、交叉编译出的二进制、`.toolchain/`、`deploy/fnos-app/nas.env`。
**别把构建产物提交进仓库**——真实教训：一个 6.8MB 的 Linux 二进制被提交过，仓库体积和
每次 `git status` 都被它污染，最后还得 `git rm --cached` 收拾。

`fnpack` 输出之后先自检一遍，**fpk 是 tar.gz**：

```bash
tar tzf deploy/fnos-app/<app>.fpk | head -20
tar tzf deploy/fnos-app/<app>.fpk | grep -c wizard      # 期望 0（见 app-modes.md）
tar tzf deploy/fnos-app/<app>.fpk | grep -c 'ICON'      # 期望 2
```

## 二、版本号：三处必须一致

| 位置 | 谁看它 |
|---|---|
| `manifest` 的 `version` | 应用清单 / 升级判断 |
| 二进制里的版本（`-X main.version`，由 `/api/health` 吐出） | **你**，用来证明 NAS 上跑的到底是哪一版 |
| 应用中心的登记记录 | 用户在应用中心看到的版本号 |

前两处由 `pack.sh` 保证一致；第三处**只有走正规安装才会更新**（见下）。
`/api/health` 返回版本号这一条极其值钱：没有它，"升级到底生效没有"只能靠猜。

如果发 Release：tag 名必须等于 manifest 的版本号（`v0.6.6` ↔ `0.6.6`），附件由 CI 构建——
**别拿本机手工打的包顶 Release 附件**：不同 Go 工具链（1.24 vs 1.27）产出的体积本来就不一样（7.45MB vs 8.29MB），
混用会让“发布的是哪一版”变得说不清。

## 三、安装与升级（`install.sh`）

```bash
bash deploy/fnos-app/install.sh              # 打包（默认版本号 +1）并安装
bash deploy/fnos-app/install.sh --no-bump    # 用当前版本号（首次安装）
```

流程：打包 → `scp` 到 NAS 的 `/tmp/` → 远端 `tar xzf` 到一个临时目录 →
`sudo -n appcenter-cli install-local -d <解包目录> -v <卷>` → 自检。

### 为什么不能用 `install-fpk`

`appcenter-cli install-fpk` 对**已安装的同名应用是空操作**，版本号更高也一样：

```
Application [<app>] is installed.
```

文件一个字节都不换。所以"我明明打包了、NAS 上还是旧的"十有八九是踩了这条。
`install-local -d <解包目录> -v <卷>` 才会真正替换（内部流程：停止 → 卸载 → 安装 → 启动）。
`-d` 要指向**解包后的目录**（fpk 的展开内容），不是 fpk 文件本身。

### 数据安全

- `install-local` 的卸载/安装**不会动数据目录**（`/usr/local/apps/@appdata/<app>`）。
  实测验证方式：装前装后对比某个数据文件的**字节数与 mtime**，一致即可。
- 卸载向导里"删除数据"的默认值是保留（`wizard_data_action=keep`），非交互安装走默认。
- 自己写部署脚本时，**不要**顺手 `rm -rf` 任何 `@appdata` 路径。想更保险就先备份：
  `sudo -n cp -a <数据目录> /tmp/<app>-data-backup-$(date +%H%M)`。

### `sudo -n` 的白名单

NAS 上普通账号并不是什么都能免密 sudo。实测可用：`appcenter-cli`、`cp`、`install`；
实测**不可用**：`ls`、`md5sum`、`cat`（会 `sudo: a password is required`）。

- 用一个新命令前，先单独跑一次确认；`sudo -n -l` 最省事。
- **绝对不要把不在白名单的命令串进 `set -e` 的部署脚本**：会在中途中断，留下一个停着的应用。
  真实教训：某次升级因为 `sudo -n md5sum` 失败而中断，应用停着没起来。
- 自检尽量只用白名单内的命令 + 不需要 sudo 的 HTTP 探测（`curl`）。要看数据目录内容，
  用应用自己的接口，或让用户手动看一眼。

### 手工"五步法"（没有 install-local 时的兜底）

```bash
sudo -n appcenter-cli stop <app>
sudo -n cp <旧二进制> <旧二进制>.bak-$(date +%H%M)          # 先备份，能回滚
sudo -n install -m 755 -o root -g root <新二进制> <目标路径>
sudo -n appcenter-cli start <app>
curl -s --unix-socket /var/apps/<app>/target/app.sock http://localhost/api/health
```

注意：手工替换**不会更新应用中心的版本号与图标登记**（那一步只有正规安装会做），
只在应急时用。

## 四、验收清单

按顺序做，每一条都能被"再看一眼"验证：

1. **本机**：逻辑测试 / 冒烟测试全过；`pack.sh` 能在本机从零跑通。
2. **包内容**：`tar tzf` 看条目齐全（`app.tgz` / `cmd/*` / `config/*` / `manifest` / `ICON*`），
   向导条目数 = 0（若你没打算用向导）。
3. **实机版本**：`appcenter-cli list` 的版本 == manifest 版本 == `health` 返回的版本。
4. **静态产物**：`curl` 应用入口页与 JS 包，与本地构建产物**逐字节**比对（md5 或内容特征串）。
   这一条能一次性证明"前端确实跟着上去了"。
5. **图标**：`/var/apps/<app>/ICON*.PNG`、`app/ui/images/*`、程序 favicon 端点三处的 md5
   与仓库文件一致。
6. **数据**：升级前后数据文件的大小与 mtime 不变；应用里能正常读到旧数据。
7. **品牌逐层**：按 `icons-and-branding.md` 的七层表过一遍。
8. **浏览器**：真机/手机各打开一次（**用无痕窗口排掉缓存**）；内嵌应用确认 socket 模式
   （`curl --unix-socket`）也正常。

## 五、回滚

- 保留上一版 fpk（`deploy/fnos-app/<app>.fpk` 改名存档）与二进制备份（`*.bak-HHMM`）。
- 回滚 = 用旧 fpk 再走一次 `install-local`（最快），或手工五步法换回旧二进制。
- 数据通常不用回滚：升级不该动数据；真出问题就用 `/tmp/<app>-data-backup-*` 覆盖回去
  （**先停应用**）。
