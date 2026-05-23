"""Tests for embedding version registry."""

from __future__ import annotations

import pytest

from src.config.settings import EmbeddingSettings
from src.embedding.version_registry import (
    EmbeddingVersion,
    EmbeddingVersionRegistry,
    plot_embedding_property,
    register_version,
)


class FakeStore:
    def __init__(self) -> None:
        self.nodes: dict[str, dict] = {}
        self.by_role: dict[str, str] = {}

    def execute_read(self, cypher: str, params: dict | None = None) -> list[dict]:
        params = params or {}
        if "role" in params:
            vid = self.by_role.get(params["role"])
            if not vid:
                return []
            return [self.nodes[vid]]
        return []

    def execute_write(self, cypher: str, params: dict | None = None) -> list[dict]:
        params = params or {}
        if "version" in params and "MERGE" in cypher:
            vid = params["version"]
            row = {
                "version": vid,
                "dimension": params["dimension"],
                "role": params["role"],
                "model_name": params["model_name"],
                "property_key": params["property_key"],
                "created_at": None,
            }
            old_role = self.nodes.get(vid, {}).get("role")
            if old_role and old_role in self.by_role:
                del self.by_role[old_role]
            self.nodes[vid] = row
            self.by_role[params["role"]] = vid
            return [row]
        if "promote" in cypher.lower() or "shadow.role = 'active'" in cypher:
            active_id = self.by_role.get("active")
            shadow_id = self.by_role.get("shadow")
            if not active_id or not shadow_id:
                return []
            self.nodes[active_id]["role"] = "retired"
            self.nodes[shadow_id]["role"] = "active"
            del self.by_role["active"]
            del self.by_role["shadow"]
            self.by_role["active"] = shadow_id
            return [self.nodes[shadow_id]]
        return []


@pytest.fixture
def settings() -> EmbeddingSettings:
    return EmbeddingSettings(dimension=1024, model_name="BAAI/bge-m3")


@pytest.fixture
def registry(settings: EmbeddingSettings) -> EmbeddingVersionRegistry:
    return EmbeddingVersionRegistry(FakeStore(), settings=settings)


def test_plot_embedding_property() -> None:
    assert plot_embedding_property("1") == "plot_embedding_v1"


def test_register_and_get_active(registry: EmbeddingVersionRegistry) -> None:
    v = registry.register_version("1", role="active")
    assert isinstance(v, EmbeddingVersion)
    assert v.dimension == 1024
    assert v.property_key == "plot_embedding_v1"
    active = registry.get_active_version()
    assert active is not None
    assert active.version == "1"
    assert active.role == "active"


def test_write_targets_includes_shadow(registry: EmbeddingVersionRegistry) -> None:
    registry.register_version("1", role="active")
    registry.register_version("2", role="shadow")
    targets = registry.write_targets()
    assert [t.version for t in targets] == ["1", "2"]


def test_vector_index_statements_for_version() -> None:
    from src.graph.cypher_statements import (
        vector_index_statements,
        vector_index_statements_for_version,
    )

    versioned = vector_index_statements_for_version("2", 1024)
    assert len(versioned) == 1
    assert "plot_embedding_v2" in versioned[0]
    assert "movie_plot_vec_2" in versioned[0]
    assert len(vector_index_statements(1024)) == 3


def test_module_register_version_helper(settings: EmbeddingSettings) -> None:
    store = FakeStore()
    v = register_version("3", role="shadow", client=store, settings=settings)
    assert v.version == "3"
    shadow = EmbeddingVersionRegistry(store, settings=settings).get_shadow_version()
    assert shadow is not None
    assert shadow.version == "3"
