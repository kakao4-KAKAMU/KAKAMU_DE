"""Dual-write feed/comment summary embeddings to active and shadow version properties."""

from __future__ import annotations

from typing import Literal, Mapping, Optional, Sequence

from src.embedding.version_registry import EmbeddingVersionRegistry
from src.graph.client import Neo4jClient
from src.graph.cypher_statements.comment import build_update_comment_summary_embedding
from src.graph.cypher_statements.feed import build_update_feed_summary_embedding
from src.graph.cypher_statements.properties import summary_embedding_property

SummaryEntityType = Literal["feed", "comment"]


class SummaryEmbeddingDualWriter:
    """Writes the same vector to summary_embedding + summary_embedding_vN targets."""

    def __init__(
        self,
        neo4j: Neo4jClient,
        registry: EmbeddingVersionRegistry,
    ) -> None:
        self._neo4j = neo4j
        self._registry = registry

    def _version_properties(self) -> list[str]:
        return [
            summary_embedding_property(v.version)
            for v in self._registry.write_targets()
        ]

    def write_summary_embedding(
        self,
        entity_type: SummaryEntityType,
        entity_id: str,
        embedding: Sequence[float],
        *,
        extra_params: Optional[Mapping[str, object]] = None,
    ) -> list[dict]:
        version_props = self._version_properties()
        if entity_type == "feed":
            cypher = build_update_feed_summary_embedding(version_props)
            params: dict[str, object] = {
                "feed_id": entity_id,
                "summary_embedding": list(embedding),
            }
        else:
            cypher = build_update_comment_summary_embedding(version_props)
            params = {
                "comment_id": entity_id,
                "summary_embedding": list(embedding),
            }
        if extra_params:
            params.update(extra_params)
        return self._neo4j.execute_write(cypher, params)


__all__ = ["SummaryEmbeddingDualWriter", "SummaryEntityType"]
