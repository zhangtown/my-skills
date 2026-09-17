# my-skills 共享技能库 Agent 指引

本仓库是**所有 AI Agent 的统一技能主库**，本机路径 `~/.skills-manager/skills/`（git 仓库 `zhangtown/my-skills`）。

各端的技能条目都是**逐个技能 junction（目录联接）指向本目录**，**加/删/改技能只在这里做一份**，各端即时生效，不要往任何 Agent 自己的 skills 目录里单独塞副本：

| Agent | 目录 | 方式 |
|---|---|---|
| WorkBuddy | `~/.workbuddy/skills` | 每技能 junction → 本目录（唯一未入库的本地专属技能是 `docx-surgical-edit`） |
| Claude | `~/.claude/skills` | 每技能 junction → 本目录 |
| ZCode | `~/.zcode/skills` | 每技能 junction → 本目录 |
| CodeBuddy | `~/.codebuddy/skills` | 每技能 junction → 本目录 |
| Pi | `~/.pi/agent/skills` | 每技能 junction → 本目录 |
| Skills CLI / ZCode 全局 | `~/.agents/skills` | 每技能 junction → 本目录（`npx skills add -g` 的落地目录） |
| DeepSeek Harness | `~/.dsh/skills` | 每技能 junction → 本目录（skills-manager 里的 agent key 是 `deepseek_harness`） |

### 维护：检查 / 修复联接

`python rewire-skills.py`（在库根目录；干跑，只打印计划 + 审计）→ 加 `--apply` 执行：

| 参数 | 作用 |
|---|---|
| （无） | 干跑：打印计划与审计报告 |
| `--apply` | 把“内容一致的副本”换成 junction、修好指错目标的 junction |
| `--prune` | 删掉**目标已消失**的死链与**别名**（改名后的遗留链接）——只删链接，绝不动内容 |
| `--link-missing` | 给“任何 Agent 都读不到”的库内技能补链接 |
| `--link-dirs a,b` | 配合 `--link-missing`，只补进指定端 |
| `--force 技能名` | 强制用本库版本替换被取代的旧副本（会 rmtree，慎用） |

健康标准：结尾 `verify:` 那一行要 **`dead-links=0 aliases=0 conflicts=0 wrong-target=0 real-copies=0 orphans=0`**。
内容差异只看**逻辑内容**（CRLF/LF 视为一致，2026-09-17 修）；真差异报 `CONFLICT` 并原样保留。

**判断链接是否有效不要用 `os.path.isdir()`**：Windows 下断链 junction 的 `isdir` 是 False（这正是 2026-09-17 前
报 `ok: 350` 全绿却漏掉 6 条死链的原因），要用 `os.path.lexists(p) and not os.path.exists(p)`。

替换前各目录的原始内容保留在同级的 `*.bak-20260830` 里（Pi 的散装技能包移到 `~/.pi/agent/skill-packages/`）。

## 结构

- 每个子目录 = 一个技能（含 `SKILL.md`，frontmatter 需有 name/description/version）
- `.gitignore` 排除了 `*.pyz`、`node_modules/` 等大文件（GitHub 单文件 100MB 上限）；换新机器后这些大文件需单独拷贝，技能文档内应注明
- **本地大资产绝不入库**：`qwen-tts/`、`qwen-tts__skillhub/`（约 3.7GB 模型权重 + venv，`*.safetensors`）已在 `.gitignore` 手工屏蔽 ——
  该块曾被 skills-manager 的 `auto backup` 自动提交删掉过；若发现 `git status` 冒出 `qwen-tts/` 或 `*.safetensors`，先把规则加回去再 `git add`
- **但 `.skills-manager/` 元数据必须入库（不要再加整目录忽略规则）**：它是 skills-manager 的合并协议
  （`protocol.json` / `schema.json` / `skills/<uuid>.json` / `scenario-skills/`），每次 adopt/部署都会写入，
  忽略它会让多机合并状态不同步（2026-09-17 已修掉这条误伤规则，提交 `fa4b8e3`）
- 2026-09 集中化时回收入库的技能：`drawio2vsdx`（自研）、`academic-search`、`drawio-academic-skills`、`visio-skill`、`win-mingw-toolchain-bootstrap`、`frontend-dev`（原名 `前端开发`，已改名以与 SKILL.md 一致）；`drawio` 换为 bahayonghang v2.8.0（原 jgraph 单文件版见提交 `44d9cf9`）
- **库里有目录 ≠ App 里显示**：skills-manager 的「技能库」只列**已 adopt**（DB 有记录）的技能。2026-09-17 收编了
  `tender-bid-writer`（id `49c52d98-…`，6 端已部署）；其余 36 个目录是“裸躺”状态（各端可用、App 列表不显示）。
  要收编：`skills-manager-cli.exe skills adopt <库外的副本路径>` —— 直接传库内路径会被拒（source == destination），
  且 adopt 不会自动进预设/部署，需再 `presets add-skill Default <技能>` + `skills deploy --agent <各端> <技能>`
- `pdf` 技能已被同步删除，统一用 `kimi-pdf`（各端遗留的 `pdf` 死链已于 2026-09-17 清理）
- `AGENTS.md`/`.disable_to_model_invocation_migration.json` 等根目录散文件是配置/标记，不是技能

## ⚠️ 契约联动（speech-visual-html 专属）

`speech-visual-html` 实现的「ztEdit 原生格式」契约正本在另一个仓库：`https://github.com/zhangtown/Html-ZT-Edit`（WORKFLOW.md「二、数据模型」，本机 `D:\Program Files\html-zt-edit`，若已 clone）。

**改动该技能的格式/动画清单章节前，先确认编辑器端是否已同步升级契约版本**；改完在本机 ztEdit 仓库跑 `npm run check:contract` 校验两端一致。详见该 SKILL.md 开头的「跨仓库契约声明」。

## 习惯

- 装新技能：放进本库根目录 → `git add -A && git commit -m "feat: 添加 xx 技能" && git push`
- 开工前先 `git pull`（多机同步）
- Skills Manager（`~/.skills-manager/`）是安装器/备份工具，它的中央 checkout 恰好就是本目录；从市场安装的新技能会自动落到这里，装完记得在本库 commit + push
