"""genre_theme_mood_library → JSON Schema enum 주입.

SOLID
-----
- SRP : vocabulary 로드와 schema enum 주입만 담당한다.
- OCP : 새 프롬프트 스키마는 ``apply_vocab_enums`` / ``build_keyword_item_schema`` 로 확장한다.
- DIP : 프롬프트 빌더는 본 모듈의 getter 에만 의존한다.
"""

from __future__ import annotations

import hashlib
import json
import re
from copy import deepcopy
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from textwrap import dedent
from typing import Any, Iterable, Mapping, Sequence

from src.ontology.schema import KEYWORD_KIND_VALUES, Keyword, build_strict_object_schema
from src.vocab.normalizer import VocabularyNormalizer

LIBRARY_PATH: Path = (
    Path(__file__).resolve().parents[3] / "docs" / "genre_theme_mood_library.md"
)

# themes/moods 는 movie 전용 폐쇄형 필드. keywords.kind 는 schema.KeywordKind 기준.
KEYWORD_KINDS: tuple[str, ...] = tuple(KEYWORD_KIND_VALUES)

_JSON_OBJECT_BLOCK = re.compile(r"```json\s*(\{.*?\})\s*```", re.DOTALL)
_JSON_ARRAY_BLOCK = re.compile(r"```json\s*(\[.*?\])\s*```", re.DOTALL)
_MOOD_ONTOLOGY_HEADER = re.compile(r"^# Mood Ontology\s*$", re.MULTILINE)


@dataclass(frozen=True)
class _GenreMeta:
    name: str
    common_themes: tuple[str, ...]
    common_moods: tuple[str, ...]


@dataclass(frozen=True)
class _ThemeMeta:
    name: str
    display_ko: str
    related_moods: tuple[str, ...]


@dataclass(frozen=True)
class _MoodMeta:
    name: str
    display_ko: str


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


@lru_cache(maxsize=1)
def _load_cypher_vocab_metadata() -> tuple[
    tuple[_GenreMeta, ...], tuple[_ThemeMeta, ...], tuple[_MoodMeta, ...]
]:
    """genre_theme_mood_library 에서 Cypher 질문 분석용 ontology 메타를 로드한다."""
    normalizer = get_vocab_normalizer()
    relations = normalizer.relations

    genre_meta: dict[str, _GenreMeta] = {}
    theme_ko: dict[str, str] = {}
    theme_moods: dict[str, set[str]] = {}
    mood_ko: dict[str, str] = {}

    if LIBRARY_PATH.is_file():
        text = LIBRARY_PATH.read_text(encoding="utf-8")
        for block in _JSON_OBJECT_BLOCK.findall(text):
            try:
                data = json.loads(block)
            except json.JSONDecodeError:
                continue
            if not isinstance(data, dict):
                continue

            obj_id = str(data.get("id", ""))
            if obj_id.startswith("genre_"):
                display_ko = str(data.get("display_name_ko", ""))
                english_name = str(data.get("name", ""))
                korean = (
                    normalizer.normalize_genre(display_ko)
                    or normalizer.normalize_genre(english_name)
                    or display_ko
                )
                if not korean:
                    continue
                block_themes = {str(t) for t in data.get("common_themes", [])}
                block_moods = {str(m) for m in data.get("common_moods", [])}
                rel_themes = set(relations.genre_themes.get(korean, ()))
                rel_moods = set(relations.genre_moods.get(korean, ()))
                genre_meta[korean] = _GenreMeta(
                    korean,
                    tuple(sorted(block_themes | rel_themes)),
                    tuple(sorted(block_moods | rel_moods)),
                )
            elif obj_id.startswith("theme_"):
                name = str(data.get("name", ""))
                if not name:
                    continue
                theme_ko[name] = str(data.get("display_name_ko", name))
                theme_moods.setdefault(name, set()).update(
                    str(m) for m in data.get("related_moods", [])
                )

        mood_match = _MOOD_ONTOLOGY_HEADER.search(text)
        if mood_match is not None:
            section = text[mood_match.end() :]
            next_header = re.search(r"^# ", section, re.MULTILINE)
            if next_header is not None:
                section = section[: next_header.start()]
            for block in _JSON_ARRAY_BLOCK.findall(section):
                try:
                    data = json.loads(block)
                except json.JSONDecodeError:
                    continue
                if not isinstance(data, list):
                    continue
                for item in data:
                    if not isinstance(item, dict) or not item.get("name"):
                        continue
                    name = str(item["name"])
                    mood_ko[name] = str(item.get("display_name_ko", name))

    genres = tuple(
        genre_meta.get(
            genre,
            _GenreMeta(
                genre,
                tuple(sorted(relations.genre_themes.get(genre, ()))),
                tuple(sorted(relations.genre_moods.get(genre, ()))),
            ),
        )
        for genre in vocab_genres()
    )
    themes = tuple(
        _ThemeMeta(
            theme,
            theme_ko.get(theme, theme),
            tuple(
                sorted(
                    theme_moods.get(theme, set())
                    | set(relations.theme_moods.get(theme, ()))
                )
            ),
        )
        for theme in vocab_themes()
    )
    moods = tuple(_MoodMeta(mood, mood_ko.get(mood, "")) for mood in vocab_moods())
    return genres, themes, moods


def build_cypher_analysis_knowledge() -> str:
    """Cypher 생성 프롬프트용 Genre/Theme/Mood 질문 분석 ontology 가이드."""
    genres, themes, moods = _load_cypher_vocab_metadata()
    lines = [
        dedent(
            """\
            [질문 분석 기준 — Genre / Theme / Mood]
            1. 사용자 질문에서 장르·테마·무드 의도를 식별한다.
            2. Genre: (m:Movie)-[:HAS_GENRE]->(g:Genre {name: '<한국어>'})
            3. Theme: (m:Movie)-[:HAS_THEME]->(t:Theme {name: '<snake_case>'})
            4. Mood: (m:Movie)-[:HAS_MOOD]->(md:Mood {name: '<snake_case>'})
            5. 한국어 표현은 display_ko 와 대조해 canonical name 을 선택한다.
            6. 복수 조건은 MATCH 패턴을 AND 로 연결한다.
            """
        ).strip(),
        "",
        f"## Genre ({len(genres)}종, Genre.name=한국어)",
    ]
    for genre in genres:
        theme_part = ", ".join(genre.common_themes) if genre.common_themes else "-"
        mood_part = ", ".join(genre.common_moods) if genre.common_moods else "-"
        lines.append(f"- {genre.name} | themes: {theme_part} | moods: {mood_part}")

    lines.extend(["", f"## Theme ({len(themes)}종, Theme.name=snake_case)"])
    for theme in themes:
        ko_suffix = (
            f" ({theme.display_ko})" if theme.display_ko and theme.display_ko != theme.name else ""
        )
        mood_part = ", ".join(theme.related_moods) if theme.related_moods else "-"
        lines.append(f"- {theme.name}{ko_suffix} | moods: {mood_part}")

    lines.extend(["", f"## Mood ({len(moods)}종, Mood.name=snake_case)"])
    for mood in moods:
        if mood.display_ko:
            lines.append(f"- {mood.name} ({mood.display_ko})")
        else:
            lines.append(f"- {mood.name}")

    return "\n".join(lines)


def with_vocab_cache_salt(base_salt: str) -> str:
    return f"{base_salt}:vocab:{vocab_fingerprint()}"


__all__ = [
    "KEYWORD_KINDS",
    "LIBRARY_PATH",
    "apply_vocab_enums",
    "build_cypher_analysis_knowledge",
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
