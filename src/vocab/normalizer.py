"""폐쇄형 vocabulary 정규화.

SOLID
-----
- SRP : 표제어 매핑 lookup만 담당. 외부에서는 ``normalize_*`` 와 public iterator 만 사용.
- OCP : ``from_library_md`` 등 alternative loader 를 추가해 확장한다.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Iterable, Optional

_JSON_BLOCK = re.compile(r"```json\s*(\{.*?\})\s*```", re.DOTALL)


class VocabularyNormalizer:
    def __init__(self, themes: set[str], moods: set[str], genres: set[str]) -> None:
        self._themes = {t.lower(): t for t in themes}
        self._moods = {m.lower(): m for m in moods}
        self._genres = {g.lower(): g for g in genres}

    # ------------------------------------------------------------------
    # Lookup
    # ------------------------------------------------------------------
    def normalize_theme(self, term: str) -> Optional[str]:
        return self._themes.get(term.strip().lower())

    def normalize_mood(self, term: str) -> Optional[str]:
        return self._moods.get(term.strip().lower())

    def normalize_genre(self, term: str) -> Optional[str]:
        return self._genres.get(term.strip().lower())

    # ------------------------------------------------------------------
    # Public iterators (캡슐화 유지)
    # ------------------------------------------------------------------
    def themes(self) -> Iterable[str]:
        return tuple(self._themes.values())

    def moods(self) -> Iterable[str]:
        return tuple(self._moods.values())

    def genres(self) -> Iterable[str]:
        return tuple(self._genres.values())

    # ------------------------------------------------------------------
    # Loader
    # ------------------------------------------------------------------
    @classmethod
    def from_library_md(cls, path: Path) -> "VocabularyNormalizer":
        text = path.read_text(encoding="utf-8")
        themes: set[str] = set()
        moods: set[str] = set()
        genres: set[str] = set()
        for block in _JSON_BLOCK.findall(text):
            try:
                data = json.loads(block)
            except json.JSONDecodeError:
                continue
            name = data.get("name") or data.get("id", "").replace("genre_", "")
            if "genre_" in str(data.get("id", "")):
                genres.add(str(name))
            for t in data.get("common_themes", []):
                themes.add(str(t))
            for m in data.get("common_moods", []):
                moods.add(str(m))
        return cls(themes=themes, moods=moods, genres=genres)


__all__ = ["VocabularyNormalizer"]
