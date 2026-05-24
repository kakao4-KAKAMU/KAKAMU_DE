"""Thompson Sampling contextual bandit.

SOLID
-----
- SRP : posterior 표본/업데이트만 담당. 영속화는 BanditStateRepository 에 위임.
- DIP : ``store`` 는 Protocol 로 주입되어 in-memory ↔ DB 교체가 자유롭다.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Optional

from src.recommend.arms import DEFAULT_ARMS, BanditArm
from src.recommend.bandit_store import BanditStateRepository, BanditStateRow


@dataclass
class ArmState:
    alpha: float = 1.0
    beta: float = 1.0
    n_pulls: int = 0
    n_rewards: int = 0


class ThompsonBandit:
    """Beta-Bernoulli Thompson Sampling.

    Args:
        arms: 후보 arm 리스트. None 이면 :data:`DEFAULT_ARMS`.
        store: BanditStateRepository 구현. 주입 시 write-through 와 시작 시 load.
    """

    def __init__(
        self,
        arms: list[BanditArm] | None = None,
        *,
        store: Optional[BanditStateRepository] = None,
    ) -> None:
        self._arms = arms or DEFAULT_ARMS
        self._state: dict[tuple[str, str], ArmState] = {}
        self._store = store
        if store is not None:
            self._hydrate_from_store(store)

    # ------------------------------------------------------------------
    # Hydration
    # ------------------------------------------------------------------
    def _hydrate_from_store(self, store: BanditStateRepository) -> None:
        for row in store.load_all():
            self._state[(row.arm_id, row.context_key)] = ArmState(
                alpha=row.alpha,
                beta=row.beta,
                n_pulls=row.n_pulls,
                n_rewards=row.n_rewards,
            )

    # ------------------------------------------------------------------
    # Core
    # ------------------------------------------------------------------
    def _key(self, arm_id: str, context_key: str) -> tuple[str, str]:
        return (arm_id, context_key)

    def get_state(self, arm_id: str, context_key: str) -> ArmState:
        k = self._key(arm_id, context_key)
        if k not in self._state:
            self._state[k] = ArmState()
        return self._state[k]

    def _persist(self, arm_id: str, context_key: str) -> None:
        if self._store is None:
            return
        st = self._state[self._key(arm_id, context_key)]
        self._store.upsert_state(
            BanditStateRow(
                arm_id=arm_id,
                context_key=context_key,
                alpha=st.alpha,
                beta=st.beta,
                n_pulls=st.n_pulls,
                n_rewards=st.n_rewards,
            )
        )

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
        self._persist(best_arm.arm_id, context_key)
        return best_arm

    def update(self, arm_id: str, context_key: str, reward: float) -> None:
        st = self.get_state(arm_id, context_key)
        st.n_pulls += 1
        if reward > 0:
            st.alpha += reward
            st.n_rewards += 1
        else:
            st.beta += abs(reward)
        self._persist(arm_id, context_key)


__all__ = ["ThompsonBandit", "ArmState"]
