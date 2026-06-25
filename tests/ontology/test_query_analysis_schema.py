"""query_analysis JSON schema tests."""

from __future__ import annotations

from src.ontology.prompts.query_analysis import get_query_analysis_schema_json
from src.ontology.prompts.schema_vocab import vocab_themes
from src.ontology.schema import (
    FEED_CATEGORY_VALUES,
    GENRE_VALUES,
    KEYWORD_KIND_VALUES,
)


def _nested_props(schema: dict, *path: str) -> dict:
    node = schema["schema"]["properties"]
    for key in path:
        node = node[key]["properties"]
    return node


def test_query_analysis_schema_has_nested_vocab_enums() -> None:
    schema = get_query_analysis_schema_json()
    movie = _nested_props(schema, "movie")
    feed = _nested_props(schema, "feed")

    assert set(movie["genres"]["items"]["enum"]) == set(GENRE_VALUES)
    assert "identity" in movie["themes"]["items"]["enum"]
    assert set(movie["themes"]["items"]["enum"]) == set(vocab_themes())
    assert set(feed["categories"]["items"]["enum"]) == set(FEED_CATEGORY_VALUES)


def test_query_analysis_keyword_items_are_strict_keyword_schema() -> None:
    schema = get_query_analysis_schema_json()
    movie_kw = _nested_props(schema, "movie")["keywords"]["items"]
    feed_kw = _nested_props(schema, "feed")["keywords"]["items"]

    for kw_schema in (movie_kw, feed_kw):
        assert kw_schema["additionalProperties"] is False
        assert set(kw_schema["required"]) == {"term", "normalized", "weight", "kind"}
        assert set(kw_schema["properties"]["kind"]["enum"]) == set(KEYWORD_KIND_VALUES)


def test_query_analysis_schema_excludes_created_at() -> None:
    schema = get_query_analysis_schema_json()
    root_props = schema["schema"]["properties"]
    assert "created_at" not in root_props
