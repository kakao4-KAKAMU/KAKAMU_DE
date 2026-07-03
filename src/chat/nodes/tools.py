"""ToolNode wrapper: Neo4j tool 실행 후 state 동기화."""

from __future__ import annotations

import json
import logging
from typing import Any

from langchain_core.messages import ToolMessage
from langgraph.prebuilt import ToolNode

from src.chat.nodes.dependencies import ChatGraphDependencies
from src.chat.state import ChatState

logger = logging.getLogger(__name__)

_MEDIA_ID_KEYS = frozenset({"movie_id", "feed_id"})
_ROW_WRAPPER_KEYS = ("row", "item", "record")
_NESTED_NODE_HINT_KEYS = frozenset({"movie_id", "feed_id", "title", "summary", "plot_raw"})


def _parse_tool_payload(content: str) -> dict[str, Any] | None:
    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        logger.warning("Tool returned non-JSON content: %s", content[:200])
        return None
    return data if isinstance(data, dict) else None


def _merge_scalar_fields(flat: dict[str, Any], row: dict[str, Any], *, skip_keys: set[str]) -> dict[str, Any]:
    for key, value in row.items():
        if key in skip_keys or key in flat or isinstance(value, (dict, list)):
            continue
        flat[key] = value
    return flat


def _flatten_neo4j_row(row: dict[str, Any]) -> dict[str, Any]:
    """Neo4j row를 movie/feed flat dict로 변환한다.

    지원 형태:
    - flat: ``{movie_id: ..., title: ...}``
    - wrapper: ``{row: {movie_id: ...}}`` (CALL { UNION ALL ... } RETURN row)
    - nested node: ``{m: {movie_id: ...}, score: 0.9}``
    """
    if _MEDIA_ID_KEYS & row.keys():
        return dict(row)

    for wrapper_key in _ROW_WRAPPER_KEYS:
        payload = row.get(wrapper_key)
        if isinstance(payload, dict) and (_MEDIA_ID_KEYS & payload.keys() or _NESTED_NODE_HINT_KEYS & payload.keys()):
            return _merge_scalar_fields(dict(payload), row, skip_keys={wrapper_key})

    for value in row.values():
        if not isinstance(value, dict):
            continue
        if _NESTED_NODE_HINT_KEYS & value.keys():
            return _merge_scalar_fields(dict(value), row, skip_keys=set())

    return dict(row)


def _rows_to_retrieved(rows: list[dict[str, Any]]) -> tuple[list[dict], list[dict]]:
    movies: list[dict[str, Any]] = []
    feeds: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        flat = _flatten_neo4j_row(row)
        movie_id = flat.get("movie_id")
        feed_id = flat.get("feed_id")
        if movie_id:
            movies.append(flat)
        if feed_id:
            feeds.append(flat)
    return movies, feeds


def _dedupe_rows(rows: list[dict[str, Any]], id_key: str) -> list[dict[str, Any]]:
    seen: set[str] = set()
    deduped: list[dict[str, Any]] = []
    for row in rows:
        row_id = row.get(id_key)
        if not row_id:
            continue
        key = str(row_id)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(row)
    return deduped


def resolve_retrieved_media(
    state: ChatState,
    *,
    top_k: int,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Neo4j tool 조회 결과를 reply 후보 목록으로 정규화한다."""
    movies = list(state.get("retrieved_movies") or [])
    feeds = list(state.get("retrieved_feeds") or [])
    if not movies and not feeds:
        for entry in state.get("graph_query_results") or []:
            if not isinstance(entry, dict):
                continue
            rows = entry.get("rows") or []
            if not isinstance(rows, list):
                continue
            new_movies, new_feeds = _rows_to_retrieved(rows)
            movies.extend(new_movies)
            feeds.extend(new_feeds)
    movies = _dedupe_rows(movies, "movie_id")[:top_k]
    feeds = _dedupe_rows(feeds, "feed_id")[:top_k]
    return movies, feeds


def merge_tool_results_into_state(
    tool_update: ChatState,
    prior: ChatState,
) -> ChatState:
    """ToolMessage JSON을 graph_query_results / retrieved_* 필드로 병합."""
    messages = tool_update.get("messages") or []
    accumulated = list(prior.get("graph_query_results") or [])
    movies = list(prior.get("retrieved_movies") or [])
    feeds = list(prior.get("retrieved_feeds") or [])

    for msg in messages:
        if not isinstance(msg, ToolMessage):
            continue
        payload = _parse_tool_payload(str(msg.content))
        if payload is None or payload.get("status") != "ok":
            continue
        rows = payload.get("rows") or []
        if not isinstance(rows, list):
            continue
        entry = {
            "cypher": payload.get("cypher", ""),
            "rows": rows,
        }
        accumulated.append(entry)
        new_movies, new_feeds = _rows_to_retrieved(rows)
        movies.extend(new_movies)
        feeds.extend(new_feeds)

    result: ChatState = dict(tool_update)
    if accumulated:
        result["graph_query_results"] = accumulated
    if movies:
        result["retrieved_movies"] = movies
    if feeds:
        result["retrieved_feeds"] = feeds

    intent_scope = 'none'
    if len(movies) > 0 and len(feeds) > 0:
        intent_scope = 'both'
    elif len(movies) > 0:
        intent_scope = 'movie'
    elif len(feeds) > 0:
        intent_scope = 'feed'
    result['intent_scope'] = intent_scope
    return result


def run_neo4j_tools(state: ChatState, deps: ChatGraphDependencies) -> ChatState:
    """langgraph.prebuilt.ToolNode 실행 + 조회 결과 state 동기화."""
    tool_node = ToolNode(deps.neo4j_tools)
    update = tool_node.invoke(state)
    return merge_tool_results_into_state(update, state)


__all__ = ["merge_tool_results_into_state", "resolve_retrieved_media", "run_neo4j_tools"]
