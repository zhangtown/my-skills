# my-skills 共享技能库 Agent 指引

本仓库是**所有 AI Agent 的统一技能主库**，本机路径 `~/.agents/skills/`。ZCode、Pi、WorkBuddy 等通过 Windows 目录联接（junction）共享它——**加/删/改技能只在这里做一份**，各端即时生效，不要往任何 Agent 自己的 skills 目录里单独塞副本。

## 结构

- 每个子目录 = 一个技能（含 `SKILL.md`，frontmatter 需有 name/description/version）
- `.gitignore` 排除了 `*.pyz`、`node_modules/` 等大文件（GitHub 单文件 100MB 上限）；换新机器后这些大文件需单独拷贝，技能文档内应注明
- `AGENTS.md`/`.disable_to_model_invocation_migration.json` 等根目录散文件是配置/标记，不是技能

## ⚠️ 契约联动（speech-visual-html 专属）

`speech-visual-html` 实现的「ztEdit 原生格式」契约正本在另一个仓库：`https://github.com/zhangtown/Html-ZT-Edit`（WORKFLOW.md「二、数据模型」，本机 `D:\Program Files\html-zt-edit`，若已 clone）。

**改动该技能的格式/动画清单章节前，先确认编辑器端是否已同步升级契约版本**；改完在本机 ztEdit 仓库跑 `npm run check:contract` 校验两端一致。详见该 SKILL.md 开头的「跨仓库契约声明」。

## 习惯

- 装新技能：放进本库根目录 → `git add -A && git commit -m "feat: 添加 xx 技能" && git push`
- 开工前先 `git pull`（多机同步）
- Skills Manager（`~/.skills-manager/`）只是安装器/备份工具，它的中央库不是本库；从中安装后应把技能文件落到本库再提交
