"""LangGraph 채팅 상태 정의.

SOLID
-----
- SRP : 상태 스키마만 정의. 노드 구현/의존성은 graph.py 와 분리.
- ISP : LangGraph 가 TypedDict 의 부분 갱신을 자유롭게 머지하도록 모든 키를 NotRequired.
"""

from __future__ import annotations

from typing import Any, Literal, Optional, TypedDict


MediaType = Literal["movie", "feed"]


class ChatMetadata(TypedDict, total=False):
    type: MediaType
    id: str

class ChatState(TypedDict, total=False):
    """LangGraph 노드 간 공유 상태.

    각 노드는 필요한 키만 갱신해서 partial dict 를 반환한다.
    """

    user_id: str
    persona_id: str
    session_id: str
    query: str

    query_embedding: list[float]
    keywords: list[str]
    themes: list[str]
    moods: list[str]

    media_type: MediaType

    arm_id: str
    weights: dict[str, float]
    top_k: int
    vec_top_k: int
    max_toxicity: float

    retrieved: list[dict[str, Any]]
    reply: str

    reply_metadata: Optional[ChatMetadata]

    ontology_ref: dict[str, Any]


__all__ = ["ChatState", "ChatMetadata", "MediaType"]
