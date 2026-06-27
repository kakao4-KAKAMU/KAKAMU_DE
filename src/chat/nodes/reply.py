"""generate_reply 노드: 분석·필터링 결과를 근거로 한국어 답변 생성.

intent_scope 에 따라 프롬프트·응답 스키마를 분기한다.

SOLID
-----
- SRP : LLM 호출과 응답 정규화/폴백만 담당.
- DIP : 프롬프트/스키마는 ``ontology.prompts.reply`` 에 위임한다.
"""

from __future__ import annotations

import logging
from typing import Any

from src.chat.nodes.dependencies import ChatGraphDependencies
from src.chat.state import ChatState, IntentScope
from src.ontology.prompts.reply import ReplyScope, build_reply_messages

logger = logging.getLogger(__name__)


def _resolve_scope(state: ChatState) -> IntentScope:
    scope = state.get("intent_scope")
    if scope in ("movie", "feed", "both", "none"):
        return scope
    media = state.get("media_type")
    if media in ("movie", "feed"):
        return media
    return "none"


def _build_payload(state: ChatState, deps: ChatGraphDependencies, scope: IntentScope) -> dict[str, Any]:
    user_query = state.get("query", "")
    top_k = deps.default_top_k
    if scope == "none":
        return {
            "query": user_query,
            "intent_scope": scope,
            "direct_reply_hint": state.get("direct_reply_hint") or "",
            "graph_query_results": state.get("graph_query_results") or [],
            **deps.extra_user_payload,
        }
    payload: dict[str, Any] = {}
    if scope == "movie" or scope == "both":
        payload["movie_filters"] = state.get("movie_filters") or {}
        payload["movie_candidates"] = (state.get("retrieved_movies") or [])[:top_k]
    if scope == "feed" or scope == "both":
        payload["feed_filters"] = state.get("feed_filters") or {}
        payload["feed_candidates"] = (state.get("retrieved_feeds") or [])[:top_k]
    graph_results = state.get("graph_query_results") or []
    if graph_results:
        payload["graph_query_results"] = graph_results
    return {
        "query": user_query,
        "intent_scope": scope,
        **payload,
        **deps.extra_user_payload,
    }


def _normalize_entry(value: Any, media: str) -> dict[str, Any] | None:
    if not isinstance(value, dict) or not value.get("id"):
        return None
    entry_type = value.get("type")
    if entry_type in ("movie", "feed"):
        return {"type": entry_type, "id": str(value["id"])}
    return {"type": media, "id": str(value["id"])}


def _normalize_entry_list(value: Any, media: str) -> list[dict[str, Any]]:
    if isinstance(value, list):
        return [
            entry
            for item in value
            if (entry := _normalize_entry(item, media)) is not None
        ]
    entry = _normalize_entry(value, media)
    return [entry] if entry else []


def _normalize_metadata(raw: dict[str, Any], scope: IntentScope) -> dict[str, Any] | None:
    metadata = raw.get("metadata")
    if not isinstance(metadata, dict):
        return None
    if scope in ("movie", "feed") and metadata.get("type") in ("movie", "feed"):
        items = _normalize_entry_list(metadata, scope)
        return {scope: items} if items else None

    result: dict[str, Any] = {}
    if scope in ("movie", "both"):
        movie_items = _normalize_entry_list(metadata.get("movie"), "movie")
        if movie_items:
            result["movie"] = movie_items
    if scope in ("feed", "both"):
        feed_items = _normalize_entry_list(metadata.get("feed"), "feed")
        if feed_items:
            result["feed"] = feed_items
    return result or None


def _fallback_metadata(
    scope: IntentScope, state: ChatState, top_k: int
) -> dict[str, Any] | None:
    result: dict[str, Any] = {}
    if scope in ("movie", "both"):
        movie_items = [
            {"type": "movie", "id": str(row["movie_id"])}
            for row in (state.get("retrieved_movies") or [])[:top_k]
            if row.get("movie_id")
        ]
        if movie_items:
            result["movie"] = movie_items
    if scope in ("feed", "both"):
        feed_items = [
            {"type": "feed", "id": str(row["feed_id"])}
            for row in (state.get("retrieved_feeds") or [])[:top_k]
            if row.get("feed_id")
        ]
        if feed_items:
            result["feed"] = feed_items
    return result or None


def build_structured_reply(state: ChatState, deps: ChatGraphDependencies) -> ChatState:
    """조회 결과를 바탕으로 ``reply`` / ``reply_metadata`` 를 생성한다."""
    scope: ReplyScope = _resolve_scope(state)
    payload = _build_payload(state, deps, scope)
    chat_payload = build_reply_messages(scope=scope, payload=payload)
    raw: dict[str, Any] = {}
    try:
        raw = deps.llm.chat_json(
            chat_payload["messages"],
            response_format=chat_payload["response_format"],
            user_id=state.get("user_id"),
            max_tokens=deps.reply_max_tokens,
            temperature=deps.reply_temperature,
        )
        reply = str(raw.get("reply") or "").strip()
    except Exception:
        logger.exception("Reply generation failed; falling back to deterministic answer.")
        reply = _fallback_reply(scope, state)
    if not reply:
        reply = _fallback_reply(scope, state)
    reply_metadata = _normalize_metadata(raw, scope)
    if reply_metadata is None and scope != "none":
        reply_metadata = _fallback_metadata(scope, state, deps.default_top_k)
    return {"reply": reply, "reply_metadata": reply_metadata}


def _fallback_reply(scope: IntentScope, state: ChatState) -> str:
    if scope == "none":
        hint = str(state.get("direct_reply_hint") or "").strip()
        return hint or "안녕하세요! 영화나 감상 피드 추천이 필요하시면 말씀해 주세요."
    if scope == "both":
        movies = state.get("retrieved_movies") or []
        feeds = state.get("retrieved_feeds") or []
        if not movies and not feeds:
            return "조건에 맞는 추천을 찾지 못했어요. 다른 키워드를 시도해 보세요."
        movie_titles = ", ".join(
            str(r.get("title") or r.get("movie_id")) for r in movies[:2]
        )
        feed_snippets = ", ".join(
            str(r.get("summary") or r.get("feed_id")) for r in feeds[:2]
        )
        return f"영화 추천: {movie_titles or '없음'}. 피드 추천: {feed_snippets or '없음'}."
    if scope == "feed":
        feeds = state.get("retrieved_feeds") or []
        if not feeds:
            return "조건에 맞는 추천을 찾지 못했어요. 다른 키워드를 시도해 보세요."
        snippets = ", ".join(
            str(r.get("summary") or r.get("feed_id")) for r in feeds[:3]
        )
        return f"이런 감상 피드를 추천드려요: {snippets}."
    movies = state.get("retrieved_movies") or []
    if not movies:
        return "조건에 맞는 추천을 찾지 못했어요. 다른 키워드를 시도해 보세요."
    titles = ", ".join(str(r.get("title") or r.get("movie_id")) for r in movies[:3])
    return f"이런 영화를 추천드려요: {titles}."


__all__ = ["build_structured_reply"]
