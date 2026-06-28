"""Backward-compatible re-export. Prefer ``src.config.limits``."""

from __future__ import annotations

from src.config.limits import (
    DEFAULT_MAX_CHAT_MESSAGE_LENGTH,
    DEFAULT_MAX_CYPHER_QUESTION_LENGTH,
    DEFAULT_MAX_INGEST_CONTENT_LENGTH,
    DEFAULT_MAX_RECOMMEND_QUERY_LENGTH,
)

__all__ = [
    "DEFAULT_MAX_CHAT_MESSAGE_LENGTH",
    "DEFAULT_MAX_RECOMMEND_QUERY_LENGTH",
    "DEFAULT_MAX_INGEST_CONTENT_LENGTH",
    "DEFAULT_MAX_CYPHER_QUESTION_LENGTH",
]
