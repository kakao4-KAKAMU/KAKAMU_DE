"""Implicit feedback → reward scalar."""

from __future__ import annotations

from typing import Literal

Action = Literal["click", "dwell", "like", "skip", "dislike"]

REWARD_MAP: dict[Action, float] = {
    "click": 1.0,
    "dwell": 2.0,
    "like": 3.0,
    "skip": -1.0,
    "dislike": -2.0,
}


def reward_from_action(action: Action, *, dwell_seconds: float = 0.0) -> float:
    if action == "dwell" and dwell_seconds < 30:
        return 0.0
    return REWARD_MAP.get(action, 0.0)


__all__ = ["reward_from_action", "REWARD_MAP"]
