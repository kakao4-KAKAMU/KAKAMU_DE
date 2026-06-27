"""Neo4j comment context reader tests."""

from __future__ import annotations

from unittest.mock import MagicMock

from src.graph.context_reader import (
    Neo4jCommentContextReader,
    Neo4jMoviePlotReader,
    NullCommentContextReader,
    NullMoviePlotReader,
)


def test_null_context_reader_returns_none() -> None:
    reader = NullCommentContextReader()
    assert reader.get_feed_summary("f-1") is None
    assert reader.get_comment_summary("c-1") is None


def test_null_movie_plot_reader_returns_none() -> None:
    reader = NullMoviePlotReader()
    assert reader.get_plot_raw("m-1") is None


def test_neo4j_context_reader_fetches_summaries() -> None:
    neo4j = MagicMock()
    neo4j.execute_read.side_effect = [
        [{"summary": "피드 요약"}],
        [{"summary": "부모 댓글 요약"}],
    ]
    reader = Neo4jCommentContextReader(neo4j)

    assert reader.get_feed_summary("f-1") == "피드 요약"
    assert reader.get_comment_summary("c-parent") == "부모 댓글 요약"
    assert neo4j.execute_read.call_count == 2


def test_neo4j_context_reader_returns_none_when_missing() -> None:
    neo4j = MagicMock()
    neo4j.execute_read.return_value = []
    reader = Neo4jCommentContextReader(neo4j)

    assert reader.get_feed_summary("missing") is None


def test_neo4j_movie_plot_reader_fetches_plot_raw() -> None:
    neo4j = MagicMock()
    neo4j.execute_read.return_value = [{"plot_raw": "가난한 가족의 이야기"}]
    reader = Neo4jMoviePlotReader(neo4j)

    assert reader.get_plot_raw("m-1") == "가난한 가족의 이야기"
    neo4j.execute_read.assert_called_once()


def test_neo4j_movie_plot_reader_returns_none_when_missing() -> None:
    neo4j = MagicMock()
    neo4j.execute_read.return_value = []
    reader = Neo4jMoviePlotReader(neo4j)

    assert reader.get_plot_raw("missing") is None
