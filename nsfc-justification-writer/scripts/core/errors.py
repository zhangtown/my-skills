#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

from typing import List, Optional


class SkillError(Exception):
    """
    统一的 Skill 异常基类：携带可读的修复建议（供 CLI 友好输出）。
    """

    def __init__(self, message: str, *, fix_suggestion: str = "") -> None:
        super().__init__(message)
        self.fix_suggestion = str(fix_suggestion or "").strip()


class TargetFileNotFoundError(SkillError):
    def __init__(self, *, target_relpath: str, project_root: str) -> None:
        super().__init__(
            f"目标文件不存在：{target_relpath}",
            fix_suggestion=(
                "请检查：\n"
                f"1) 项目根目录是否正确：{project_root}\n"
                "2) 标书模板是否已初始化（是否存在 extraTex/ 与 references/）\n"
                f"3) 目标文件路径是否应为：{target_relpath}\n"
            ),
        )


class TargetResolutionError(SkillError):
    def __init__(self, *, project_root: str, candidates: Optional[List[str]] = None) -> None:
        self.candidates = [str(x) for x in (candidates or [])]
        if self.candidates:
            detail = "\n".join(f"- {x}" for x in self.candidates[:20])
            message = "发现多个目标文件（自动流程将按优先级选择）：\n" + detail
        else:
            message = "未找到可自动选择的目标文件。"
        super().__init__(
            message,
            fix_suggestion=(
                f"请在项目配置 targets.justification_tex 或命令行 --target-file 中显式指定项目内正文文件：{project_root}\n"
                "可在 targets.justification_tex 中指定正文路径；自动流程不会依赖旧版固定文件名回退。"
            ),
        )


class MissingCitationKeysError(SkillError):
    def __init__(self, missing_keys: list[str]) -> None:
        self.missing_keys = [str(x) for x in (missing_keys or []) if str(x).strip()]
        super().__init__(
            f"检测到 {len(self.missing_keys)} 个缺失引用 bibkey（为避免幻觉引用，已拒绝写入）",
            fix_suggestion=(
                "建议：\n"
                "- 优先：提供 DOI/链接（或可核验题录信息），补齐并核验 references/*.bib 后重试\n"
                "- 或：删除未核验引用/改写为无引用的可核验描述\n"
                "- 如确需忽略该检查：在命令中加入 `--allow-missing-citations`\n"
            ),
        )


class BackupNotFoundError(SkillError):
    def __init__(self, run_id: str) -> None:
        self.run_id = run_id
        super().__init__(
            f"未找到 run_id={run_id} 的备份文件",
            fix_suggestion=(
                "建议：先运行 `list-runs` 查看可用 run_id；\n"
                "或检查 `config.yaml:workspace.runs_dir` 是否指向正确的任务级工作区。"
            ),
        )


class SectionNotFoundError(SkillError):
    def __init__(self, *, title: str, suggestions: list[str]) -> None:
        sug = "\n".join([f"- {t}" for t in suggestions[:10]]) if suggestions else "（无）"
        super().__init__(
            f"未找到匹配的小标题：{title}",
            fix_suggestion=("可用的小标题候选：\n" + sug + "\n\n提示：可加 `--suggest-alias` 输出更多候选。"),
        )


class QualityGateError(SkillError):
    def __init__(self, *, avoid_commands: list[str]) -> None:
        self.avoid_commands = [str(x) for x in (avoid_commands or []) if str(x).strip()]
        parts = []
        if self.avoid_commands:
            parts.append("可能破坏模板的命令：" + "、".join(self.avoid_commands[:10]))
        detail = "；".join(parts) if parts else "命中质量闸门"
        super().__init__(
            f"新正文命中质量闸门，已拒绝写入（{detail}）",
            fix_suggestion=(
                "建议：\n"
                "- 避免在正文中直接使用 \\section/\\subsection/\\input/\\include 等结构命令\n"
                "- 修订后重试；措辞中的吹牛式表述由宿主 AI 按 references/boastful_expression_guidelines.md 复核\n"
            ),
        )
