"""Tests for embedding property naming helpers."""

from __future__ import annotations

from src.graph.cypher_statements.properties import (
    BASE_PLOT_EMBEDDING,
    BASE_SUMMARY_EMBEDDING,
    build_embedding_set_clause,
    plot_embedding_property,
    summary_embedding_property,
    versioned_embedding_property,
)


def test_summary_embedding_property() -> None:
    assert summary_embedding_property("2") == "summary_embedding_v2"
    assert summary_embedding_property("1.0") == "summary_embedding_v1_0"


def test_plot_embedding_property() -> None:
    assert plot_embedding_property("1") == "plot_embedding_v1"


def test_build_embedding_set_clause_includes_base_and_versions() -> None:
    clause = build_embedding_set_clause(
        "f",
        BASE_SUMMARY_EMBEDDING,
        "summary_embedding",
        ["summary_embedding_v1", "summary_embedding_v2"],
    )
    assert "f.summary_embedding = $summary_embedding" in clause
    assert "f.summary_embedding_v1 = $summary_embedding" in clause
    assert "f.summary_embedding_v2 = $summary_embedding" in clause


def test_versioned_embedding_property_generic() -> None:
    assert versioned_embedding_property(BASE_PLOT_EMBEDDING, "3") == "plot_embedding_v3"
