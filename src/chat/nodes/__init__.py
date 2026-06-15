"""LangGraph 노드 패키지 (순수 함수 + 의존성 컨테이너).

각 노드는 ``(state, deps) -> partial ChatState`` 시그니처로 작성되어
LangGraph 의 closure 와 단위 테스트 모두에서 재사용 가능하다.

모듈 구성 (SRP 단위 분리)
------------------------
- ``protocols``    : 노드가 의존하는 최소 인터페이스(Protocol).
- ``dependencies`` : ``ChatGraphDependencies`` 의존성 컨테이너 + 기본값.
- ``embedding``    : ``embed_query``.
- ``intent``       : ``plan_intent``.
- ``media``        : ``classify_media`` + ``route_media`` (conditional_edges).
- ``weights``      : ``select_weights``.
- ``retrieval``    : ``retrieve_movies`` / ``retrieve_feeds``.
- ``reply``        : ``generate_reply``.
- ``persistence``  : ``persist_history``.

SOLID
-----
- SRP : 각 노드 모듈은 단일 책임만 수행.
- DIP : 외부 IO 는 모두 ``ChatGraphDependencies`` 로 주입.
"""

from __future__ import annotations

from src.chat.nodes.dependencies import (
    DEFAULT_FEED_TEMPLATE_ID,
    DEFAULT_MOVIE_TEMPLATE_ID,
    DEFAULT_WEIGHTS,
    ChatGraphDependencies,
)
from src.chat.nodes.embedding import embed_query
from src.chat.nodes.intent import plan_intent
from src.chat.nodes.media import classify_media, route_media
from src.chat.nodes.persistence import persist_history
from src.chat.nodes.protocols import (
    ChatLLMLike,
    EmbedderLike,
    MediaClassifierLike,
)
from src.chat.nodes.reply import generate_reply
from src.chat.nodes.retrieval import retrieve_feeds, retrieve_movies
from src.chat.nodes.weights import select_weights

__all__ = [
    "ChatGraphDependencies",
    "ChatLLMLike",
    "EmbedderLike",
    "MediaClassifierLike",
    "DEFAULT_FEED_TEMPLATE_ID",
    "DEFAULT_MOVIE_TEMPLATE_ID",
    "DEFAULT_WEIGHTS",
    "classify_media",
    "embed_query",
    "generate_reply",
    "persist_history",
    "plan_intent",
    "retrieve_feeds",
    "retrieve_movies",
    "route_media",
    "select_weights",
]
