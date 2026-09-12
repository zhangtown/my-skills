# 诊断报告示例（节选）

## 示例 1：结构完整但引用缺失

诊断结果：
- ✅ 结构完整：`subsubsection=4`
- ❌ 引用缺失：`.bib` 未找到 `Smith2020`、`Super1957`
- ℹ️ 字数（中文字符，不含注释）：2210

建议：
- 先补齐/核验 BibTeX（优先 DOI/链接或可核验题录），再使用 `\\cite{...}`。
- 宿主 AI 按 `references/boastful_expression_guidelines.md` 复核措辞；Python 不命中固定短语。

## 示例 2：结构缺失（阻塞）

诊断结果：
- ❌ 结构缺失：`subsubsection=2`，缺少背景、现状、局限、切入点
- ✅ 引用格式：所有 `\\cite{...}` 均在 `.bib` 中存在
- ℹ️ 字数（中文字符，不含注释）：830

说明：
- 只有用户或 legacy 配置显式启用结构检查时才按提示修复；默认不因缺少 `\\subsubsection` 骨架判定正文为空。
