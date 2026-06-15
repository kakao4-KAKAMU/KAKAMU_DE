"""LangGraph StateGraph 구성.

플로우::

    embed_query → plan_intent → classify_media → select_weights →
        ├─(movie)→ retrieve_movies ┐
        └─(feed) → retrieve_feeds  ┘
    → generate_reply → persist_history → END

``classify_media`` 가 결정한 ``media_type`` 을 ``route_media`` conditional_edges
가 읽어 영화/피드 추천 경로로 분기한다.

SOLID
-----
- SRP : 본 모듈은 노드를 엮는 책임만 가진다.
- OCP : 새 노드/매체를 추가하려면 nodes 패키지에 함수를 추가하고 본 모듈에서 edge 연결.
"""

from __future__ import annotations

from typing import Optional

from langgraph.graph import END, START, StateGraph

from src.chat.nodes import (
    ChatGraphDependencies,
    classify_media,
    embed_query,
    generate_reply,
    persist_history,
    plan_intent,
    retrieve_feeds,
    retrieve_movies,
    route_media,
    select_weights,
)
from src.chat.state import ChatState


def build_chat_graph(
    deps: ChatGraphDependencies,
    *,
    checkpointer: Optional[object] = None,
):
    """LangGraph CompiledGraph 빌더.

    Args:
        deps: 노드들이 사용할 외부 IO 컨테이너.
        checkpointer: ``langgraph-checkpoint-postgres`` 의 ``PostgresSaver`` 인스턴스.
            ``None`` 이면 in-memory 동작.
    """

    graph = StateGraph(ChatState)

    graph.add_node("embed_query", lambda s: embed_query(s, deps))
    graph.add_node("plan_intent", lambda s: plan_intent(s, deps))
    graph.add_node("classify_media", lambda s: classify_media(s, deps))
    graph.add_node("select_weights", lambda s: select_weights(s, deps))
    graph.add_node("retrieve_movies", lambda s: retrieve_movies(s, deps))
    graph.add_node("retrieve_feeds", lambda s: retrieve_feeds(s, deps))
    graph.add_node("generate_reply", lambda s: generate_reply(s, deps))
    graph.add_node("persist_history", lambda s: persist_history(s, deps))

    graph.add_edge(START, "embed_query")
    graph.add_edge("embed_query", "plan_intent")
    graph.add_edge("plan_intent", "classify_media")
    graph.add_edge("classify_media", "select_weights")

    # 추천 매체(영화 / 피드)에 따라 retrieve 노드를 분기한다.
    graph.add_conditional_edges(
        "select_weights",
        route_media,
        {
            "movie": "retrieve_movies",
            "feed": "retrieve_feeds",
        },
    )

    graph.add_edge("retrieve_movies", "generate_reply")
    graph.add_edge("retrieve_feeds", "generate_reply")
    graph.add_edge("generate_reply", "persist_history")
    graph.add_edge("persist_history", END)

    if checkpointer is not None:
        return graph.compile(checkpointer=checkpointer)
    return graph.compile()


__all__ = ["ChatGraphDependencies", "build_chat_graph"]
