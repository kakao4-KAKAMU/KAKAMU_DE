from typing import Any, Callable, Mapping, Protocol


class Embedder(Protocol):
    """경량 임베딩 추상화. 실제 구현은 VLLMEmbeddingClient."""

    def embed(self, text: str) -> list[float]: ...


class LLMClient(Protocol):
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


Handler = Callable[[Mapping[str, Any]], None]


__all__ = ["Embedder", "LLMClient", "Handler"]
