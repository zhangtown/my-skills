# 本机技能库：布局、部署与提交约定

本机（Windows）的 agent 技能**只有一个主库**，各端都是软链接指过来。改技能只改库里的那一份，
但**部署状态要单独确认**——"库里改了、某端还是旧的"是这套机制最常出的事。

## 一、布局

| 位置 | 说明 |
|---|---|
| `D:/ProgramData/projects/my-skills/`（= `~/.skills-manager/skills/`） | **技能主库**，git 仓库 `zhangtown/my-skills`。一级子目录 = 一个技能 |
| `~/.pi/agent/skills/<技能名>` | pi 端的入口：逐个技能的 **junction（目录联接）** 指向主库 |
| `~/.claude/skills/<技能名>` | Claude Code 端入口，同上 |
| `~/.workbuddy/skills`、`~/.zcode/skills`、`~/.codebuddy/skills`、`~/.agents/skills`、`~/.dsh/skills` | 其余各端入口，同上 |
| `my-skills/AGENTS.md` | **本库的权威约定**（联接修复、`.skills-manager/` 元数据、大资产忽略规则…）。动手前先读它 |
| `my-skills/.skills-manager/` | skills-manager 的合并协议元数据，**必须入库**，别加整目录忽略规则 |

## 二、加一个新技能

1. 在库根建目录：`<技能名>/SKILL.md`（+ 按需 `references/`、`scripts/`、`assets/`、`evals/`）。
   技能名用小写连字符，**与 frontmatter 的 `name` 一致**。
2. **补到各端的链接**：库根 `python rewire-skills.py`（干跑看计划）→ `--apply --link-missing` 执行；
   只想补某一端用 `--link-dirs pi,claude`。健康标准是末尾那行
   `verify: dead-links=0 aliases=0 conflicts=0 wrong-target=0 real-copies=0 orphans=0`。
3. 提交：`git add <技能名>` → `git commit -m "新增技能 <技能名>：<一句话>"`。
   改动已有技能时，消息里写清补了什么（"补充 <主题> 的实测细节"），方便日后回溯。

## 三、四个必踩的坑

- **不要往各端目录里塞副本**：副本会与主库分叉，之后所有改动都"不生效"。发现某端是独立副本时，
  用 `rewire-skills.py --apply` 换成联接；确实要强制替换用 `--force <技能名>`（会删目录，慎用）。
- **判断链接是否有效别用 `os.path.isdir()`**：Windows 下断链 junction 的 `isdir` 返回 False，
  历史上正是它让"全绿"的审计漏掉 6 条死链。用 `os.path.lexists(p) and not os.path.exists(p)` 判断断链。
- **暂存区目录必须以点开头**：`rewire-skills.py` 把"非点开头的一级目录"当技能，`.staging/` 写错成 `_staging/`
  会被扫成技能名，甚至被 `--link-missing` 链进各端。
- **大资产不入库**：模型权重、`*.pyz`、`node_modules/` 等已在 `.gitignore` 里排除，换机要单独拷贝；
  技能文档里应注明"哪些文件不在仓库里、从哪补"。

## 四、库里有目录 ≠ App 里显示

skills-manager 的图形界面只列**已 adopt**（数据库有记录）的技能；裸放在库里的技能各端能用、App 列表里看不到。

收编要传**库外的那份副本**（传库内路径会被拒绝；adopt 本身不复制文件，只登记，`central_path` 仍指向库里那份）：

```bash
CLI=~/AppData/Local/skills-manager/skills-manager-cli.exe
# 1) 登记：外部副本路径 + 指定 git 源（带 --git-url 才会有"检查更新"能力，否则 source_type=local）
"$CLI" skills adopt --dry-run --git-url https://github.com/zhangtown/my-skills.git \
        --git-subpath <技能名> <库外副本>/<技能名>        # 先干跑，看到 reason="ready" 再去掉 --dry-run
# 2) 加入预置 + 部署到各端（已安装且启用的代理才需要）
"$CLI" presets add-skill Default <技能名>
"$CLI" skills deploy --agent <代理key> <技能名>            # 可一次传多个技能名；代理 key 见 skills agents list
# 3) 核对
"$CLI" skills list --json | grep -A3 <技能名>             # 看 source_type=git、presets、deployed_to
"$CLI" skills check <技能名>                              # last_check_error 应为 null
```

登记会在 `skills/.skills-manager/{skills,scenario-skills}/` 生成 JSON 元数据——**这些要一起提交**，否则换台机器 App 里就看不到。
日常开发技能时**不必**每次走这三步——各端的 junction 已经能让它生效，纳管是"让 App 认识它"这一步。

## 五、改动后的自检

1. 该端技能目录里能读到新内容（`cat <端目录>/<技能名>/SKILL.md` 与库里一致——联接的话本来就是同一份）
2. `rewire-skills.py` 干跑，末尾那行全 0
3. 库 `git status` 干净，或明确知道哪些改动还没提交
4. **在一个全新会话里试一次触发**（改描述之后尤其必要）：本机自测通过 ≠ 别的端能触发
