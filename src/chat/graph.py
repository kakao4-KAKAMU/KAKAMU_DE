"""LangGraph StateGraph 구성.

플로우::

    embed_query → analyze_query → agent
        ├─(tool_calls) → neo4j_tools → agent  (루프)
        └─(no tools)   → generate_reply → persist_history → END

``analyze_query`` 가 ``intent_scope`` 와 온톨로지 필터를 결정하고,
``agent`` 가 데이터 조회 필요 시 ``query_neo4j_graph`` tool을 호출한다.
tool 내부에서 Cypher 생성·검증(CypherQueryCorrector + CyVer) 후 read-only 실행.

SOLID
-----
- SRP : 본 모듈은 노드를 엮는 책임만 가진다.
- OCP : 새 노드/매체를 추가하려면 nodes 패키지에 함수를 추가하고 본 모듈에서 edge 연결.
"""

from __future__ import annotations

from typing import Optional

from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import tools_condition

from src.chat.nodes import (
    ChatGraphDependencies,
    analyze_query,
    call_agent,
    embed_query,
    generate_reply,
    persist_history,
    run_neo4j_tools,
)
from src.chat.state import ChatState

_AGENT_RECURSION_LIMIT = 15


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
    graph.add_node("agent", lambda s: call_agent(s, deps))
    graph.add_node("neo4j_tools", lambda s: run_neo4j_tools(s, deps))
    graph.add_node("generate_reply", lambda s: generate_reply(s, deps))
    graph.add_node("persist_history", lambda s: persist_history(s, deps))

    graph.add_edge(START, "embed_query")
    graph.add_edge("embed_query", "analyze_query")
    graph.add_edge("analyze_query", "agent")

    graph.add_conditional_edges(
        "agent",
        tools_condition,
        {"tools": "neo4j_tools", END: "generate_reply"},
    )
    graph.add_edge("neo4j_tools", "agent")
    graph.add_edge("generate_reply", "persist_history")
    graph.add_edge("persist_history", END)

    compile_kwargs: dict = {}
    if checkpointer is not None:
        compile_kwargs["checkpointer"] = checkpointer
    return graph.compile(**compile_kwargs)


__all__ = ["ChatGraphDependencies", "build_chat_graph", "AGENT_RECURSION_LIMIT"]

AGENT_RECURSION_LIMIT = _AGENT_RECURSION_LIMIT
