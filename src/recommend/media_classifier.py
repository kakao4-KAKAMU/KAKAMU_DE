"""추천 매체(영화 / 피드) 분류기 (LLM 기반).

SOLID
-----
- SRP : 자연어 질의를 추천 매체 타입으로 분류하는 책임만 가진다.
- DIP : 구체 LLM 이 아닌 ``JSONChatLLM`` Protocol 에만 의존한다.
- OCP : 프롬프트/응답 스키마/기본값 교체로 동작을 확장한다.
"""

from __future__ import annotations

import logging
from textwrap import dedent
from typing import Any, Literal, Protocol

logger = logging.getLogger(__name__)

MediaType = Literal["movie", "feed"]


class JSONChatLLM(Protocol):
    """매체 분류에 필요한 LLM 의 최소 인터페이스(ISP)."""

    def chat_json(
        self,
        messages: list[dict[str, str]],
        *,
        user_id: str | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
        response_format: dict[str, Any] | None = None,
        cache_salt: str | None = None,
        guided_json_schema: dict[str, Any] | None = None,
    ) -> dict[str, Any]: ...


_LLM_SYSTEM_PROMPT = dedent(
    """
    너는 추천 매체 분류기다.
    사용자 질의가 아래 둘 중 무엇을 원하는지 판단하라.
    - "movie": 영화 자체(작품)를 추천받고 싶은 경우.
    - "feed": 영화에 대한 감상/후기/리뷰/게시글(피드)을 추천받고 싶은 경우.
    판단이 모호하면 "movie" 를 선택하라.
    출력은 단일 JSON 객체: {"media_type": "movie" | "feed"}.
    """
).strip()

_LLM_RESPONSE_FORMAT: dict[str, Any] = {
    "type": "json_schema",
    "json_schema": {
        "name": "media_classification",
        "strict": True,
        "schema": {
            "type": "object",
            "properties": {
                "media_type": {"type": "string", "enum": ["movie", "feed"]},
            },
            "required": ["media_type"],
        },
    },
}


class LLMMediaClassifier:
    """LLM 으로 추천 매체를 판단하는 분류기.

    LLM 호출이 실패하거나 비정상 응답(스키마 밖 값)일 때, 또는 질의가 비어 있을
    때는 ``default`` (기본 ``"movie"``) 로 안전하게 처리한다.
    """

    def __init__(
        self,
        llm: JSONChatLLM,
        *,
        default: MediaType = "movie",
        max_tokens: int = 16,
        temperature: float = 0.0,
    ) -> None:
        self._llm = llm
        self._default: MediaType = default
        self._max_tokens = max_tokens
        self._temperature = temperature

    def classify(self, query: str) -> MediaType:
        text = (query or "").strip()
        if not text:
            return self._default
        messages = [
            {"role": "system", "content": _LLM_SYSTEM_PROMPT},
            {"role": "user", "content": text},
        ]
        try:
            raw = self._llm.chat_json(
                messages,
                response_format=_LLM_RESPONSE_FORMAT,
                max_tokens=self._max_tokens,
                temperature=self._temperature,
            )
            media = str(raw.get("media_type") or "").strip().lower()
            if media in ("movie", "feed"):
                return media  # type: ignore[return-value]
            logger.warning("LLM media classification returned unexpected value: %r", media)
        except Exception:
            logger.exception("LLM media classification failed; using default %r.", self._default)
        return self._default


__all__ = ["LLMMediaClassifier", "JSONChatLLM", "MediaType"]
