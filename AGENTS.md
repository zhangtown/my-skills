# my-skills 共享技能库 Agent 指引

本仓库是**所有 AI Agent 的统一技能主库**，本机路径 `~/.skills-manager/skills/`（git 仓库 `zhangtown/my-skills`）。

各端的技能条目都是**逐个技能 junction（目录联接）指向本目录**，**加/删/改技能只在这里做一份**，各端即时生效，不要往任何 Agent 自己的 skills 目录里单独塞副本：

| Agent | 目录 | 方式 |
|---|---|---|
| WorkBuddy | `~/.workbuddy/skills` | 每技能 junction → 本目录（另有 2 个本地专属技能：`win-mingw-toolchain-bootstrap` 已入库，`drawio.bak.*` 为历史备份） |
| Claude | `~/.claude/skills` | 每技能 junction → 本目录 |
| ZCode | `~/.zcode/skills` | 每技能 junction → 本目录 |
| CodeBuddy | `~/.codebuddy/skills` | 每技能 junction → 本目录 |
| Pi | `~/.pi/agent/skills` | 每技能 junction → 本目录 |
| Skills CLI / ZCode 全局 | `~/.agents/skills` | 每技能 junction → 本目录（`npx skills add -g` 的落地目录） |

### 维护：检查 / 修复联接

`python ~/.skills-manager/rewire-skills.py`（干跑，只打印计划）→ 加 `--apply` 执行；
`--force 技能名` 用于强制用本库版本替换被取代的旧副本。脚本只会把**内容逐字节一致**的副本换成 junction，
内容不同的会报 `CONFLICT` 并原样保留。**装完新技能后跑一次干跑**，输出 `ok: N` 且无 `REWIRE/CONFLICT` 即为健康。

替换前各目录的原始内容保留在同级的 `*.bak-20260830` 里（Pi 的散装技能包移到 `~/.pi/agent/skill-packages/`）。

## 结构

- 每个子目录 = 一个技能（含 `SKILL.md`，frontmatter 需有 name/description/version）
- `.gitignore` 排除了 `*.pyz`、`node_modules/` 等大文件（GitHub 单文件 100MB 上限）；换新机器后这些大文件需单独拷贝，技能文档内应注明
- **本地大资产绝不入库**：`qwen-tts/`（约 3.7GB 模型权重 + venv）与安装器元数据 `.skills-manager/` 已在 `.gitignore` 手工屏蔽 ——
  该块曾被 skills-manager 的 `auto backup` 自动提交删掉过，若发现 `git status` 冒出 `qwen-tts/` 或 UUID 命名的 `.json`，先把规则加回去再 `git add`
- 2026-09 集中化时回收入库的技能：`drawio2vsdx`（自研）、`academic-search`、`drawio-academic-skills`、`visio-skill`、`win-mingw-toolchain-bootstrap`、`前端开发`；`drawio` 换为 bahayonghang v2.8.0（原 jgraph 单文件版见提交 `44d9cf9`）
- `AGENTS.md`/`.disable_to_model_invocation_migration.json` 等根目录散文件是配置/标记，不是技能

## ⚠️ 契约联动（speech-visual-html 专属）

`speech-visual-html` 实现的「ztEdit 原生格式」契约正本在另一个仓库：`https://github.com/zhangtown/Html-ZT-Edit`（WORKFLOW.md「二、数据模型」，本机 `D:\Program Files\html-zt-edit`，若已 clone）。

**改动该技能的格式/动画清单章节前，先确认编辑器端是否已同步升级契约版本**；改完在本机 ztEdit 仓库跑 `npm run check:contract` 校验两端一致。详见该 SKILL.md 开头的「跨仓库契约声明」。

## 习惯

- 装新技能：放进本库根目录 → `git add -A && git commit -m "feat: 添加 xx 技能" && git push`
- 开工前先 `git pull`（多机同步）
- Skills Manager（`~/.skills-manager/`）是安装器/备份工具，它的中央 checkout 恰好就是本目录；从市场安装的新技能会自动落到这里，装完记得在本库 commit + push
