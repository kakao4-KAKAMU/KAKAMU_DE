"""Production dispatcher: extractor + embedder + loader 흐름 통합 (mock)."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock

from src.ingest.dispatcher import (
    build_comment_handler,
    build_feed_handler,
    build_movie_handler,
    build_production_dispatcher,
)
from src.ontology.schema import (
    CommentOntology,
    FeedOntology,
    MoviePlotOntology,
    Sentiment,
)


def _movie_ontology() -> MoviePlotOntology:
    return MoviePlotOntology(
        source_id="m-1",
        summary="가난한 가족이 부유한 가족의 집에 침투하는 이야기",
        themes=["계급"],
        moods=["긴장감"],
        keywords=[],
    )


def _feed_ontology() -> FeedOntology:
    return FeedOntology(
        source_id="f-1",
        summary="좋았다",
        sentiment=Sentiment.POSITIVE,
        sentiment_score=0.6,
    )


def _comment_ontology() -> CommentOntology:
    return CommentOntology(
        source_id="c-1",
        summary="동의",
        sentiment=Sentiment.POSITIVE,
        sentiment_score=0.4,
    )


def test_movie_handler_invokes_extract_embed_upsert() -> None:
    extractor = MagicMock()
    extractor.extract.return_value = _movie_ontology()
    embedder = MagicMock()
    embedder.embed.return_value = [0.1, 0.2]
    loader = MagicMock()

    handler = build_movie_handler(extractor=extractor, embedder=embedder, loader=loader)
    handler(
        {
            "movie_id": "m-1",
            "title": "기생충",
            "producing_year": 2019,
            "country": "KR",
            "genres": ["드라마"],
            "plot": "...",
        }
    )

    extractor.extract.assert_called_once()
    embedder.embed.assert_called_once()
    loader.upsert_movie.assert_called_once()
    kwargs = loader.upsert_movie.call_args.kwargs
    assert kwargs["movie_id"] == "m-1"
    assert kwargs["plot_embedding"] == [0.1, 0.2]


def test_feed_handler_parses_created_at_iso() -> None:
    extractor = MagicMock()
    extractor.extract.return_value = _feed_ontology()
    embedder = MagicMock()
    embedder.embed.return_value = [0.0]
    loader = MagicMock()

    handler = build_feed_handler(extractor=extractor, embedder=embedder, loader=loader)
    handler(
        {
            "feed_id": "f-1",
            "user_id": "u-1",
            "content": "재밌었어요",
            "created_at": "2026-05-23T10:00:00+00:00",
        }
    )
    created_at = loader.upsert_feed.call_args.kwargs["created_at"]
    assert isinstance(created_at, datetime)
    assert created_at.tzinfo is not None


def test_comment_handler_routes_to_upsert_comment() -> None:
    extractor = MagicMock()
    extractor.extract.return_value = _comment_ontology()
    embedder = MagicMock()
    embedder.embed.return_value = [0.0]
    loader = MagicMock()

    handler = build_comment_handler(extractor=extractor, embedder=embedder, loader=loader)
    handler(
        {
            "comment_id": "c-1",
            "feed_id": "f-1",
            "user_id": "u-2",
            "content": "동의합니다",
        }
    )
    loader.upsert_comment.assert_called_once()


def test_production_dispatcher_registers_three_aggregates() -> None:
    llm = MagicMock()
    embedder = MagicMock()
    embedder.embed.return_value = [0.0]
    loader = MagicMock()
    dispatcher = build_production_dispatcher(llm=llm, embedder=embedder, loader=loader)
    # _handlers 는 internal 이므로 dispatch() 로 간접 검증
    for agg in ("movie", "feed", "comment"):
        assert agg in dispatcher._handlers  # noqa: SLF001 - test detail
