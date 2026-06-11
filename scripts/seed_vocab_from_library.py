"""genre_theme_mood_library.md → Neo4j Genre/Theme/Mood 시드."""

from __future__ import annotations

import logging
from pathlib import Path

from src.config.settings import get_settings
from src.graph.client import Neo4jClient
from src.vocab.normalizer import VocabularyNormalizer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parents[1]
LIBRARY = ROOT / "docs" / "genre_theme_mood_library.md"

MERGE_GENRE: str = "MERGE (g:Genre {name: $name})"
MERGE_THEME: str = "MERGE (t:Theme {name: $name})"
MERGE_MOOD: str = "MERGE (m:Mood {name: $name})"

MERGE_GENRE_THEME: str = """
MATCH (g:Genre {name: $genre})
MATCH (t:Theme {name: $theme})
MERGE (g)-[:COMMON_THEME]->(t)
"""

MERGE_GENRE_MOOD: str = """
MATCH (g:Genre {name: $genre})
MATCH (m:Mood {name: $mood})
MERGE (g)-[:COMMON_MOOD]->(m)
"""

MERGE_GENRE_RELATED: str = """
MATCH (g1:Genre {name: $from_genre})
MATCH (g2:Genre {name: $to_genre})
MERGE (g1)-[:RELATED_TO]->(g2)
"""

MERGE_THEME_RELATED: str = """
MATCH (t1:Theme {name: $from_theme})
MATCH (t2:Theme {name: $to_theme})
MERGE (t1)-[:RELATED_TO]->(t2)
"""

MERGE_THEME_MOOD: str = """
MATCH (t:Theme {name: $theme})
MATCH (m:Mood {name: $mood})
MERGE (t)-[:SUGGESTS_MOOD]->(m)
"""


def main() -> None:
    norm = VocabularyNormalizer.from_library_md(LIBRARY)
    rel = norm.relations
    settings = get_settings()
    with Neo4jClient(settings.neo4j) as neo:
        for g in norm.genres():
            neo.execute_write(MERGE_GENRE, {"name": g})
        for t in norm.themes():
            neo.execute_write(MERGE_THEME, {"name": t})
        for m in norm.moods():
            neo.execute_write(MERGE_MOOD, {"name": m})

        for genre, themes in rel.genre_themes.items():
            for theme in themes:
                neo.execute_write(MERGE_GENRE_THEME, {"genre": genre, "theme": theme})
        for genre, moods in rel.genre_moods.items():
            for mood in moods:
                neo.execute_write(MERGE_GENRE_MOOD, {"genre": genre, "mood": mood})
        for genre, related in rel.genre_related.items():
            for other in related:
                neo.execute_write(
                    MERGE_GENRE_RELATED,
                    {"from_genre": genre, "to_genre": other},
                )
        for theme, related in rel.theme_related.items():
            for other in related:
                neo.execute_write(
                    MERGE_THEME_RELATED,
                    {"from_theme": theme, "to_theme": other},
                )
        for theme, moods in rel.theme_moods.items():
            for mood in moods:
                neo.execute_write(MERGE_THEME_MOOD, {"theme": theme, "mood": mood})

    logger.info(
        "Seeded genres=%d themes=%d moods=%d "
        "genre_theme=%d genre_mood=%d genre_related=%d "
        "theme_related=%d theme_mood=%d",
        len(list(norm.genres())),
        len(list(norm.themes())),
        len(list(norm.moods())),
        sum(len(v) for v in rel.genre_themes.values()),
        sum(len(v) for v in rel.genre_moods.values()),
        sum(len(v) for v in rel.genre_related.values()),
        sum(len(v) for v in rel.theme_related.values()),
        sum(len(v) for v in rel.theme_moods.values()),
    )


if __name__ == "__main__":
    main()
