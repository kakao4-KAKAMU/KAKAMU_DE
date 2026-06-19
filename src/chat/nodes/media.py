"""추천 매체(영화 / 피드) 분류 노드 + conditional_edges 라우팅 함수.

SOLID
-----
- SRP : ``classify_media`` 는 매체 결정만, ``route_media`` 는 분기 키 반환만 담당.
- OCP : 새 매체가 추가되면 분류기(``LLMMediaClassifier``)와 라우팅 맵만 확장한다.
"""

from __future__ import annotations

from src.chat.nodes.dependencies import ChatGraphDependencies
from src.chat.state import ChatState, MediaType


def classify_media(state: ChatState, deps: ChatGraphDependencies) -> ChatState:
    """질의로부터 추천 매체 타입을 결정해 상태에 기록한다.

    이미 ``media_type`` 이 지정되어 있으면(상위 레이어가 강제한 경우) 그대로 존중한다.
    """
    existing = state.get("media_type")
    if existing in ("movie", "feed"):
        return {"media_type": existing}
    media: MediaType = deps.media_classifier.classify(state.get("query", ""))
    return {"media_type": media}


def route_media(state: ChatState) -> MediaType:
    """conditional_edges 용 라우팅 함수: 다음 노드를 결정하는 키를 반환."""
    media = state.get("media_type")
    return media if media in ("movie", "feed") else "movie"


__all__ = ["classify_media", "route_media"]
