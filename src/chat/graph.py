"""LangGraph StateGraph 구성.

플로우::

    embed_query → plan_intent → select_weights → retrieve_movies →
    generate_reply → persist_history → END

SOLID
-----
- SRP : 본 모듈은 노드를 엮는 책임만 가진다.
- OCP : 새 노드를 추가하려면 nodes.py 에 함수를 추가하고 본 모듈에서 edge 연결.
"""

from __future__ import annotations

from typing import Optional

from langgraph.graph import END, START, StateGraph

from src.chat.nodes import (
    ChatGraphDependencies,
    embed_query,
    generate_reply,
    persist_history,
    plan_intent,
    retrieve_movies,
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
    graph.add_node("select_weights", lambda s: select_weights(s, deps))
    graph.add_node("retrieve_movies", lambda s: retrieve_movies(s, deps))
    graph.add_node("generate_reply", lambda s: generate_reply(s, deps))
    graph.add_node("persist_history", lambda s: persist_history(s, deps))

    graph.add_edge(START, "embed_query")
    graph.add_edge("embed_query", "plan_intent")
    graph.add_edge("plan_intent", "select_weights")
    graph.add_edge("select_weights", "retrieve_movies")
    graph.add_edge("retrieve_movies", "generate_reply")
    graph.add_edge("generate_reply", "persist_history")
    graph.add_edge("persist_history", END)

    if checkpointer is not None:
        return graph.compile(checkpointer=checkpointer)
    return graph.compile()


__all__ = ["ChatGraphDependencies", "build_chat_graph"]
