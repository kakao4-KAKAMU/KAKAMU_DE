"""generate_reply 노드: 추천 후보를 근거로 한국어 답변 생성.

매체(영화 / 피드)에 따라 시스템 프롬프트와 응답 스키마를 분기한다.

SOLID
-----
- SRP : LLM 호출과 응답 정규화/폴백만 담당.
- OCP : 매체별 프롬프트/스키마를 ``_REPLY_PROFILES`` 에 등록해 확장한다.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from textwrap import dedent
from typing import Any

from src.chat.nodes.dependencies import ChatGraphDependencies
from src.chat.state import ChatState, MediaType

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class _ReplyProfile:
    system_prompt: str
    response_format: dict[str, Any]


def _response_format(name: str, media: MediaType) -> dict[str, Any]:
    return {
        "type": "json_schema",
        "json_schema": {
            "name": name,
            "strict": True,
            "schema": {
                "type": "object",
                "properties": {
                    "reply": {"type": "string"},
                    "metadata": {
                        "type": "object",
                        "properties": {
                            "type": {"type": "string", "enum": [media]},
                            "id": {"type": "string"},
                        },
                    },
                },
            },
        },
    }


_MOVIE_PROFILE = _ReplyProfile(
    system_prompt=dedent(
        """
        너는 한국어 영화 추천 도우미다.
        아래 추천 후보 목록(JSON)을 근거로 사용자의 요청에 1~3 문장으로 답하라.
        추천된 영화가 없다면 다른 키워드를 제시하라.
        출력은 단일 JSON 객체: {"reply": "문장", "metadata": { "type": "movie", "id": "<영화 ID>" }}.
        metadata 는 추천 결과의 타입과 ID를 나타낸다.
        """
    ).strip(),
    response_format=_response_format("reply_movie_ontology", "movie"),
)

_FEED_PROFILE = _ReplyProfile(
    system_prompt=dedent(
        """
        너는 한국어 영화 감상 피드 추천 도우미다.
        아래 추천 피드 후보 목록(JSON)을 근거로 사용자의 요청에 1~3 문장으로 답하라.
        추천된 피드가 없다면 다른 키워드를 제시하라.
        출력은 단일 JSON 객체: {"reply": "문장", "metadata": { "type": "feed", "id": "<피드 ID>" }}.
        metadata 는 추천 결과의 타입과 ID를 나타낸다.
        """
    ).strip(),
    response_format=_response_format("reply_feed_ontology", "feed"),
)

_REPLY_PROFILES: dict[MediaType, _ReplyProfile] = {
    "movie": _MOVIE_PROFILE,
    "feed": _FEED_PROFILE,
}


def generate_reply(state: ChatState, deps: ChatGraphDependencies) -> ChatState:
    media: MediaType = state.get("media_type") or "movie"
    profile = _REPLY_PROFILES.get(media, _MOVIE_PROFILE)

    user_query = state.get("query", "")
    retrieved = state.get("retrieved") or []
    payload = {
        "query": user_query,
        "media_type": media,
        "candidates": retrieved[: deps.default_top_k],
        **deps.extra_user_payload,
    }
    messages = [
        {"role": "system", "content": profile.system_prompt},
        {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
    ]
    raw: dict[str, Any] = {}
    try:
        raw = deps.llm.chat_json(
            messages,
            response_format=profile.response_format,
            user_id=state.get("user_id"),
            max_tokens=deps.reply_max_tokens,
            temperature=deps.reply_temperature,
        )
        reply = str(raw.get("reply") or "").strip()
    except Exception:
        logger.exception("Reply generation failed; falling back to deterministic answer.")
        reply = _fallback_reply(media, retrieved)
    if not reply:
        reply = _fallback_reply(media, retrieved)
    return {"reply": reply, "reply_metadata": raw.get("metadata")}


def _fallback_reply(media: MediaType, retrieved: list[dict[str, Any]]) -> str:
    if not retrieved:
        return "조건에 맞는 추천을 찾지 못했어요. 다른 키워드로 시도해 보세요."
    if media == "feed":
        snippets = ", ".join(
            str(r.get("summary") or r.get("feed_id")) for r in retrieved[:3]
        )
        return f"이런 감상 피드를 추천드려요: {snippets}."
    titles = ", ".join(str(r.get("title") or r.get("movie_id")) for r in retrieved[:3])
    return f"이런 영화를 추천드려요: {titles}."


__all__ = ["generate_reply"]
