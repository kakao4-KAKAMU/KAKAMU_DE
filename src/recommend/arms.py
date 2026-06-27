"""Bandit arm 정의 (가중치 벡터)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping


@dataclass(frozen=True)
class BanditArm:
    arm_id: str
    weights: Mapping[str, float]
    description: str = ""


DEFAULT_ARMS: list[BanditArm] = [
    BanditArm("baseline", {"w_vec": 0.55, "w_kw": 0.15, "w_theme": 0.10, "w_mood": 0.05, "w_user": 0.15}, "baseline"),
    BanditArm("vec_heavy", {"w_vec": 0.70, "w_kw": 0.10, "w_theme": 0.08, "w_mood": 0.02, "w_user": 0.10}, "semantic heavy"),
    BanditArm("kw_heavy", {"w_vec": 0.40, "w_kw": 0.30, "w_theme": 0.12, "w_mood": 0.08, "w_user": 0.10}, "keyword heavy"),
    BanditArm("user_heavy", {"w_vec": 0.45, "w_kw": 0.10, "w_theme": 0.10, "w_mood": 0.05, "w_user": 0.30}, "personalization heavy"),
    BanditArm("balanced", {"w_vec": 0.50, "w_kw": 0.15, "w_theme": 0.15, "w_mood": 0.10, "w_user": 0.10}, "balanced"),
    BanditArm("theme_mood", {"w_vec": 0.45, "w_kw": 0.10, "w_theme": 0.20, "w_mood": 0.15, "w_user": 0.10}, "theme/mood heavy"),
]


__all__ = ["BanditArm", "DEFAULT_ARMS"]
