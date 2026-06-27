"""LangGraph 노드 패키지 (순수 함수 + 의존성 컨테이너).

각 노드는 ``(state, deps) -> partial ChatState`` 시그니처로 작성되어
LangGraph 의 closure 와 단위 테스트 모두에서 재사용 가능하다.

모듈 구성 (SRP 단위 분리)
------------------------
- ``protocols``    : 노드가 의존하는 최소 인터페이스(Protocol).
- ``dependencies`` : ``ChatGraphDependencies`` 의존성 컨테이너 + 기본값.
- ``embedding``    : ``embed_query``.
- ``intent``       : ``analyze_query``.
- ``media``        : ``route_after_analysis`` (conditional_edges).
- ``retrieval``    : ``filter_movies`` / ``filter_feeds`` / ``filter_both``.
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
from src.chat.nodes.agent import build_agent_llm, call_agent
from src.chat.nodes.embedding import embed_query
from src.chat.nodes.intent import analyze_query, plan_intent
from src.chat.nodes.media import route_after_analysis, route_media
from src.chat.nodes.persistence import persist_history
from src.chat.nodes.protocols import (
    ChatLLMLike,
    EmbedderLike,
    MediaClassifierLike,
)
from src.chat.nodes.reply import build_structured_reply, generate_reply
from src.chat.nodes.retrieval import (
    filter_both,
    filter_feeds,
    filter_movies,
    retrieve_feeds,
    retrieve_movies,
)
from src.chat.nodes.tools import merge_tool_results_into_state, run_neo4j_tools
from src.chat.nodes.weights import select_weights

__all__ = [
    "ChatGraphDependencies",
    "ChatLLMLike",
    "EmbedderLike",
    "MediaClassifierLike",
    "DEFAULT_FEED_TEMPLATE_ID",
    "DEFAULT_MOVIE_TEMPLATE_ID",
    "DEFAULT_WEIGHTS",
    "analyze_query",
    "build_structured_reply",
    "build_agent_llm",
    "call_agent",
    "embed_query",
    "filter_both",
    "filter_feeds",
    "filter_movies",
    "generate_reply",
    "merge_tool_results_into_state",
    "persist_history",
    "plan_intent",
    "retrieve_feeds",
    "retrieve_movies",
    "route_after_analysis",
    "route_media",
    "run_neo4j_tools",
    "select_weights",
]
