"""채팅 답변(generate_reply)용 프롬프트·JSON schema.

intent_scope 에 따라 Pydantic 스키마와 시스템 가이드를 분기한다.
추천 후보(movie/feed)는 system 메시지에 명시하고, metadata 는 해당 목록에서만 선택한다.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from textwrap import dedent
from typing import Any, Final, Literal

from src.ontology.schema import (
    ChatReplyBoth,
    ChatReplyFeed,
    ChatReplyMovie,
    ChatReplyNone,
    build_llm_json_schema,
)

ReplyScope = Literal["movie", "feed", "both", "none"]

REPLY_CACHE_SALT: Final[str] = "chat_reply:v1"

_MOVIE_CANDIDATE_FIELDS: Final[tuple[str, ...]] = (
    "movie_id",
    "title",
    "producing_year",
    "country",
    "plot_summary",
    "score",
)
_FEED_CANDIDATE_FIELDS: Final[tuple[str, ...]] = (
    "feed_id",
    "summary",
    "sentiment_score",
    "score",
)

_MOVIE_GUIDE: Final[str] = dedent(
    """
    너는 한국어 영화 추천 도우미다.
    system 메시지의 [영화 추천 후보 목록]만 근거로 사용자 요청에 1~3 문장으로 답하라.
    추천은 반드시 목록에 있는 영화만 선택한다. 목록에 없는 movie_id·제목을 생성하지 마라.
    답변에 언급한 추천 영화마다 metadata.movie 배열에 항목을 추가하라 (1~3개).
    각 항목은 {"type": "movie", "id": "<목록의 movie_id>"} 형식이다.
    후보 목록이 비어 있으면 metadata.movie 는 빈 배열로 두고 다른 키워드를 제안하라.
    """
).strip()

_FEED_GUIDE: Final[str] = dedent(
    """
    너는 한국어 영화 감상 피드 추천 도우미다.
    system 메시지의 [피드 추천 후보 목록]만 근거로 사용자 요청에 1~3 문장으로 답하라.
    추천은 반드시 목록에 있는 피드만 선택한다. 목록에 없는 feed_id·내용을 생성하지 마라.
    답변에 언급한 추천 피드마다 metadata.feed 배열에 항목을 추가하라 (1~3개).
    각 항목은 {"type": "feed", "id": "<목록의 feed_id>"} 형식이다.
    후보 목록이 비어 있으면 metadata.feed 는 빈 배열로 두고 다른 키워드를 제안하라.
    """
).strip()

_BOTH_GUIDE: Final[str] = dedent(
    """
    너는 한국어 영화·피드 추천 도우미다.
    system 메시지의 [영화 추천 후보 목록]과 [피드 추천 후보 목록]만 근거로 2~4 문장으로 답하라.
    영화·피드 추천을 모두 포함하되, 각각 해당 목록에서만 선택한다.
    metadata.movie / metadata.feed 의 id 는 각 목록의 movie_id·feed_id 중 하나여야 한다.
    답변에 언급한 추천마다 metadata.movie / metadata.feed 배열에 항목을 추가하라 (각 1~3개).
    """
).strip()

_NONE_GUIDE: Final[str] = dedent(
    """
    너는 한국어 영화 추천 서비스 도우미다.
    사용자 질의는 영화/피드 추천과 무관하다. 친절하게 1~3 문장으로 답하라.
    direct_reply_hint 가 있으면 참고하되, 추천 후보가 없으므로 일반 대화로 응답한다.
    metadata 는 빈 객체 {} 로 둔다.
    """
).strip()

_REPLY_SYSTEM_RULES: Final[str] = dedent(
    """
    [출력]
    - 단일 JSON 객체만 출력. 코드펜스/주석/설명 금지.
    - 스키마에 없는 키 추가 금지.
    - JSON 문자열 값에 줄바꿈 대신 공백 사용.
      metadata 의 id 는 system 메시지 후보 목록에 있는 값만 사용한다.
    """
).strip()


def _slim_candidate(row: dict[str, Any], fields: tuple[str, ...]) -> dict[str, Any]:
    return {
        key: row[key]
        for key in fields
        if key in row and row[key] is not None and row[key] != ""
    }


def _format_movie_candidates(candidates: list[dict[str, Any]]) -> str:
    if not candidates:
        return dedent(
            """
            [영화 추천 후보 목록]
            (후보 없음)
            """
        ).strip()
    slim = [_slim_candidate(row, _MOVIE_CANDIDATE_FIELDS) for row in candidates]
    return dedent(
        f"""
        [영화 추천 후보 목록]
        아래 JSON 배열에서만 추천 영화를 선택하라.
        metadata.movie[].id 는 반드시 아래 movie_id 값 중 하나여야 한다.

        {json.dumps(slim, ensure_ascii=False, indent=2)}
        """
    ).strip()


def _format_feed_candidates(candidates: list[dict[str, Any]]) -> str:
    if not candidates:
        return dedent(
            """
            [피드 추천 후보 목록]
            (후보 없음)
            """
        ).strip()
    slim = [_slim_candidate(row, _FEED_CANDIDATE_FIELDS) for row in candidates]
    return dedent(
        f"""
        [피드 추천 후보 목록]
        아래 JSON 배열에서만 추천 피드를 선택하라.
        metadata.feed[].id 는 반드시 아래 feed_id 값 중 하나여야 한다.

        {json.dumps(slim, ensure_ascii=False, indent=2)}
        """
    ).strip()


def _build_user_payload(payload: dict[str, Any]) -> str:
    user_body = {
        key: value
        for key, value in payload.items()
        if key not in ("movie_candidates", "feed_candidates")
    }
    return json.dumps(user_body, ensure_ascii=False)


def _candidate_system_messages(
    scope: ReplyScope,
    *,
    movie_candidates: list[dict[str, Any]] | None,
    feed_candidates: list[dict[str, Any]] | None,
) -> list[str]:
    messages: list[str] = []
    if scope in ("movie", "both"):
        messages.append(_format_movie_candidates(movie_candidates or []))
    if scope in ("feed", "both"):
        messages.append(_format_feed_candidates(feed_candidates or []))
    return messages


@dataclass(frozen=True)
class _ReplyPromptSpec:
    name: str
    guide: str
    schema_base: dict[str, Any]

    def schema_json(self) -> dict[str, Any]:
        return self.schema_base

    def build_payload(
        self,
        *,
        user_payload: str,
        candidate_system_messages: list[str] | None = None,
    ) -> dict[str, Any]:
        messages: list[dict[str, str]] = [
            {"role": "system", "content": _REPLY_SYSTEM_RULES},
            {"role": "system", "content": self.guide},
        ]
        for content in candidate_system_messages or []:
            messages.append({"role": "system", "content": content})
        messages.append({"role": "user", "content": user_payload})
        return {
            "messages": messages,
            "response_format": {
                "type": "json_schema",
                "schema": self.schema_json(),
            },
            "cache_salt": REPLY_CACHE_SALT,
        }


_REPLY_SPECS: dict[ReplyScope, _ReplyPromptSpec] = {
    "movie": _ReplyPromptSpec(
        name="reply_movie",
        guide=_MOVIE_GUIDE,
        schema_base=build_llm_json_schema(ChatReplyMovie, name="reply_movie_ontology"),
    ),
    "feed": _ReplyPromptSpec(
        name="reply_feed",
        guide=_FEED_GUIDE,
        schema_base=build_llm_json_schema(ChatReplyFeed, name="reply_feed_ontology"),
    ),
    "both": _ReplyPromptSpec(
        name="reply_both",
        guide=_BOTH_GUIDE,
        schema_base=build_llm_json_schema(ChatReplyBoth, name="reply_both_ontology"),
    ),
    "none": _ReplyPromptSpec(
        name="reply_none",
        guide=_NONE_GUIDE,
        schema_base=build_llm_json_schema(ChatReplyNone, name="reply_none_ontology"),
    ),
}


def get_reply_schema_json(scope: ReplyScope) -> dict[str, Any]:
    return _REPLY_SPECS[scope].schema_json()


def build_reply_messages(
    *,
    scope: ReplyScope,
    payload: dict[str, Any],
) -> dict[str, Any]:
    """분석·필터링 결과 payload → generate_reply messages + response_format."""
    movie_candidates = payload.get("movie_candidates")
    feed_candidates = payload.get("feed_candidates")
    user_payload = _build_user_payload(payload)
    candidate_messages = _candidate_system_messages(
        scope,
        movie_candidates=movie_candidates if isinstance(movie_candidates, list) else None,
        feed_candidates=feed_candidates if isinstance(feed_candidates, list) else None,
    )
    return _REPLY_SPECS[scope].build_payload(
        user_payload=user_payload,
        candidate_system_messages=candidate_messages,
    )


__all__ = [
    "REPLY_CACHE_SALT",
    "ReplyScope",
    "build_reply_messages",
    "get_reply_schema_json",
]
