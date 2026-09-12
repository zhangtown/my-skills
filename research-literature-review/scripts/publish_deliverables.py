#!/usr/bin/env python3
"""把已生成的核心交付物安全发布到用户指定目录。"""

from __future__ import annotations

import fnmatch
import shutil
from dataclasses import dataclass
from pathlib import Path


class PublishError(RuntimeError):
    """发布目录不满足白名单或存在覆盖风险。"""


@dataclass(frozen=True)
class PublishResult:
    published: list[str]


CORE_PATTERNS = ("*_review.pdf", "*_review.docx")
SUPPORTING_PATTERNS = (
    "*_review.tex",
    "*_参考文献.bib",
    "*_工作条件.md",
    "*_验证报告.md",
)


def _allowed(name: str, include_supporting: bool) -> bool:
    patterns = CORE_PATTERNS + (SUPPORTING_PATTERNS if include_supporting else ())
    return any(fnmatch.fnmatch(name, pattern) for pattern in patterns)


def _allowed_supporting(name: str) -> bool:
    return any(fnmatch.fnmatch(name, pattern) for pattern in SUPPORTING_PATTERNS)


def publish_deliverables(
    source_dir: Path,
    publish_dir: Path,
    *,
    include_supporting: bool = False,
    force: bool = False,
) -> PublishResult:
    source = Path(source_dir).expanduser().resolve()
    target = Path(publish_dir).expanduser().resolve()
    if not source.is_dir():
        raise PublishError(f"交付源目录不存在：{source}")
    target.mkdir(parents=True, exist_ok=True)

    supporting_source = source / "supporting"
    source_unexpected = [
        p
        for p in source.iterdir()
        if p.name != "supporting" and (p.is_dir() or not _allowed(p.name, False))
    ]
    if source_unexpected:
        names = ", ".join(sorted(p.name for p in source_unexpected))
        raise PublishError(f"交付源目录包含未授权文件或目录，请移入 artifacts/reference：{names}")
    if supporting_source.exists() and not supporting_source.is_dir():
        raise PublishError("交付源目录的 supporting 必须是目录")
    if include_supporting and supporting_source.exists():
        supporting_unexpected = [
            p for p in supporting_source.iterdir() if p.is_dir() or not _allowed_supporting(p.name)
        ]
        if supporting_unexpected:
            names = ", ".join(sorted(p.name for p in supporting_unexpected))
            raise PublishError(f"supporting 目录包含未授权文件：{names}")

    unexpected = [p for p in target.iterdir() if p.is_dir() or not _allowed(p.name, include_supporting)]
    if unexpected:
        names = ", ".join(sorted(p.name for p in unexpected))
        raise PublishError(f"发布目录包含未授权文件或目录：{names}")

    candidates = sorted(p for p in source.iterdir() if p.is_file() and _allowed(p.name, False))
    if include_supporting and supporting_source.exists():
        candidates.extend(sorted(p for p in supporting_source.iterdir() if p.is_file() and _allowed_supporting(p.name)))
    if not candidates:
        raise PublishError(f"交付源目录没有可发布文件：{source}")

    conflicts = [p.name for p in candidates if (target / p.name).exists()]
    if conflicts and not force:
        raise PublishError(f"发布目录已有同名文件，拒绝覆盖：{', '.join(conflicts)}")

    for source_file in candidates:
        destination = target / source_file.name
        temporary = destination.with_name(f".{destination.name}.tmp")
        shutil.copy2(source_file, temporary)
        temporary.replace(destination)

    return PublishResult(published=[p.name for p in candidates])
