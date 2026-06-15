"""embed_query 노드: 질의 임베딩 생성."""

from __future__ import annotations

from src.chat.nodes.dependencies import ChatGraphDependencies
from src.chat.state import ChatState


def embed_query(state: ChatState, deps: ChatGraphDependencies) -> ChatState:
    query = state.get("query", "")
    if not query:
        raise ValueError("ChatState.query is required")
    embedding = deps.embedder.embed(query)
    return {"query_embedding": list(embedding)}


__all__ = ["embed_query"]
