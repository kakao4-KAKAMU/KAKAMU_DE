"""Neo4j CandidateTerm 관찰 저장."""

from __future__ import annotations

from datetime import datetime
from typing import Optional, Sequence

from src.graph.client import Neo4jClient

OBSERVE_CYPHER = """
MERGE (c:CandidateTerm {normalized: $normalized, kind: $kind})
ON CREATE SET c.term = $term,
              c.count = 1,
              c.first_seen = datetime(),
              c.last_seen = datetime()
ON MATCH SET c.count = c.count + 1,
             c.last_seen = datetime(),
             c.term = coalesce(c.term, $term)
WITH c
CALL {
  WITH c
  WITH c WHERE $embedding IS NOT NULL
  SET c.embedding = $embedding
  RETURN 1 AS _
}
RETURN c.normalized AS normalized, c.count AS count
"""

LIST_READY_CYPHER = """
MATCH (c:CandidateTerm)
WHERE c.count >= $min_count
  AND duration.between(c.first_seen, datetime()).days >= $min_days
RETURN c.normalized AS normalized, c.kind AS kind, c.term AS term,
       c.count AS count, c.embedding AS embedding
"""


class CandidateStore:
    def __init__(self, neo4j: Neo4jClient) -> None:
        self._neo4j = neo4j

    def observe(
        self,
        *,
        term: str,
        normalized: str,
        kind: str,
        embedding: Optional[Sequence[float]] = None,
    ) -> int:
        rows = self._neo4j.execute_write(
            OBSERVE_CYPHER,
            {
                "term": term,
                "normalized": normalized,
                "kind": kind,
                "embedding": list(embedding) if embedding else None,
            },
        )
        return int(rows[0]["count"]) if rows else 1

    def list_promotion_candidates(
        self, *, min_count: int, min_days: int
    ) -> list[dict]:
        return self._neo4j.execute_read(
            LIST_READY_CYPHER,
            {"min_count": min_count, "min_days": min_days},
        )


__all__ = ["CandidateStore"]
