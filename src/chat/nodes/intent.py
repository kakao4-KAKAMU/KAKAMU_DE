"""plan_intent 노드: 질의 → 정규화된 (keywords, themes, moods)."""

from __future__ import annotations

from src.chat.nodes.dependencies import ChatGraphDependencies
from src.chat.state import ChatState
from src.recommend.intent_resolver import ResolvedIntent


def plan_intent(state: ChatState, deps: ChatGraphDependencies) -> ChatState:
    query = state.get("query", "")
    intent: ResolvedIntent = deps.intent_resolver.resolve(query)
    return {
        "keywords": list(intent.keywords),
        "themes": list(intent.themes),
        "moods": list(intent.moods),
    }


__all__ = ["plan_intent"]
