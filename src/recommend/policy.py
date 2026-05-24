"""Bandit 정책 + baseline 가드레일.

SOLID
-----
- SRP : 노출(가중치) 선택과 reward 기록만 담당.
- DIP : ThompsonBandit 와 BanditStateRepository 는 주입 가능.
"""

from __future__ import annotations

import random
from typing import Mapping, Optional

from src.config.settings import BanditSettings, get_settings
from src.recommend.arms import DEFAULT_ARMS, BanditArm
from src.recommend.bandit import ThompsonBandit
from src.recommend.bandit_store import BanditStateRepository


class RecommendPolicy:
    def __init__(
        self,
        bandit: ThompsonBandit | None = None,
        settings: BanditSettings | None = None,
        *,
        store: Optional[BanditStateRepository] = None,
    ) -> None:
        if bandit is None:
            bandit = ThompsonBandit(DEFAULT_ARMS, store=store)
        self._bandit = bandit
        self._settings = settings or get_settings().bandit
        self._baseline_id = "baseline"

    @property
    def baseline_arm_id(self) -> str:
        return self._baseline_id

    def select_arm(self, *, context_key: str = "default") -> BanditArm:
        """가드레일 적용된 arm 을 반환한다."""
        if random.random() < self._settings.baseline_min_share:
            return next(a for a in DEFAULT_ARMS if a.arm_id == self._baseline_id)
        return self._bandit.sample_arm(context_key)

    def select_weights(
        self, *, user_id: str, context_key: str = "default"  # noqa: ARG002 (예약)
    ) -> Mapping[str, float]:
        arm = self.select_arm(context_key=context_key)
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
