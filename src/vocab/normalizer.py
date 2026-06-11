"""폐쇄형 vocabulary 정규화.

SOLID
-----
- SRP : 표제어 매핑 lookup만 담당. 외부에서는 ``normalize_*`` 와 public iterator 만 사용.
- OCP : ``from_library_md`` 등 alternative loader 를 추가해 확장한다.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Mapping, Optional

_JSON_OBJECT_BLOCK = re.compile(r"```json\s*(\{.*?\})\s*```", re.DOTALL)
_JSON_ARRAY_BLOCK = re.compile(r"```json\s*(\[.*?\])\s*```", re.DOTALL)
_GENRE_LIST_HEADER = re.compile(r"^genre list\s*$", re.MULTILINE | re.IGNORECASE)


@dataclass(frozen=True)
class OntologyRelations:
    """Genre/Theme/Mood 온톨로지 간 연관 관계."""

    genre_themes: Mapping[str, frozenset[str]]
    genre_moods: Mapping[str, frozenset[str]]
    genre_related: Mapping[str, frozenset[str]]
    theme_moods: Mapping[str, frozenset[str]]
    theme_related: Mapping[str, frozenset[str]]


class VocabularyNormalizer:
    def __init__(
        self,
        themes: set[str],
        moods: set[str],
        genres: set[str],
        *,
        genre_aliases: Mapping[str, str] | None = None,
        relations: OntologyRelations | None = None,
    ) -> None:
        self._themes = {t.lower(): t for t in themes}
        self._moods = {m.lower(): m for m in moods}
        self._genres = {g.lower(): g for g in genres}
        self._genre_aliases = {
            alias.strip().lower(): canonical
            for alias, canonical in (genre_aliases or {}).items()
        }
        self._relations = relations or OntologyRelations(
            genre_themes={},
            genre_moods={},
            genre_related={},
            theme_moods={},
            theme_related={},
        )

    # ------------------------------------------------------------------
    # Lookup
    # ------------------------------------------------------------------
    def normalize_theme(self, term: str) -> Optional[str]:
        return self._themes.get(term.strip().lower())

    def normalize_mood(self, term: str) -> Optional[str]:
        return self._moods.get(term.strip().lower())

    def normalize_genre(self, term: str) -> Optional[str]:
        key = term.strip().lower()
        if key in self._genres:
            return self._genres[key]
        alias = self._genre_aliases.get(key)
        if alias is not None:
            return self._genres.get(alias.lower(), alias)
        return None

    # ------------------------------------------------------------------
    # Public iterators (캡슐화 유지)
    # ------------------------------------------------------------------
    def themes(self) -> Iterable[str]:
        return tuple(self._themes.values())

    def moods(self) -> Iterable[str]:
        return tuple(self._moods.values())

    def genres(self) -> Iterable[str]:
        return tuple(self._genres.values())

    @property
    def relations(self) -> OntologyRelations:
        return self._relations

    def themes_for_genre(self, genre: str) -> frozenset[str]:
        canon = self.normalize_genre(genre)
        if canon is None:
            return frozenset()
        return self._relations.genre_themes.get(canon, frozenset())

    def moods_for_genre(self, genre: str) -> frozenset[str]:
        canon = self.normalize_genre(genre)
        if canon is None:
            return frozenset()
        return self._relations.genre_moods.get(canon, frozenset())

    def related_genres(self, genre: str) -> frozenset[str]:
        canon = self.normalize_genre(genre)
        if canon is None:
            return frozenset()
        return self._relations.genre_related.get(canon, frozenset())

    def moods_for_theme(self, theme: str) -> frozenset[str]:
        canon = self.normalize_theme(theme)
        if canon is None:
            return frozenset()
        return self._relations.theme_moods.get(canon, frozenset())

    def related_themes(self, theme: str) -> frozenset[str]:
        canon = self.normalize_theme(theme)
        if canon is None:
            return frozenset()
        return self._relations.theme_related.get(canon, frozenset())

    # ------------------------------------------------------------------
    # Loader
    # ------------------------------------------------------------------
    @classmethod
    def from_library_md(cls, path: Path) -> "VocabularyNormalizer":
        text = path.read_text(encoding="utf-8")
        genres = set(_parse_genre_list(text))

        themes: set[str] = set()
        moods: set[str] = set()
        genre_aliases: dict[str, str] = {}

        genre_themes: dict[str, set[str]] = {}
        genre_moods: dict[str, set[str]] = {}
        genre_related: dict[str, set[str]] = {}
        theme_moods: dict[str, set[str]] = {}
        theme_related: dict[str, set[str]] = {}

        english_to_korean: dict[str, str] = {}

        for block in _JSON_OBJECT_BLOCK.findall(text):
            try:
                data = json.loads(block)
            except json.JSONDecodeError:
                continue
            if not isinstance(data, dict):
                continue

            obj_id = str(data.get("id", ""))
            if obj_id.startswith("genre_"):
                cls._ingest_genre_ontology(
                    data,
                    genres=genres,
                    themes=themes,
                    moods=moods,
                    genre_aliases=genre_aliases,
                    english_to_korean=english_to_korean,
                    genre_themes=genre_themes,
                    genre_moods=genre_moods,
                    genre_related=genre_related,
                )
            elif obj_id.startswith("theme_"):
                cls._ingest_theme_ontology(
                    data,
                    themes=themes,
                    moods=moods,
                    theme_moods=theme_moods,
                    theme_related=theme_related,
                )

        for block in _JSON_ARRAY_BLOCK.findall(text):
            try:
                data = json.loads(block)
            except json.JSONDecodeError:
                continue
            if not isinstance(data, list):
                continue
            for item in data:
                if isinstance(item, dict) and item.get("name"):
                    moods.add(str(item["name"]))

        cls._finalize_genre_relations(
            genre_related=genre_related,
            english_to_korean=english_to_korean,
            genres=genres,
        )
        _register_genre_aliases(genres, genre_aliases)

        relations = OntologyRelations(
            genre_themes={k: frozenset(v) for k, v in genre_themes.items()},
            genre_moods={k: frozenset(v) for k, v in genre_moods.items()},
            genre_related={k: frozenset(v) for k, v in genre_related.items()},
            theme_moods={k: frozenset(v) for k, v in theme_moods.items()},
            theme_related={k: frozenset(v) for k, v in theme_related.items()},
        )
        return cls(
            themes=themes,
            moods=moods,
            genres=genres,
            genre_aliases=genre_aliases,
            relations=relations,
        )

    @staticmethod
    def _ingest_genre_ontology(
        data: dict,
        *,
        genres: set[str],
        themes: set[str],
        moods: set[str],
        genre_aliases: dict[str, str],
        english_to_korean: dict[str, str],
        genre_themes: dict[str, set[str]],
        genre_moods: dict[str, set[str]],
        genre_related: dict[str, set[str]],
    ) -> None:
        english_name = str(data.get("name", ""))
        display_ko = str(data.get("display_name_ko", ""))
        if not english_name or not display_ko:
            return

        korean = _resolve_korean_genre(display_ko, genres)
        if korean is None:
            korean = display_ko
        genres.add(korean)

        english_to_korean[english_name] = korean
        genre_aliases[english_name.lower()] = korean
        if display_ko and display_ko != korean:
            genre_aliases[display_ko.lower()] = korean

        for theme in data.get("common_themes", []):
            theme_name = str(theme)
            themes.add(theme_name)
            genre_themes.setdefault(korean, set()).add(theme_name)
        for mood in data.get("common_moods", []):
            mood_name = str(mood)
            moods.add(mood_name)
            genre_moods.setdefault(korean, set()).add(mood_name)
        for related in data.get("related_genres", []):
            genre_related.setdefault(korean, set()).add(str(related))

    @staticmethod
    def _ingest_theme_ontology(
        data: dict,
        *,
        themes: set[str],
        moods: set[str],
        theme_moods: dict[str, set[str]],
        theme_related: dict[str, set[str]],
    ) -> None:
        theme_name = str(data.get("name", ""))
        if not theme_name:
            return
        themes.add(theme_name)

        for mood in data.get("related_moods", []):
            mood_name = str(mood)
            moods.add(mood_name)
            theme_moods.setdefault(theme_name, set()).add(mood_name)
        for related in data.get("related_themes", []):
            theme_related.setdefault(theme_name, set()).add(str(related))

    @staticmethod
    def _finalize_genre_relations(
        *,
        genre_related: dict[str, set[str]],
        english_to_korean: dict[str, str],
        genres: set[str],
    ) -> None:
        for genre, related_english in list(genre_related.items()):
            resolved: set[str] = set()
            for rel in related_english:
                korean = english_to_korean.get(rel)
                if korean is None:
                    korean = _resolve_korean_genre(rel, genres)
                if korean is not None and korean != genre:
                    resolved.add(korean)
            genre_related[genre] = resolved


def _parse_genre_list(text: str) -> list[str]:
    match = _GENRE_LIST_HEADER.search(text)
    if not match:
        return []
    lines: list[str] = []
    started = False
    for line in text[match.end() :].splitlines():
        stripped = line.strip()
        if not stripped:
            if started:
                break
            continue
        if stripped == "---" or stripped.startswith("#"):
            break
        started = True
        lines.append(stripped)
    return lines


def _register_genre_aliases(genres: set[str], genre_aliases: dict[str, str]) -> None:
    for genre in genres:
        for part in re.split(r"[/·]", genre):
            token = part.strip()
            if token and token != genre:
                genre_aliases.setdefault(token.lower(), genre)
        paren = re.match(r"^(.+?)\((.+?)\)$", genre)
        if paren:
            base, inner = paren.group(1).strip(), paren.group(2).strip()
            if base:
                genre_aliases.setdefault(base.lower(), genre)
            if inner:
                genre_aliases.setdefault(inner.lower(), genre)


def _resolve_korean_genre(display_ko: str, genre_set: set[str]) -> str | None:
    if not display_ko:
        return None
    return display_ko if display_ko in genre_set else None


__all__ = ["OntologyRelations", "VocabularyNormalizer"]
