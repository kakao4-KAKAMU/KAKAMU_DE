"""기존 Movie.title → MovieTitle 노드 백필 (1회 실행용).

사용 예
-------
$ python -m scripts.migrate_movie_titles
"""

from __future__ import annotations

import logging

from src.config.settings import get_settings
from src.graph.client import Neo4jClient
from src.graph.cypher_statements import MIGRATE_MOVIE_TITLES_FROM_MOVIE

logger = logging.getLogger(__name__)


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s :: %(message)s",
    )
    settings = get_settings()
    with Neo4jClient(settings.neo4j) as neo:
        records = neo.execute_write(MIGRATE_MOVIE_TITLES_FROM_MOVIE, {})
        migrated = records[0]["migrated"] if records else 0
        logger.info("Migrated %s MovieTitle node(s) from Movie.title", migrated)


if __name__ == "__main__":
    main()
