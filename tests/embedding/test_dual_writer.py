"""Tests for plot embedding dual writer."""

from __future__ import annotations

import pytest

from src.config.settings import EmbeddingSettings
from src.embedding.dual_writer import (
    PlotEmbeddingDualWriter,
    build_movie_embedding_set_clause,
    build_upsert_movie_embedding_cypher,
)
from src.embedding.version_registry import EmbeddingVersion, EmbeddingVersionRegistry
from tests.embedding.test_version_registry import FakeStore


@pytest.fixture
def embedding_1024() -> list[float]:
    return [0.1] * 1024


@pytest.fixture
def writer_with_versions(embedding_1024: list[float]) -> tuple[PlotEmbeddingDualWriter, FakeStore]:
    store = FakeStore()
    settings = EmbeddingSettings(dimension=1024)
    registry = EmbeddingVersionRegistry(store, settings=settings)
    registry.register_version("1", role="active")
    registry.register_version("2", role="shadow")

    class WriteCapture(FakeStore):
        def execute_write(self, cypher: str, params: dict | None = None) -> list[dict]:
            self.last_cypher = cypher
            self.last_params = params or {}
            return [{"movie_id": params.get("movie_id")}]

    capture = WriteCapture()
    capture.nodes = store.nodes
    capture.by_role = store.by_role
    w = PlotEmbeddingDualWriter(capture, EmbeddingVersionRegistry(capture, settings=settings))
    return w, capture


def test_build_set_clause_two_versions() -> None:
    versions = [
        EmbeddingVersion("1", 1024, "active", "m", "plot_embedding_v1"),
        EmbeddingVersion("2", 1024, "shadow", "m", "plot_embedding_v2"),
    ]
    clause = build_movie_embedding_set_clause(versions)
    assert "plot_embedding_v1 = $embedding" in clause
    assert "plot_embedding_v2 = $embedding" in clause


def test_build_cypher_includes_movie_id() -> None:
    versions = [EmbeddingVersion("1", 1024, "active", "m", "plot_embedding_v1")]
    cypher = build_upsert_movie_embedding_cypher(versions)
    assert "movie_id: $movie_id" in cypher
    assert "plot_embedding = $plot_embedding" in cypher
    assert "plot_embedding_v1" in cypher


def test_dual_write_executes_both_properties(
    writer_with_versions: tuple[PlotEmbeddingDualWriter, FakeStore],
    embedding_1024: list[float],
) -> None:
    writer, store = writer_with_versions
    writer.write_movie_plot_embedding("mv-1", embedding_1024)
    assert "plot_embedding_v1" in store.last_cypher
    assert "plot_embedding_v2" in store.last_cypher
    assert store.last_params["movie_id"] == "mv-1"
    assert len(store.last_params["plot_embedding"]) == 1024


def test_target_versions_requires_registry() -> None:
    store = FakeStore()
    registry = EmbeddingVersionRegistry(store, settings=EmbeddingSettings(dimension=1024))
    writer = PlotEmbeddingDualWriter(store, registry)
    with pytest.raises(RuntimeError, match="No active"):
        writer.write_movie_plot_embedding("x", [0.0] * 1024)
