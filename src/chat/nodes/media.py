"""질의 분석 결과 기반 conditional_edges 라우팅.

SOLID
-----
- SRP : ``route_after_analysis`` 는 분기 키 반환만 담당.
- OCP : 새 intent_scope 가 추가되면 라우팅 맵만 확장한다.
"""

from __future__ import annotations

from src.chat.state import ChatState, IntentScope


def route_after_analysis(state: ChatState) -> IntentScope:
    """conditional_edges 용 라우팅: intent_scope 에 따라 다음 노드를 결정."""
    scope = state.get("intent_scope")
    if scope in ("movie", "feed", "both", "none"):
        return scope
    return "none"


# 하위 호환
def route_media(state: ChatState) -> str:
    media = state.get("media_type")
    if media in ("movie", "feed"):
        return media
    return "movie"


__all__ = ["route_after_analysis", "route_media"]
