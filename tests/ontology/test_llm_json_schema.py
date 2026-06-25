"""build_llm_json_schema / build_strict_object_schema 회귀 테스트."""

from __future__ import annotations

from typing import Any

from src.ontology.schema import (
    CommentOntology,
    FeedOntology,
    KEYWORD_KIND_VALUES,
    MoviePlotOntology,
    QueryOntologyAnalysis,
    SCHEMA_VERSION_VALUES,
    build_llm_json_schema,
)


def _assert_strict_object(node: dict[str, Any]) -> None:
    if node.get("type") == "object" and "properties" in node:
        assert node.get("additionalProperties") is False
        assert set(node["required"]) == set(node["properties"].keys())
        for prop in node["properties"].values():
            _assert_strict_object(prop)
    if node.get("type") == "array" and "items" in node:
        _assert_strict_object(node["items"])
    if "anyOf" in node:
        for item in node["anyOf"]:
            _assert_strict_object(item)


def test_movie_plot_llm_schema_is_strict_and_excludes_created_at() -> None:
    wrapper = build_llm_json_schema(MoviePlotOntology, name="movie_knowledge_ontology")
    schema = wrapper["schema"]

    assert wrapper["strict"] is True
    assert "created_at" not in schema["properties"]
    assert schema["properties"]["schema_version"]["enum"] == SCHEMA_VERSION_VALUES
    _assert_strict_object(schema)

    kw_items = schema["properties"]["keywords"]["items"]
    assert set(kw_items["required"]) == {"term", "normalized", "weight", "kind"}
    assert set(kw_items["properties"]["kind"]["enum"]) == set(KEYWORD_KIND_VALUES)


def test_feed_and_comment_llm_schemas_are_strict() -> None:
    for model in (FeedOntology, CommentOntology):
        wrapper = build_llm_json_schema(model, name=model.__name__)
        assert wrapper["strict"] is True
        assert "created_at" not in wrapper["schema"]["properties"]
        _assert_strict_object(wrapper["schema"])


def test_query_analysis_llm_schema_has_nested_objects() -> None:
    wrapper = build_llm_json_schema(QueryOntologyAnalysis, name="query_ontology_analysis")
    schema = wrapper["schema"]

    assert wrapper["strict"] is True
    assert "created_at" not in schema["properties"]
    movie_props = schema["properties"]["movie"]["properties"]
    feed_props = schema["properties"]["feed"]["properties"]
    assert "genres" in movie_props
    assert "categories" in feed_props
    _assert_strict_object(schema)
