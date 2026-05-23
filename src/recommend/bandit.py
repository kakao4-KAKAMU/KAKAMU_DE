"""Thompson Sampling contextual bandit."""

from __future__ import annotations

import random
from dataclasses import dataclass

from src.recommend.arms import DEFAULT_ARMS, BanditArm


@dataclass
class ArmState:
    alpha: float = 1.0
    beta: float = 1.0
    n_pulls: int = 0
    n_rewards: int = 0


class ThompsonBandit:
    def __init__(self, arms: list[BanditArm] | None = None) -> None:
        self._arms = arms or DEFAULT_ARMS
        self._state: dict[tuple[str, str], ArmState] = {}

    def _key(self, arm_id: str, context_key: str) -> tuple[str, str]:
        return (arm_id, context_key)

    def get_state(self, arm_id: str, context_key: str) -> ArmState:
        k = self._key(arm_id, context_key)
        if k not in self._state:
            self._state[k] = ArmState()
        return self._state[k]

    def sample_arm(self, context_key: str = "default") -> BanditArm:
        best_arm = self._arms[0]
        best_score = -1.0
        for arm in self._arms:
            st = self.get_state(arm.arm_id, context_key)
            score = random.betavariate(st.alpha, st.beta)
            if score > best_score:
                best_score = score
                best_arm = arm
        st = self.get_state(best_arm.arm_id, context_key)
        st.n_pulls += 1
        return best_arm

    def update(self, arm_id: str, context_key: str, reward: float) -> None:
        st = self.get_state(arm_id, context_key)
        st.n_pulls += 1
        if reward > 0:
            st.alpha += reward
            st.n_rewards += 1
        else:
            st.beta += abs(reward)


__all__ = ["ThompsonBandit", "ArmState"]
