"""SSE node 이벤트 환경별 필터링."""

from __future__ import annotations

from typing import Any, Literal

from src.api.routers.chat.utils import jsonify

SseNodeMode = Literal["full", "filtered"]

_SAFE_PERSIST_KEYS = frozenset({"reply", "reply_metadata"})
_SUMMARY_NODES = frozenset({"embed_query", "agent", "neo4j_tools"})


def sse_node_mode(env: str) -> SseNodeMode:
    """local/dev 는 전체 state, stg/prod 는 최소 필드만 노출."""
    if env in ("local", "dev"):
        return "full"
    return "filtered"


def public_error_detail(env: str, exc: Exception) -> str:
    if env in ("local", "dev"):
        return str(exc)
    return "An internal error occurred"


def filter_sse_node_chunk(chunk: dict[str, Any]) -> dict[str, Any]:
    """prod/stg 용 node chunk — reply·메타만 노출, Cypher/내부 state 제거."""
    filtered: dict[str, Any] = {}
    for node_name, update in chunk.items():
        if not isinstance(update, dict):
            filtered[node_name] = {"status": "ok"}
            continue

        if node_name == "persist_history":
            filtered[node_name] = {
                key: jsonify(update[key])
                for key in _SAFE_PERSIST_KEYS
                if key in update
            }
            continue

        if node_name in _SUMMARY_NODES:
            summary: dict[str, Any] = {"status": "ok"}
            movies = update.get("retrieved_movies")
            feeds = update.get("retrieved_feeds")
            if isinstance(movies, list):
                summary["movie_count"] = len(movies)
            if isinstance(feeds, list):
                summary["feed_count"] = len(feeds)
            filtered[node_name] = summary
            continue

        filtered[node_name] = {"status": "ok"}
    return filtered


__all__ = ["filter_sse_node_chunk", "public_error_detail", "sse_node_mode"]
