"""vLLM(OpenAI-compatible) chat 클라이언트.

이 모듈은 다음 두 가지에 특화되어 있다.

1) **유저 단위 KV-cache 재사용**
   - vLLM 의 `--enable-prefix-caching` 활성화 시, 동일한 prompt prefix 는
     PagedAttention 블록 단위로 KV-cache 가 자동 재사용된다.
   - 따라서 본 클라이언트는 호출마다 system prompt 와 user persona prefix 를
     **동일한 순서/내용**으로 배치하여 prefix-cache hit-rate 를 극대화한다.
   - 또한 OpenAI 호환 확장 필드인 `user` 를 채워, vLLM 서버 사이드에서
     사용자별 라우팅/로그 추적이 가능하도록 한다.
   - `cache_salt` 로 동일 온톨로지 타입끼리 prefix-cache 를 공유하고,
     타입/테넌트 간 캐시 격리를 할 수 있다 (`extra_body.cache_salt`).

2) **JSON 강제 출력**
   - `response_format={"type": "json_schema", "json_schema": ...}` 로 structured output.
   - 미지정 시 `{"type": "json_object"}` 를 사용한다.
   - `guided_json_schema` 는 vLLM guided decoding 호환을 위한 레거시 옵션이다.

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


def _apply_extra_body(kwargs: dict[str, Any], extra: dict[str, Any]) -> None:
    """extra_body 필드를 병합한다 (guided_json / cache_salt 등)."""
    if not extra:
        return
    merged = dict(kwargs.get("extra_body") or {})
    merged.update(extra)
    kwargs["extra_body"] = merged


def _normalize_json_schema_wrapper(wrapper: dict[str, Any]) -> dict[str, Any]:
    """OpenAI/vLLM 이 기대하는 ``{name, strict?, schema}`` wrapper 로 맞춘다."""
    normalized = dict(wrapper)
    if "schema" not in normalized:
        legacy_schema = normalized.pop("json_schema", None)
        if isinstance(legacy_schema, dict):
            normalized["schema"] = legacy_schema
    return normalized


def normalize_response_format(response_format: dict[str, Any]) -> dict[str, Any]:
    """vLLM structured output 검증 오류를 피하도록 response_format 을 정규화한다."""
    rf_type = response_format.get("type")

    # bare wrapper → full response_format
    if rf_type is None and ("schema" in response_format or "json_schema" in response_format):
        return {
            "type": "json_schema",
            "json_schema": _normalize_json_schema_wrapper(response_format),
        }

    if rf_type != "json_schema":
        return response_format

    # flat: {"type": "json_schema", "name": ..., "schema": ...}
    if "json_schema" not in response_format and (
        "schema" in response_format or "name" in response_format
    ):
        wrapper = {
            key: response_format[key]
            for key in ("name", "strict", "schema", "json_schema")
            if key in response_format
        }
        return {
            "type": "json_schema",
            "json_schema": _normalize_json_schema_wrapper(wrapper),
        }

    inner = response_format.get("json_schema")
    if not isinstance(inner, dict):
        return response_format

    normalized_inner = _normalize_json_schema_wrapper(inner)
    if normalized_inner == inner:
        return response_format

    return {"type": "json_schema", "json_schema": normalized_inner}


class VLLMChatClient:
    """OpenAI 호환 vLLM 서버용 chat 클라이언트."""

    def __init__(self, settings: Optional[VLLMGenSettings] = None) -> None:
        self._settings = settings or get_settings().vllm_gen
        self._client = OpenAI(
            base_url=self._settings.base_url,
            api_key=self._settings.api_key,
            timeout=600
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
        frequency_penalty: float | None = None,
        response_format: dict[str, Any] | None = None,
        cache_salt: str | None = None,
        guided_json_schema: dict[str, Any] | None = None,
        thinking: bool = True,
    ) -> dict[str, Any]:
        """JSON 객체만 반환하는 chat 호출.

        Args:
            messages: system/user role messages.
            user_id : 사용자 단위 prefix-cache 추적/라우팅을 위한 식별자.
            max_tokens / temperature : per-call override.
            response_format: OpenAI structured output (`json_schema` 등).
            cache_salt: vLLM prefix-cache 격리/공유용 salt (`extra_body`).
            guided_json_schema : vLLM `extra_body.guided_json` (response_format 미지정 시).
        """

        kwargs: dict[str, Any] = {
            "model": self._settings.model_name,
            "messages": messages,
            "max_tokens": max_tokens or self._settings.max_tokens,
            "temperature": (
                temperature if temperature is not None else self._settings.temperature
            ),
            "top_p": 0.95,
            "seed": 23419708,
            "thinking_token_budget": 1000,
        }
        if user_id:
            kwargs["user"] = user_id

        if response_format is not None:
            kwargs["response_format"] = normalize_response_format(response_format)
        else:
            kwargs["response_format"] = {"type": "json_object"}

        extra_body: dict[str, Any] = {}
        if frequency_penalty:
            extra_body["frequency_penalty"] = frequency_penalty
        if cache_salt:
            extra_body["cache_salt"] = cache_salt
        if guided_json_schema is not None and response_format is None:
            extra_body["guided_json"] = guided_json_schema
        extra_body["chat_template_kwargs"] = {"enable_thinking": False}
        _apply_extra_body(kwargs, extra_body)

        resp = self._client.chat.completions.create(**kwargs)
        content = resp.choices[0].message.content or "{}"

        try:
            return json.loads(content)
        except json.JSONDecodeError:
            logger.warning(
                "vLLM returned non-JSON content; attempting recovery. requestContent = %s", kwargs["messages"]
            )
            start = content.find("{")
            end = content.rfind("}")
            if start != -1 and end != -1 and end > start:
                return json.loads(content[start : end + 1])
            raise


__all__ = ["VLLMChatClient", "normalize_response_format"]
