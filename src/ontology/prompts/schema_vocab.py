"""genre_theme_mood_library → JSON Schema enum 주입.

SOLID
-----
- SRP : vocabulary 로드와 schema enum 주입만 담당한다.
- OCP : 새 프롬프트 스키마는 ``apply_vocab_enums`` / ``build_keyword_item_schema`` 로 확장한다.
- DIP : 프롬프트 빌더는 본 모듈의 getter 에만 의존한다.
"""

from __future__ import annotations

import hashlib
from copy import deepcopy
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from src.ontology.schema import KEYWORD_KIND_VALUES, Keyword, build_strict_object_schema
from src.vocab.normalizer import VocabularyNormalizer

LIBRARY_PATH: Path = (
    Path(__file__).resolve().parents[3] / "docs" / "genre_theme_mood_library.md"
)

# themes/moods 는 movie 전용 폐쇄형 필드. keywords.kind 는 schema.KeywordKind 기준.
KEYWORD_KINDS: tuple[str, ...] = tuple(KEYWORD_KIND_VALUES)


@lru_cache(maxsize=1)
def get_vocab_normalizer() -> VocabularyNormalizer:
    if LIBRARY_PATH.is_file():
        return VocabularyNormalizer.from_library_md(LIBRARY_PATH)
    return VocabularyNormalizer(themes=set(), moods=set(), genres=set())


@lru_cache(maxsize=1)
def vocab_genres() -> tuple[str, ...]:
    return tuple(sorted(get_vocab_normalizer().genres()))


@lru_cache(maxsize=1)
def vocab_themes() -> tuple[str, ...]:
    return tuple(sorted(get_vocab_normalizer().themes()))


@lru_cache(maxsize=1)
def vocab_moods() -> tuple[str, ...]:
    return tuple(sorted(get_vocab_normalizer().moods()))


@lru_cache(maxsize=1)
def vocab_fingerprint() -> str:
    payload = "|".join(
        [
            ",".join(vocab_genres()),
            ",".join(vocab_themes()),
            ",".join(vocab_moods()),
        ]
    )
    return hashlib.sha256(payload.encode()).hexdigest()[:12]


def string_enum(values: Sequence[str]) -> dict[str, Any]:
    return {"type": "string", "enum": list(values)}


def string_array_enum(values: Sequence[str]) -> dict[str, Any]:
    return {"type": "array", "items": string_enum(values)}


def build_keyword_item_schema() -> dict[str, Any]:
    return build_strict_object_schema(Keyword)


def _schema_root(json_schema: Mapping[str, Any]) -> dict[str, Any]:
    root = json_schema.get("schema", json_schema)
    if not isinstance(root, dict):
        raise TypeError("json_schema must contain an object schema")
    return root


def _field_parent(root: dict[str, Any], path: str) -> tuple[dict[str, Any], str]:
    """``movie.themes`` 같은 dotted path 의 부모 properties 와 필드명을 반환."""
    parts = path.split(".")
    node = root
    for part in parts[:-1]:
        props = node.get("properties")
        if not isinstance(props, dict) or part not in props:
            raise KeyError(path)
        node = props[part]
    return node, parts[-1]


def apply_vocab_enums(
    json_schema: Mapping[str, Any],
    *,
    genre_fields: Iterable[str] = ("genres",),
    theme_fields: Iterable[str] = ("themes",),
    mood_fields: Iterable[str] = ("moods",),
    keyword_fields: Iterable[str] = ("keywords",),
    static_genre_enums: Mapping[str, Sequence[str]] | None = None,
) -> dict[str, Any]:
    """JSON schema wrapper 에 vocabulary enum 을 주입한 deep copy 를 반환한다."""

    result = deepcopy(dict(json_schema))
    root = _schema_root(result)
    properties = root.get("properties")
    if not isinstance(properties, dict):
        return result

    static_genres = static_genre_enums or {}

    for field in genre_fields:
        values = static_genres.get(field, vocab_genres())
        parent, name = _field_parent(root, field)
        parent.setdefault("properties", {})[name] = string_array_enum(values)
    for field in theme_fields:
        parent, name = _field_parent(root, field)
        parent.setdefault("properties", {})[name] = string_array_enum(vocab_themes())
    for field in mood_fields:
        parent, name = _field_parent(root, field)
        parent.setdefault("properties", {})[name] = string_array_enum(vocab_moods())

    keyword_schema = {
        "type": "array",
        "maxItems": 10,
        "items": build_keyword_item_schema(),
    }
    for field in keyword_fields:
        parent, name = _field_parent(root, field)
        parent.setdefault("properties", {})[name] = deepcopy(keyword_schema)

    return result


def build_vocab_guide_lines() -> str:
    genres = vocab_genres()
    themes = vocab_themes()
    moods = vocab_moods()
    return (
        "[폐쇄형 vocabulary — 반드시 아래 표제어만 사용]\n"
        # f"- genres (한국어, {len(genres)}종): "
        # f"{', '.join(genres)}\n"
        f"- themes (snake_case, {len(themes)}종): "
        f"{', '.join(themes)}\n"
        f"- moods (snake_case, {len(moods)}종): "
        f"{', '.join(moods)}\n"
    )


def with_vocab_cache_salt(base_salt: str) -> str:
    return f"{base_salt}:vocab:{vocab_fingerprint()}"


__all__ = [
    "KEYWORD_KINDS",
    "LIBRARY_PATH",
    "apply_vocab_enums",
    "build_keyword_item_schema",
    "build_vocab_guide_lines",
    "get_vocab_normalizer",
    "string_array_enum",
    "string_enum",
    "vocab_fingerprint",
    "vocab_genres",
    "vocab_moods",
    "vocab_themes",
    "with_vocab_cache_salt",
]
