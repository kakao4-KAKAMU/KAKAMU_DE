from __future__ import annotations

from src.graph.cypher_statements import FULLTEXT_INDEXES, NODE_PROPERTY_INDEXES


def test_movie_title_property_index() -> None:
    indexes = "\n".join(NODE_PROPERTY_INDEXES)
    assert "movie_title_country_idx" in indexes
    assert "MovieTitle" in indexes
    assert "mt.country" in indexes


def test_movie_title_fulltext_index() -> None:
    indexes = "\n".join(FULLTEXT_INDEXES)
    assert "movie_title_text_ft" in indexes
    assert "MovieTitle" in indexes
    assert "mt.title" in indexes
    assert "fulltext.analyzer" in indexes
