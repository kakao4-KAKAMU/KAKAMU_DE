"""Bandit 정책 + baseline 가드레일."""

from __future__ import annotations

import random
from typing import Mapping

from src.config.settings import BanditSettings, get_settings
from src.recommend.arms import DEFAULT_ARMS, BanditArm
from src.recommend.bandit import ThompsonBandit


class RecommendPolicy:
    def __init__(
        self,
        bandit: ThompsonBandit | None = None,
        settings: BanditSettings | None = None,
    ) -> None:
        self._bandit = bandit or ThompsonBandit(DEFAULT_ARMS)
        self._settings = settings or get_settings().bandit
        self._baseline_id = "baseline"

    def select_weights(
        self, *, user_id: str, context_key: str = "default"
    ) -> Mapping[str, float]:
        # baseline 최소 노출 가드레일
        if random.random() < self._settings.baseline_min_share:
            arm = next(a for a in DEFAULT_ARMS if a.arm_id == self._baseline_id)
        else:
            arm = self._bandit.sample_arm(context_key)
        return dict(arm.weights)

    def record_reward(
        self,
        *,
        arm_id: str,
        context_key: str,
        reward: float,
    ) -> None:
        self._bandit.update(arm_id, context_key, reward)


__all__ = ["RecommendPolicy"]
