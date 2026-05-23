"""임베딩 버전 메타 (Neo4j + in-memory cache)."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional

from src.graph.client import Neo4jClient


class VersionStatus(str, Enum):
    ACTIVE = "active"
    SHADOW = "shadow"
    DEPRECATED = "deprecated"


@dataclass(frozen=True)
class EmbeddingVersion:
    name: str
    model: str
    dimension: int
    status: VersionStatus


MERGE_VERSION = """
MERGE (v:EmbeddingVersionMeta {name: $name})
SET v.model = $model,
    v.dimension = $dimension,
    v.status = $status,
    v.updated_at = datetime()
"""

GET_BY_STATUS = """
MATCH (v:EmbeddingVersionMeta {status: $status})
RETURN v.name AS name, v.model AS model, v.dimension AS dimension, v.status AS status
LIMIT 1
"""


class VersionRegistry:
    def __init__(self, neo4j: Neo4jClient) -> None:
        self._neo4j = neo4j

    def register_version(self, version: EmbeddingVersion) -> None:
        self._neo4j.execute_write(
            MERGE_VERSION,
            {
                "name": version.name,
                "model": version.model,
                "dimension": version.dimension,
                "status": version.status.value,
            },
        )

    def get_active_version(self) -> Optional[EmbeddingVersion]:
        rows = self._neo4j.execute_read(GET_BY_STATUS, {"status": VersionStatus.ACTIVE.value})
        if not rows:
            return None
        row = rows[0]
        return EmbeddingVersion(
            name=row["name"],
            model=row["model"],
            dimension=int(row["dimension"]),
            status=VersionStatus(row["status"]),
        )

    def get_shadow_version(self) -> Optional[EmbeddingVersion]:
        rows = self._neo4j.execute_read(GET_BY_STATUS, {"status": VersionStatus.SHADOW.value})
        if not rows:
            return None
        row = rows[0]
        return EmbeddingVersion(
            name=row["name"],
            model=row["model"],
            dimension=int(row["dimension"]),
            status=VersionStatus(row["status"]),
        )

    def promote_shadow_to_active(self, shadow_name: str) -> None:
        self._neo4j.execute_write(
            """
            MATCH (old:EmbeddingVersionMeta {status: 'active'})
            SET old.status = 'deprecated'
            WITH 1 AS _
            MATCH (shadow:EmbeddingVersionMeta {name: $name})
            SET shadow.status = 'active', shadow.updated_at = datetime()
            """,
            {"name": shadow_name},
        )


def property_name_for_version(version_name: str, base: str = "plot_embedding") -> str:
    return f"{base}_v{version_name.replace('.', '_')}"


__all__ = [
    "EmbeddingVersion",
    "VersionStatus",
    "VersionRegistry",
    "property_name_for_version",
]
