"""온톨로지 프롬프트 payload 조립 파이프라인.

SOLID
-----
- SRP : schema enum 주입 결과를 OntologyChatPayload 로 조립만 담당한다.
- DIP : vocabulary 주입은 schema_vocab, 시스템 규칙은 base 에 위임한다.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from src.extractor.base import OntologyChatPayload
from src.ontology.prompts.base import ONTOLOGY_SYSTEM_PROMPT
from src.ontology.prompts.schema_vocab import (
    apply_vocab_enums,
    build_vocab_guide_lines,
    with_vocab_cache_salt,
)

_SCHEMA_CACHE: dict[str, dict[str, Any]] = {}


@dataclass(frozen=True)
class OntologyPromptSpec:
    """선언적 스키마·가이드 → vocab 주입 JSON schema · chat payload."""

    name: str
    base_schema: dict[str, Any]
    guide: str
    cache_salt: str

    def schema_json(self) -> dict[str, Any]:
        cached = _SCHEMA_CACHE.get(self.name)
        if cached is None:
            cached = apply_vocab_enums(self.base_schema)
            _SCHEMA_CACHE[self.name] = cached
        return cached

    def build_payload(self, *, user_payload: str) -> OntologyChatPayload:
        return {
            "messages": [
                {"role": "system", "content": ONTOLOGY_SYSTEM_PROMPT},
                {"role": "system", "content": build_vocab_guide_lines()},
                {"role": "system", "content": self.guide},
                {"role": "user", "content": user_payload},
            ],
            "response_format": {
                "type": "json_schema",
                "json_schema": self.schema_json(),
            },
            "cache_salt": with_vocab_cache_salt(self.cache_salt),
        }


__all__ = ["OntologyPromptSpec"]
