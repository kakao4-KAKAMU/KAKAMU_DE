"""Neo4j 클라이언트 래퍼.

설계 원칙
---------
- SRP : 본 클래스는 "Cypher 실행" 만 담당. 비즈니스 로직(추천/온톨로지) 분리.
- DIP : 상위 모듈(extractor/recommend) 은 이 인터페이스에만 의존한다.
- LSP : sync/async 구현체를 분리해 추후 교체 가능하도록 한다.
"""

from __future__ import annotations

import logging
from contextlib import contextmanager
from typing import Any, Iterable, Iterator, List, Mapping, Optional

from neo4j import Driver, GraphDatabase, Session

from src.config.settings import Neo4jSettings, get_settings
from src.graph.cypher_statements import (
    FULLTEXT_INDEXES,
    NODE_CONSTRAINTS,
    NODE_PROPERTY_INDEXES,
    SEED_CATEGORIES,
    SEED_EMOTIONS,
    SEED_MERGE_CATEGORY,
    SEED_MERGE_EMOTION,
    vector_index_statements,
)

logger = logging.getLogger(__name__)


class Neo4jClient:
    """경량 Neo4j 드라이버 래퍼."""

    def __init__(self, settings: Optional[Neo4jSettings] = None) -> None:
        self._settings = settings or get_settings().neo4j
        self._driver: Driver = GraphDatabase.driver(
            self._settings.uri,
            auth=(self._settings.user, self._settings.password),
            max_connection_lifetime=3600.0,
            max_connection_pool_size=20,
            connection_timeout=30.0,
            liveness_check_timeout=30.0,
        )

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------
    def close(self) -> None:
        self._driver.close()

    def __enter__(self) -> "Neo4jClient":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    @contextmanager
    def session(self) -> Iterator[Session]:
        with self._driver.session(database=self._settings.database) as s:
            yield s

    # ------------------------------------------------------------------
    # Generic exec
    # ------------------------------------------------------------------
    def execute_write(
        self, cypher: str, params: Optional[Mapping[str, Any]] = None
    ) -> List[dict]:
        with self.session() as s:
            result = s.execute_write(
                lambda tx: list(tx.run(cypher, params or {}))
            )
            return [r.data() for r in result]

    def execute_read(
        self, cypher: str, params: Optional[Mapping[str, Any]] = None
    ) -> List[dict]:
        with self.session() as s:
            result = s.execute_read(
                lambda tx: list(tx.run(cypher, params or {}))
            )
            return [r.data() for r in result]

    def run_many(self, statements: Iterable[str]) -> None:
        """여러 DDL/DML 을 차례로 실행. 멱등 보장 statement 전용."""
        with self.session() as s:
            for stmt in statements:
                stmt = stmt.strip()
                if not stmt:
                    continue
                logger.debug("Running Cypher: %s", stmt.splitlines()[0])
                s.run(stmt)

    # ------------------------------------------------------------------
    # Schema bootstrap
    # ------------------------------------------------------------------
    def init_schema(self, embedding_dim: int) -> None:
        """제약/인덱스/벡터인덱스/시드 데이터를 멱등하게 적용한다."""
        logger.info("Initializing Neo4j schema (embedding_dim=%d)", embedding_dim)

        self.run_many(NODE_CONSTRAINTS)
        self.run_many(NODE_PROPERTY_INDEXES)
        self.run_many(FULLTEXT_INDEXES)
        self.run_many(vector_index_statements(embedding_dim))

        with self.session() as s:
            s.run(SEED_MERGE_CATEGORY, {"categories": SEED_CATEGORIES})
            s.run(SEED_MERGE_EMOTION, {"emotions": SEED_EMOTIONS})

        logger.info("Neo4j schema initialization complete.")


__all__ = ["Neo4jClient"]
