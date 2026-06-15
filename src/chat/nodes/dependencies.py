"""LangGraph 노드가 사용하는 외부 IO 의존성 컨테이너.

SOLID
-----
- SRP : 노드 실행에 필요한 협력 객체/설정의 보관만 담당.
- DIP : 모든 외부 IO 는 Protocol 타입으로 주입된다.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from src.chat.nodes.protocols import (
    ChatLLMLike,
    EmbedderLike,
    MediaClassifierLike,
)
from src.graph.template_executor import TemplateExecutor
from src.persistence.chat_history import ChatHistoryStore
from src.recommend.intent_resolver import IntentResolver
from src.recommend.media_classifier import LLMMediaClassifier
from src.recommend.policy import RecommendPolicy

DEFAULT_MOVIE_TEMPLATE_ID = "hybrid_recommend"
DEFAULT_FEED_TEMPLATE_ID = "hybrid_feed_recommend"

# retrieve 노드의 기본 하이브리드 가중치 (arm 미선택 시 fallback).
DEFAULT_WEIGHTS: dict[str, float] = {
    "w_vec": 0.55,
    "w_kw": 0.15,
    "w_theme": 0.10,
    "w_mood": 0.05,
    "w_user": 0.15,
}


@dataclass
class ChatGraphDependencies:
    """LangGraph 노드가 사용하는 외부 IO 컨테이너."""

    embedder: EmbedderLike
    intent_resolver: IntentResolver
    policy: RecommendPolicy
    template_executor: TemplateExecutor
    llm: ChatLLMLike
    history: Optional[ChatHistoryStore] = None
    media_classifier: Optional[MediaClassifierLike] = None
    default_top_k: int = 10
    default_vec_top_k: int = 30
    default_max_toxicity: float = 0.7
    movie_template_id: str = DEFAULT_MOVIE_TEMPLATE_ID
    feed_template_id: str = DEFAULT_FEED_TEMPLATE_ID
    reply_max_tokens: int = 512
    reply_temperature: float = 0.4
    extra_user_payload: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        # 미지정 시 주입된 LLM 으로 LLM 기반 분류기를 구성한다.
        if self.media_classifier is None:
            self.media_classifier = LLMMediaClassifier(self.llm)


__all__ = [
    "ChatGraphDependencies",
    "DEFAULT_MOVIE_TEMPLATE_ID",
    "DEFAULT_FEED_TEMPLATE_ID",
    "DEFAULT_WEIGHTS",
]
