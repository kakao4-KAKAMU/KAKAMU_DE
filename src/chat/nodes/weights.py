"""select_weights 노드: bandit arm 선택 → 하이브리드 가중치 결정."""

from __future__ import annotations

from src.chat.nodes.dependencies import ChatGraphDependencies
from src.chat.state import ChatState
from src.recommend.context import bandit_context_key


def select_weights(state: ChatState, deps: ChatGraphDependencies) -> ChatState:
    user_id = state.get("user_id", "anonymous")
    context_key = bandit_context_key(user_id, state.get("persona_id"))
    arm = deps.policy.select_arm(context_key=context_key)
    return {"arm_id": arm.arm_id, "weights": dict(arm.weights)}


__all__ = ["select_weights"]
