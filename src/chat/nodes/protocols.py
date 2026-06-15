"""노드가 의존하는 최소 인터페이스(Protocol).

SOLID
-----
- ISP : 노드가 실제로 호출하는 메서드만 노출해 테스트에서 mock 하기 쉽게 한다.
- DIP : 구체 구현(vLLM, 분류기 등)이 아닌 추상 Protocol 에 의존한다.
"""

from __future__ import annotations

from typing import Any, Protocol

from src.chat.state import MediaType


class EmbedderLike(Protocol):
    def embed(self, text: str) -> list[float]: ...


class ChatLLMLike(Protocol):
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


class MediaClassifierLike(Protocol):
    def classify(self, query: str) -> MediaType: ...


__all__ = ["EmbedderLike", "ChatLLMLike", "MediaClassifierLike"]
