"""Neo4j + PostgreSQL 스키마 부트스트랩 스크립트.

사용 예
-------
$ python -m scripts.bootstrap_schema

환경변수
--------
- NEO4J_URI / NEO4J_USER / NEO4J_PASSWORD / NEO4J_DATABASE
- PG_HOST / PG_PORT / PG_DATABASE / PG_USER / PG_PASSWORD
- EMBED_DIMENSION  (기본 1024)
"""

from __future__ import annotations

import logging

from src.config.settings import get_settings
from src.graph.client import Neo4jClient
from src.persistence.chat_history import ChatHistoryStore


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s :: %(message)s",
    )

    settings = get_settings()

    # 1) Neo4j 스키마
    with Neo4jClient(settings.neo4j) as neo:
        neo.init_schema(embedding_dim=settings.embedding.dimension)

    # 2) Postgres 채팅 이력 스키마
    chat = ChatHistoryStore(settings.postgres)
    chat.init_schema()

    logging.getLogger(__name__).info("All schemas initialized.")


if __name__ == "__main__":
    main()
