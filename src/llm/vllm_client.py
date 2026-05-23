"""vLLM(OpenAI-compatible) chat 클라이언트.

이 모듈은 다음 두 가지에 특화되어 있다.

1) **유저 단위 KV-cache 재사용**
   - vLLM 의 `--enable-prefix-caching` 활성화 시, 동일한 prompt prefix 는
     PagedAttention 블록 단위로 KV-cache 가 자동 재사용된다.
   - 따라서 본 클라이언트는 호출마다 system prompt 와 user persona prefix 를
     **동일한 순서/내용**으로 배치하여 prefix-cache hit-rate 를 극대화한다.
   - 또한 OpenAI 호환 확장 필드인 `user` 를 채워, vLLM 서버 사이드에서
     사용자별 라우팅/로그 추적이 가능하도록 한다.

2) **JSON 강제 출력**
   - `response_format={"type": "json_object"}` 를 사용해 LLM 출력의 형태를 잡고,
     `extra_body={"guided_json": ...}` 또는 `guided_decoding_backend` 를 통해
     Pydantic 스키마 기반 guided decoding 을 옵션으로 제공한다.

SOLID
-----
- SRP : "LLM 호출" 만 담당. 프롬프트/스키마는 외부에서 주입.
- LSP : `LLMClient` Protocol 의 chat_json 시그니처를 구현한다.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Optional

from openai import OpenAI

from src.config.settings import VLLMGenSettings, get_settings

logger = logging.getLogger(__name__)


class VLLMChatClient:
    """OpenAI 호환 vLLM 서버용 chat 클라이언트."""

    def __init__(self, settings: Optional[VLLMGenSettings] = None) -> None:
        self._settings = settings or get_settings().vllm_gen
        self._client = OpenAI(
            base_url=self._settings.base_url,
            api_key=self._settings.api_key,
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def chat_json(
        self,
        messages: list[dict[str, str]],
        *,
        user_id: str | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
        guided_json_schema: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """JSON 객체만 반환하는 chat 호출.

        Args:
            messages: system/user role messages.
            user_id : 사용자 단위 prefix-cache 추적/라우팅을 위한 식별자.
            max_tokens / temperature : per-call override.
            guided_json_schema : Pydantic JSON Schema. 지정 시 guided decoding 적용.
        """

        kwargs: dict[str, Any] = {
            "model": self._settings.model_name,
            "messages": messages,
            "max_tokens": max_tokens or self._settings.max_tokens,
            "temperature": temperature if temperature is not None else self._settings.temperature,
            "response_format": {"type": "json_object"},
        }
        if user_id:
            kwargs["user"] = user_id

        if guided_json_schema is not None:
            kwargs["extra_body"] = {"guided_json": guided_json_schema}

        resp = self._client.chat.completions.create(**kwargs)
        content = resp.choices[0].message.content or "{}"

        try:
            return json.loads(content)
        except json.JSONDecodeError:
            logger.warning(
                "vLLM returned non-JSON content; attempting recovery. head=%s",
                content[:200],
            )
            start = content.find("{")
            end = content.rfind("}")
            if start != -1 and end != -1 and end > start:
                return json.loads(content[start : end + 1])
            raise


__all__ = ["VLLMChatClient"]
