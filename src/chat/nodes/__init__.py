"""LangGraph 노드 패키지 (순수 함수 + 의존성 컨테이너).

각 노드는 ``(state, deps) -> partial ChatState`` 시그니처로 작성되어
LangGraph 의 closure 와 단위 테스트 모두에서 재사용 가능하다.

모듈 구성 (SRP 단위 분리)
------------------------
- ``dependencies`` : ``ChatGraphDependencies`` 의존성 컨테이너.
- ``embedding``    : ``embed_query``.
- ``agent``        : ``call_agent``.
- ``tools``        : ``run_neo4j_tools``.
- ``reply``        : ``build_structured_reply``.
- ``persistence``  : ``persist_history``.

SOLID
-----
- SRP : 각 노드 모듈은 단일 책임만 수행.
- DIP : 외부 IO 는 모두 ``ChatGraphDependencies`` 로 주입.
"""

from __future__ import annotations

from src.chat.nodes.agent import build_agent_llm, call_agent
from src.chat.nodes.dependencies import ChatGraphDependencies
from src.chat.nodes.embedding import embed_query
from src.chat.nodes.persistence import persist_history
from src.chat.nodes.reply import build_structured_reply, generate_reply
from src.chat.nodes.tools import merge_tool_results_into_state, run_neo4j_tools

__all__ = [
    "ChatGraphDependencies",
    "build_agent_llm",
    "build_structured_reply",
    "call_agent",
    "embed_query",
    "generate_reply",
    "merge_tool_results_into_state",
    "persist_history",
    "run_neo4j_tools",
]
