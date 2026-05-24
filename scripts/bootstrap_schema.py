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
from pathlib import Path

from src.chat.checkpoint import setup_checkpoint_tables
from src.config.settings import get_settings
from src.graph.client import Neo4jClient
from src.persistence.chat_history import ChatHistoryStore
from src.persistence.db import get_connection

ROOT = Path(__file__).resolve().parents[1]


def _run_sql_files(settings) -> None:
    sql_files = [
        ROOT / "src" / "persistence" / "outbox_schema.sql",
        ROOT / "src" / "persistence" / "eval_schema.sql",
        ROOT / "src" / "recommend" / "bandit_schema.sql",
    ]
    with get_connection(settings.postgres) as conn:
        with conn.cursor() as cur:
            for path in sql_files:
                if path.exists():
                    cur.execute(path.read_text(encoding="utf-8"))
        conn.commit()


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s :: %(message)s",
    )

    settings = get_settings()

    # 1) Neo4j 스키마
    with Neo4jClient(settings.neo4j) as neo:
        neo.init_schema(embedding_dim=settings.embedding.dimension)

    # 2) Postgres 스키마 (chat + outbox + eval + bandit)
    chat = ChatHistoryStore(settings.postgres)
    chat.init_schema()
    _run_sql_files(settings)

    # 3) LangGraph PostgresSaver checkpoint 테이블
    setup_checkpoint_tables(settings.postgres)

    logging.getLogger(__name__).info("All schemas initialized.")


if __name__ == "__main__":
    main()
