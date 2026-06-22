"""LangGraph StateGraph 구성.

플로우::

    embed_query → analyze_query → route_after_analysis
        ├─(none)  → generate_reply → persist_history → END
        ├─(movie) → filter_movies → generate_reply → persist_history → END
        ├─(feed)  → filter_feeds  → generate_reply → persist_history → END
        └─(both)  → filter_both   → generate_reply → persist_history → END

``analyze_query`` 가 ``intent_scope`` 를 결정하고 ``route_after_analysis`` 가
영화/피드/둘 다/없음 경로로 분기한다.

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
    analyze_query,
    embed_query,
    filter_both,
    filter_feeds,
    filter_movies,
    generate_reply,
    persist_history,
    route_after_analysis,
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
    graph.add_node("analyze_query", lambda s: analyze_query(s, deps))
    graph.add_node("filter_movies", lambda s: filter_movies(s, deps))
    graph.add_node("filter_feeds", lambda s: filter_feeds(s, deps))
    graph.add_node("filter_both", lambda s: filter_both(s, deps))
    graph.add_node("generate_reply", lambda s: generate_reply(s, deps))
    graph.add_node("persist_history", lambda s: persist_history(s, deps))

    graph.add_edge(START, "embed_query")
    graph.add_edge("embed_query", "analyze_query")

    graph.add_conditional_edges(
        "analyze_query",
        route_after_analysis,
        {
            "none": "generate_reply",
            "movie": "filter_movies",
            "feed": "filter_feeds",
            "both": "filter_both",
        },
    )

    graph.add_edge("filter_movies", "generate_reply")
    graph.add_edge("filter_feeds", "generate_reply")
    graph.add_edge("filter_both", "generate_reply")
    graph.add_edge("generate_reply", "persist_history")
    graph.add_edge("persist_history", END)

    if checkpointer is not None:
        return graph.compile(checkpointer=checkpointer)
    return graph.compile()


__all__ = ["ChatGraphDependencies", "build_chat_graph"]
