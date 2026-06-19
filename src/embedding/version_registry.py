"""Neo4j-backed embedding version registry (:EmbeddingVersionMeta)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal, Optional, Protocol

from src.config.settings import EmbeddingSettings, get_settings
from src.graph.client import Neo4jClient

VersionRole = Literal["active", "shadow", "retired"]


def plot_embedding_property(version: str) -> str:
    """Versioned Movie plot embedding property name."""
    return f"plot_embedding_v{version}"


@dataclass(frozen=True)
class EmbeddingVersion:
    """Registered embedding schema version."""

    version: str
    dimension: int
    role: VersionRole
    model_name: str
    property_key: str
    created_at: Optional[datetime] = None

    @classmethod
    def from_record(cls, record: dict) -> "EmbeddingVersion":
        created = record.get("created_at")
        if created is not None and not isinstance(created, datetime):
            created = None
        return cls(
            version=str(record["version"]),
            dimension=int(record["dimension"]),
            role=record["role"],
            model_name=str(record.get("model_name") or ""),
            property_key=str(record.get("property_key") or plot_embedding_property(str(record["version"]))),
            created_at=created,
        )


class VersionStore(Protocol):
    def execute_read(self, cypher: str, params: Optional[dict] = None) -> list[dict]: ...

    def execute_write(self, cypher: str, params: Optional[dict] = None) -> list[dict]: ...


_FETCH_BY_ROLE = """
MATCH (m:EmbeddingVersionMeta {role: $role})
RETURN m.version AS version,
       m.dimension AS dimension,
       m.role AS role,
       m.model_name AS model_name,
       m.property_key AS property_key,
       m.created_at AS created_at
ORDER BY m.created_at DESC
LIMIT 1
"""

_REGISTER_VERSION = """
MERGE (m:EmbeddingVersionMeta {version: $version})
SET m.dimension = $dimension,
    m.role = $role,
    m.model_name = $model_name,
    m.property_key = $property_key,
    m.updated_at = datetime(),
    m.created_at = coalesce(m.created_at, datetime())
RETURN m.version AS version,
       m.dimension AS dimension,
       m.role AS role,
       m.model_name AS model_name,
       m.property_key AS property_key,
       m.created_at AS created_at
"""

_PROMOTE_SHADOW = """
MATCH (shadow:EmbeddingVersionMeta {role: 'shadow', version: $version})
OPTIONAL MATCH (active:EmbeddingVersionMeta {role: 'active'})
WHERE active IS NULL OR active <> shadow
FOREACH (_ IN CASE WHEN active IS NOT NULL THEN [1] ELSE [] END |
  SET active.role = 'retired',
      active.updated_at = datetime()
)
SET shadow.role = 'active',
    shadow.updated_at = datetime()
RETURN shadow.version AS version,
       shadow.dimension AS dimension,
       shadow.role AS role,
       shadow.model_name AS model_name,
       shadow.property_key AS property_key,
       shadow.created_at AS created_at
"""

class EmbeddingVersionRegistry:
    """CRUD for :EmbeddingVersionMeta nodes."""

    def __init__(
        self,
        store: VersionStore,
        *,
        settings: Optional[EmbeddingSettings] = None,
    ) -> None:
        self._store = store
        self._settings = settings or get_settings().embedding

    def get_active_version(self) -> Optional[EmbeddingVersion]:
        rows = self._store.execute_read(_FETCH_BY_ROLE, {"role": "active"})
        return EmbeddingVersion.from_record(rows[0]) if rows else None

    def get_shadow_version(self) -> Optional[EmbeddingVersion]:
        rows = self._store.execute_read(_FETCH_BY_ROLE, {"role": "shadow"})
        return EmbeddingVersion.from_record(rows[0]) if rows else None

    def register_version(
        self,
        version: str,
        *,
        role: VersionRole,
        dimension: Optional[int] = None,
        model_name: Optional[str] = None,
    ) -> EmbeddingVersion:
        dim = dimension if dimension is not None else self._settings.dimension
        model = model_name if model_name is not None else self._settings.model_name
        prop = plot_embedding_property(version)
        rows = self._store.execute_write(
            _REGISTER_VERSION,
            {
                "version": version,
                "dimension": dim,
                "role": role,
                "model_name": model,
                "property_key": prop,
            },
        )
        if not rows:
            raise RuntimeError(f"Failed to register embedding version {version!r}")
        return EmbeddingVersion.from_record(rows[0])

    def promote_shadow_to_active(self, version: str) -> Optional[EmbeddingVersion]:
        rows = self._store.execute_write(_PROMOTE_SHADOW, {"version": version})
        return EmbeddingVersion.from_record(rows[0]) if rows else None

    def write_targets(self) -> list[EmbeddingVersion]:
        """Active and optional shadow versions for dual-write."""
        targets: list[EmbeddingVersion] = []
        active = self.get_active_version()
        if active:
            targets.append(active)
        shadow = self.get_shadow_version()
        if shadow:
            targets.append(shadow)
        return targets


def get_active_version(
    client: Optional[VersionStore] = None,
    *,
    settings: Optional[EmbeddingSettings] = None,
) -> Optional[EmbeddingVersion]:
    """Module helper: return the active embedding version."""
    store = client or Neo4jClient()
    return EmbeddingVersionRegistry(store, settings=settings).get_active_version()


def register_version(
    version: str,
    *,
    role: VersionRole,
    client: Optional[VersionStore] = None,
    dimension: Optional[int] = None,
    model_name: Optional[str] = None,
    settings: Optional[EmbeddingSettings] = None,
) -> EmbeddingVersion:
    """Module helper: register a version in Neo4j."""
    store = client or Neo4jClient()
    return EmbeddingVersionRegistry(store, settings=settings).register_version(
        version,
        role=role,
        dimension=dimension,
        model_name=model_name,
    )


__all__ = [
    "EmbeddingVersion",
    "EmbeddingVersionRegistry",
    "VersionRole",
    "VersionStore",
    "get_active_version",
    "plot_embedding_property",
    "register_version",
]
