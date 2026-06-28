"""generate_reply 노드: 에이전트 응답 전달 + 언급 항목 추출.

agent AIMessage content 를 ``reply`` 로 사용하고, LLM 은 후보 목록에서
언급된 영화/피드 ID 추출(metadata)만 수행한다.

SOLID
-----
- SRP : agent content 정제·추출 LLM 호출·후보 필터링만 담당.
- DIP : 프롬프트/스키마는 ``ontology.prompts.reply`` 에 위임한다.
"""

from __future__ import annotations

import logging
from typing import Any

from langchain_core.messages import AIMessage, BaseMessage

from src.chat.cypher.sanitize import strip_reasoning_blocks
from src.chat.nodes.dependencies import ChatGraphDependencies
from src.chat.nodes.tools import resolve_retrieved_media
from src.chat.state import ChatState, IntentScope
from src.ontology.prompts.reply import ReplyScope, build_extraction_messages

logger = logging.getLogger(__name__)


def _resolve_scope(state: ChatState) -> IntentScope:
    scope = state.get("intent_scope")
    if scope in ("movie", "feed", "both", "none"):
        return scope
    media = state.get("media_type")
    if media in ("movie", "feed"):
        return media
    return "none"


def _message_text(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict):
                block_type = block.get("type")
                if block_type in ("text", "output_text"):
                    parts.append(str(block.get("text") or block.get("content") or ""))
        return "\n".join(part for part in parts if part)
    return str(content or "")


def _latest_agent_content(messages: list[BaseMessage]) -> str:
    for msg in reversed(messages):
        if not isinstance(msg, AIMessage) or msg.tool_calls:
            continue
        return strip_reasoning_blocks(_message_text(msg.content))
    return ""


def _empty_reply_fallback(state: ChatState) -> str:
    hint = str(state.get("direct_reply_hint") or "").strip()
    return hint or "안녕하세요! 영화나 감상 피드 추천이 필요하시면 말씀해 주세요."


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


def _metadata_from_rows(
    scope: IntentScope,
    movies: list[dict[str, Any]],
    feeds: list[dict[str, Any]],
) -> dict[str, Any] | None:
    result: dict[str, Any] = {}
    if scope in ("movie", "both"):
        movie_items = [
            {"type": "movie", "id": str(row["movie_id"])}
            for row in movies
            if row.get("movie_id")
        ]
        if movie_items:
            result["movie"] = movie_items
    if scope in ("feed", "both"):
        feed_items = [
            {"type": "feed", "id": str(row["feed_id"])}
            for row in feeds
            if row.get("feed_id")
        ]
        if feed_items:
            result["feed"] = feed_items
    return result or None


def _filter_by_ids(
    rows: list[dict[str, Any]],
    ids: set[str],
    id_key: str,
) -> list[dict[str, Any]]:
    if not ids:
        return []
    return [row for row in rows if str(row.get(id_key) or "") in ids]


def _ids_from_metadata(
    reply_metadata: dict[str, Any] | None,
    scope: IntentScope,
) -> tuple[set[str], set[str]]:
    movie_ids: set[str] = set()
    feed_ids: set[str] = set()
    if not reply_metadata:
        return movie_ids, feed_ids
    if scope in ("movie", "both"):
        for item in reply_metadata.get("movie") or []:
            if isinstance(item, dict) and item.get("id"):
                movie_ids.add(str(item["id"]))
    if scope in ("feed", "both"):
        for item in reply_metadata.get("feed") or []:
            if isinstance(item, dict) and item.get("id"):
                feed_ids.add(str(item["id"]))
    return movie_ids, feed_ids


def _should_extract(scope: IntentScope, movies: list[dict], feeds: list[dict]) -> bool:
    if scope == "none":
        return False
    if scope == "movie":
        return bool(movies)
    if scope == "feed":
        return bool(feeds)
    return bool(movies or feeds)


def build_structured_reply(state: ChatState, deps: ChatGraphDependencies) -> ChatState:
    """agent 응답을 ``reply`` 로 전달하고, LLM 으로 언급 항목을 추출한다."""
    scope: ReplyScope = _resolve_scope(state)
    messages = list(state.get("messages") or [])
    reply = _latest_agent_content(messages)
    if not reply:
        reply = _empty_reply_fallback(state)

    candidate_movies, candidate_feeds = resolve_retrieved_media(
        state, top_k=deps.default_top_k
    )
    filtered_movies = list(candidate_movies)
    filtered_feeds = list(candidate_feeds)
    reply_metadata: dict[str, Any] | None = None
    raw: dict[str, Any] = {}

    if _should_extract(scope, candidate_movies, candidate_feeds):
        chat_payload = build_extraction_messages(
            scope=scope,
            agent_content=reply,
            retrieved_movies=candidate_movies,
            retrieved_feeds=candidate_feeds,
        )
        print(chat_payload["messages"])
        try:
            raw = deps.llm.chat_json(
                chat_payload["messages"],
                response_format=chat_payload["response_format"],
                user_id=state.get("user_id"),
                max_tokens=deps.reply_max_tokens,
                temperature=deps.reply_temperature,
            )
            print(raw)
            reply_metadata = _normalize_metadata(raw, scope)
        except Exception:
            logger.exception("Reply metadata extraction failed; using full candidate pool.")

        if reply_metadata:
            movie_ids, feed_ids = _ids_from_metadata(reply_metadata, scope)
            if scope in ("movie", "both") and movie_ids:
                filtered_movies = _filter_by_ids(candidate_movies, movie_ids, "movie_id")
            if scope in ("feed", "both") and feed_ids:
                filtered_feeds = _filter_by_ids(candidate_feeds, feed_ids, "feed_id")

        if reply_metadata is None:
            reply_metadata = _metadata_from_rows(scope, filtered_movies, filtered_feeds)

    result: ChatState = {"reply": reply, "reply_metadata": reply_metadata}
    if filtered_movies:
        result["retrieved_movies"] = filtered_movies
    elif scope in ("movie", "both") and reply_metadata and reply_metadata.get("movie") == []:
        result["retrieved_movies"] = []
    if filtered_feeds:
        result["retrieved_feeds"] = filtered_feeds
    elif scope in ("feed", "both") and reply_metadata and reply_metadata.get("feed") == []:
        result["retrieved_feeds"] = []
    print(result)
    return result


__all__ = ["build_structured_reply"]
