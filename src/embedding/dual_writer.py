"""Active + shadow 임베딩 dual-write."""

from __future__ import annotations

from typing import Sequence

from src.embedding.version_registry import VersionRegistry, property_name_for_version
from src.graph.client import Neo4jClient


class DualEmbeddingWriter:
    def __init__(self, neo4j: Neo4jClient, registry: VersionRegistry) -> None:
        self._neo4j = neo4j
        self._registry = registry

    def write_movie_plot_embedding(
        self, movie_id: str, vector: Sequence[float]
    ) -> dict[str, str]:
        """Returns mapping version_name -> property_name written."""
        written: dict[str, str] = {}
        versions = []
        active = self._registry.get_active_version()
        shadow = self._registry.get_shadow_version()
        if active:
            versions.append(active)
        if shadow:
            versions.append(shadow)

        if not versions:
            prop = "plot_embedding"
            self._neo4j.execute_write(
                "MATCH (m:Movie {movie_id: $movie_id}) SET m.plot_embedding = $vec",
                {"movie_id": movie_id, "vec": list(vector)},
            )
            written["default"] = prop
            return written

        for ver in versions:
            prop = property_name_for_version(ver.name)
            self._neo4j.execute_write(
                f"MATCH (m:Movie {{movie_id: $movie_id}}) SET m.{prop} = $vec",
                {"movie_id": movie_id, "vec": list(vector)},
            )
            written[ver.name] = prop
        return written


__all__ = ["DualEmbeddingWriter"]
