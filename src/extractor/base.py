"""온톨로지 Extractor 추상화.

설계 원칙
---------
- SRP : 추출기는 "비정형 텍스트 → 온톨로지 객체" 변환만 담당.
- LSP : 모든 Extractor 는 동일 시그니처의 .extract() 를 가진다.
- DIP : 상위 파이프라인은 본 abstract 에만 의존한다.
- OCP : 새 LLM/SLM 백엔드는 LLMClient 추상화만 만족하면 교체 가능.
"""

from __future__ import annotations

import json
import logging
from abc import ABC, abstractmethod
from typing import Any, Generic, NotRequired, Protocol, TypedDict, TypeVar

from pydantic import BaseModel, ValidationError

logger = logging.getLogger(__name__)


T = TypeVar("T", bound=BaseModel)


class OntologyChatPayload(TypedDict):
    """프롬프트 빌더 → LLM 호출에 전달하는 messages + structured output 스펙."""

    messages: list[dict[str, str]]
    response_format: dict[str, Any]
    cache_salt: NotRequired[str]


class LLMClient(Protocol):
    """vLLM/OpenAI-compatible chat completion 추상화."""

    def chat_json(
        self,
        messages: list[dict[str, str]],
        *,
        user_id: str | None = None,
        max_tokens: int = 1536,
        temperature: float = 0.2,
        frequency_penalty: float | None = None,
        response_format: dict[str, Any] | None = None,
        cache_salt: str | None = None,
        guided_json_schema: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        ...


class OntologyExtractor(ABC, Generic[T]):
    """비정형 텍스트 → 온톨로지 Pydantic 객체 변환 추상기."""

    def __init__(self, llm: LLMClient, schema_cls: type[T]) -> None:
        self._llm = llm
        self._schema_cls = schema_cls

    @abstractmethod
    def build_messages(self, **kwargs: Any) -> OntologyChatPayload:
        """입력에서 chat messages 와 response_format 을 생성. 구현체별로 다르다."""

    def extract(self, **kwargs: Any) -> T:
        """messages 생성 → LLM 호출 → JSON → Pydantic 검증 까지의 표준 흐름."""
        payload = self.build_messages(**kwargs)
        user_id = kwargs.get("author_id") or kwargs.get("user_id") or "system"

        cache_salt = kwargs.get("cache_salt") or payload.get("cache_salt")
        raw = self._llm.chat_json(
            messages=payload.get("messages", []),
            user_id=user_id,
            frequency_penalty=payload.get("frequency_penalty"),
            response_format=payload.get("response_format"),
            cache_salt=cache_salt,
        )

        try:
            return self._schema_cls.model_validate(raw)
        except ValidationError as e:
            logger.warning(
                "Ontology validation failed (cls=%s). Falling back to lenient parse.",
                self._schema_cls.__name__,
                exc_info=False,
            )
            # 강화: 일부 LLM 이 추가 키를 넣는 경우, 알려진 필드만 추려 다시 시도.
            allowed = set(self._schema_cls.model_fields.keys())
            cleaned = {k: v for k, v in raw.items() if k in allowed}
            try:
                return self._schema_cls.model_validate(cleaned)
            except ValidationError:
                logger.error(
                    "Failed to parse LLM ontology output. raw=%s",
                    json.dumps(raw, ensure_ascii=False)[:1000],
                )
                raise e


__all__ = ["LLMClient", "OntologyChatPayload", "OntologyExtractor"]
