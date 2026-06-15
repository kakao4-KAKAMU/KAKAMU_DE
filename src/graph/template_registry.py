"""Cypher 템플릿 레지스트리 (화이트리스트 실행).

SOLID - SRP: 템플릿 등록/검증만 담당.
SOLID - OCP: 새 템플릿은 register() 로만 추가.
"""

from __future__ import annotations

import re
from typing import Any, Mapping

from pydantic import BaseModel, Field

_PARAM_PATTERN = re.compile(r"\$([a-zA-Z_][a-zA-Z0-9_]*)")
_FORBIDDEN = re.compile(
    r"\b(CREATE|MERGE|DELETE|DETACH|SET|REMOVE|DROP|LOAD\s+CSV|CALL\s+dbms\.)\b",
    re.IGNORECASE,
)


class CypherTemplate(BaseModel):
    """등록 가능한 읽기 전용 Cypher 템플릿."""

    id: str
    cypher: str
    params_schema: dict[str, str] = Field(
        default_factory=dict,
        description="param_name -> type hint (string|optional_string|int|float|list|string_list|float_list|bool)",
    )
    read_only: bool = True
    max_limit: int = Field(default=100, ge=1, le=500)
    description: str = ""


class TemplateValidationError(ValueError):
    pass


class TemplateRegistry:
    def __init__(self) -> None:
        self._templates: dict[str, CypherTemplate] = {}

    def register(self, template: CypherTemplate) -> None:
        if template.read_only and _FORBIDDEN.search(template.cypher):
            raise TemplateValidationError(
                f"Template {template.id} contains forbidden write operations"
            )
        self._templates[template.id] = template

    def get(self, template_id: str) -> CypherTemplate:
        if template_id not in self._templates:
            raise TemplateValidationError(f"Unknown template_id: {template_id}")
        return self._templates[template_id]

    def list_ids(self) -> list[str]:
        return sorted(self._templates.keys())

    def validate_params(
        self, template_id: str, params: Mapping[str, Any]
    ) -> dict[str, Any]:
        tpl = self.get(template_id)
        required = set(_PARAM_PATTERN.findall(tpl.cypher))
        provided = set(params.keys())

        missing = required - provided
        if missing:
            raise TemplateValidationError(f"Missing params for {template_id}: {missing}")

        cleaned: dict[str, Any] = {}
        for key in required:
            value = params[key]
            hint = tpl.params_schema.get(key, "string")
            cleaned[key] = _coerce(value, hint)

        if "top_k" in cleaned:
            top_k = int(cleaned["top_k"])
            if top_k > tpl.max_limit:
                raise TemplateValidationError(
                    f"top_k {top_k} exceeds max_limit {tpl.max_limit}"
                )
            cleaned["top_k"] = top_k

        if "vec_top_k" in cleaned:
            vec_top_k = int(cleaned["vec_top_k"])
            if vec_top_k > tpl.max_limit * 2:
                raise TemplateValidationError("vec_top_k too large")
            cleaned["vec_top_k"] = vec_top_k

        return cleaned


_TRUTHY = {"true", "1", "yes", "y", "on"}
_FALSY = {"false", "0", "no", "n", "off"}


def _coerce(value: Any, hint: str) -> Any:
    if hint == "int":
        return int(value)
    if hint == "float":
        return float(value)
    if hint == "bool":
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)):
            return bool(value)
        text = str(value).strip().lower()
        if text in _TRUTHY:
            return True
        if text in _FALSY:
            return False
        raise TemplateValidationError(f"Cannot coerce {value!r} to bool")
    if hint == "float_list":
        if not isinstance(value, list):
            raise TemplateValidationError(f"Expected list, got {type(value)}")
        return [float(v) for v in value]
    if hint == "optional_string":
        if value is None:
            return None
        text = str(value).strip()
        return text or None
    if hint in ("list", "string_list"):
        if not isinstance(value, list):
            raise TemplateValidationError(f"Expected list, got {type(value)}")
        return [str(v) for v in value]
    return str(value)


__all__ = [
    "CypherTemplate",
    "TemplateRegistry",
    "TemplateValidationError",
]
