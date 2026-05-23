"""Dual-write movie plot embeddings to active and shadow version properties."""

from __future__ import annotations

from typing import Mapping, Optional, Sequence

from src.embedding.version_registry import EmbeddingVersion, EmbeddingVersionRegistry
from src.graph.client import Neo4jClient


def build_movie_embedding_set_clause(versions: Sequence[EmbeddingVersion]) -> str:
    """Build SET fragment: m.plot_embedding_vN = $embedding, ..."""
    if not versions:
        raise ValueError("At least one embedding version is required")
    parts = [f"m.{v.property_key} = $embedding" for v in versions]
    return ",\n    ".join(parts)


def build_upsert_movie_embedding_cypher(versions: Sequence[EmbeddingVersion]) -> str:
    set_clause = build_movie_embedding_set_clause(versions)
    return f"""
MATCH (m:Movie {{movie_id: $movie_id}})
SET {set_clause},
    m.updated_at = datetime()
RETURN m.movie_id AS movie_id
"""


class PlotEmbeddingDualWriter:
    """Writes the same vector to all dual-write target properties."""

    def __init__(
        self,
        neo4j: Neo4jClient,
        registry: EmbeddingVersionRegistry,
    ) -> None:
        self._neo4j = neo4j
        self._registry = registry

    def target_versions(self) -> list[EmbeddingVersion]:
        return self._registry.write_targets()

    def write_movie_plot_embedding(
        self,
        movie_id: str,
        embedding: Sequence[float],
        *,
        extra_params: Optional[Mapping[str, object]] = None,
    ) -> list[dict]:
        versions = self.target_versions()
        if not versions:
            raise RuntimeError("No active or shadow embedding version configured")
        cypher = build_upsert_movie_embedding_cypher(versions)
        params: dict[str, object] = {
            "movie_id": movie_id,
            "embedding": list(embedding),
        }
        if extra_params:
            params.update(extra_params)
        return self._neo4j.execute_write(cypher, params)


__all__ = [
    "PlotEmbeddingDualWriter",
    "build_movie_embedding_set_clause",
    "build_upsert_movie_embedding_cypher",
]
