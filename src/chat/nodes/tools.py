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


def _parse_tool_payload(content: str) -> dict[str, Any] | None:
    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        logger.warning("Tool returned non-JSON content: %s", content[:200])
        return None
    return data if isinstance(data, dict) else None


def _rows_to_retrieved(rows: list[dict[str, Any]]) -> tuple[list[dict], list[dict]]:
    movies: list[dict[str, Any]] = []
    feeds: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        if "movie_id" in row:
            movies.append(dict(row))
        if "feed_id" in row:
            feeds.append(dict(row))
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
    return result


def run_neo4j_tools(state: ChatState, deps: ChatGraphDependencies) -> ChatState:
    """langgraph.prebuilt.ToolNode 실행 + 조회 결과 state 동기화."""
    tool_node = ToolNode(deps.neo4j_tools)
    update = tool_node.invoke(state)
    return merge_tool_results_into_state(update, state)


__all__ = ["merge_tool_results_into_state", "run_neo4j_tools"]
