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


def main() -> None:
    norm = VocabularyNormalizer.from_library_md(LIBRARY)
    settings = get_settings()
    with Neo4jClient(settings.neo4j) as neo:
        for g in norm.genres():
            neo.execute_write("MERGE (g:Genre {name: $name})", {"name": g})
        for t in norm.themes():
            neo.execute_write("MERGE (t:Theme {name: $name})", {"name": t})
        for m in norm.moods():
            neo.execute_write("MERGE (m:Mood {name: $name})", {"name": m})
    logger.info(
        "Seeded genres=%d themes=%d moods=%d",
        len(list(norm.genres())),
        len(list(norm.themes())),
        len(list(norm.moods())),
    )


if __name__ == "__main__":
    main()
