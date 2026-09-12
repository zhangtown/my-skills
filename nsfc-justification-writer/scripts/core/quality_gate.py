#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List

from .hard_rules import load_quality_rule
from .latex_parser import strip_comments


@dataclass(frozen=True)
class QualityGateResult:
    avoid_commands_hits: List[str]

    @property
    def ok(self) -> bool:
        if self.avoid_commands_hits:
            return False
        return True


def check_new_body_quality(
    *,
    new_body: str,
    config: Dict[str, Any],
) -> QualityGateResult:
    rule = load_quality_rule(config)
    t = strip_comments(new_body or "")
    cmd_hits = [c for c in rule.avoid_commands if c and (c in t)]

    return QualityGateResult(
        avoid_commands_hits=cmd_hits,
    )
