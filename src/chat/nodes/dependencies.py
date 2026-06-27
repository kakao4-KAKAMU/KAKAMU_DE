"""LangGraph 노드가 사용하는 외부 IO 의존성 컨테이너.

SOLID
-----
- SRP : 노드 실행에 필요한 협력 객체/설정의 보관만 담당.
- DIP : 외부 IO 는 생성 시 주입된다.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from langchain_core.language_models import BaseChatModel
from langchain_core.tools import BaseTool

from src.chat.cypher.service import Neo4jCypherService
from src.embedding.vllm_embedding import VLLMEmbeddingClient
from src.llm.vllm_client import VLLMChatClient
from src.persistence.chat_history import ChatHistoryStore


@dataclass
class ChatGraphDependencies:
    """LangGraph 노드가 사용하는 외부 IO 컨테이너."""

    embedder: VLLMEmbeddingClient
    llm: VLLMChatClient
    agent_llm: BaseChatModel
    neo4j_tools: list[BaseTool]
    cypher_service: Optional[Neo4jCypherService] = None
    history: Optional[ChatHistoryStore] = None
    default_top_k: int = 20
    reply_max_tokens: int = 512
    reply_temperature: float = 0.6
    extra_user_payload: dict[str, Any] = field(default_factory=dict)


__all__ = ["ChatGraphDependencies"]
