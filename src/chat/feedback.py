"""사용자 implicit feedback → bandit reward.

SOLID
-----
- SRP : action → reward → policy.update 흐름만 담당.
- DIP : RecommendPolicy / reward_aggregator 의 인터페이스에만 의존.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from src.recommend.policy import RecommendPolicy
from src.recommend.reward_aggregator import Action, reward_from_action

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class FeedbackResult:
    arm_id: str
    context_key: str
    reward: float


class FeedbackRecorder:
    """LangGraph 응답 이후 사용자가 보낸 implicit feedback 을 reward 로 변환."""

    def __init__(self, policy: RecommendPolicy) -> None:
        self._policy = policy

    def record(
        self,
        *,
        arm_id: str,
        context_key: str,
        action: Action,
        dwell_seconds: float = 0.0,
    ) -> FeedbackResult:
        reward = reward_from_action(action, dwell_seconds=dwell_seconds)
        if reward == 0.0:
            logger.debug(
                "Feedback skipped (no reward signal): arm=%s action=%s",
                arm_id,
                action,
            )
        self._policy.record_reward(
            arm_id=arm_id,
            context_key=context_key,
            reward=reward,
        )
        return FeedbackResult(arm_id=arm_id, context_key=context_key, reward=reward)


__all__ = ["FeedbackRecorder"]
