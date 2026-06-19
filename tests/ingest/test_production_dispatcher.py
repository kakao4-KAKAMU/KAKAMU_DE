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
    CommentReaction,
    CommentTarget,
    FeedCategory,
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
        category=FeedCategory.REVIEW,
        sentiment=Sentiment.POSITIVE,
        sentiment_score=0.6,
    )


def _comment_ontology() -> CommentOntology:
    return CommentOntology(
        source_id="c-1",
        summary="동의",
        target=CommentTarget.FEED,
        reaction=CommentReaction.EMPATHY,
        sentiment=Sentiment.POSITIVE,
        sentiment_score=0.4,
    )


def test_movie_handler_passes_persons_and_reviews_to_extract() -> None:
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
            "plot": "...",
            "persons": [
                {"person_id": "p-dir-1", "name": "봉준호", "job": "director"},
                {"person_id": "p-act-1", "name": "송강호", "job": "actor"},
            ],
            "reviews": ["계급 대비가 인상적", "반전이 서늘하다"],
        }
    )

    extract_kwargs = extractor.extract.call_args.kwargs
    assert extract_kwargs["persons"] == [
        {"person_id": "p-dir-1", "name": "봉준호", "job": "director"},
        {"person_id": "p-act-1", "name": "송강호", "job": "actor"},
    ]
    assert extract_kwargs["reviews"] == ["계급 대비가 인상적", "반전이 서늘하다"]

    upsert_kwargs = loader.upsert_movie.call_args.kwargs
    assert upsert_kwargs["persons"] == extract_kwargs["persons"]


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


def test_comment_handler_loads_ontology_context_from_neo4j() -> None:
    extractor = MagicMock()
    extractor.extract.return_value = _comment_ontology()
    embedder = MagicMock()
    embedder.embed.return_value = [0.0]
    loader = MagicMock()
    context_reader = MagicMock()
    context_reader.get_feed_summary.return_value = "기생충 재관람 감상"
    context_reader.get_comment_summary.return_value = "동의해요"

    handler = build_comment_handler(
        extractor=extractor,
        embedder=embedder,
        loader=loader,
        context_reader=context_reader,
    )
    handler(
        {
            "comment_id": "c-1",
            "feed_id": "f-1",
            "user_id": "u-2",
            "parent_comment_id": "c-parent",
            "content": "저도 그렇게 느꼈어요",
        }
    )

    context_reader.get_feed_summary.assert_called_once_with("f-1")
    context_reader.get_comment_summary.assert_called_once_with("c-parent")
    extract_kwargs = extractor.extract.call_args.kwargs
    assert extract_kwargs["parent_feed_summary"] == "기생충 재관람 감상"
    assert extract_kwargs["parent_comment_summary"] == "동의해요"
    assert extract_kwargs["mentioned_user_ids"] == []

    upsert_kwargs = loader.upsert_comment.call_args.kwargs
    assert upsert_kwargs["parent_comment_id"] == "c-parent"
    loader.upsert_comment.assert_called_once()


def test_production_dispatcher_registers_all_aggregates() -> None:
    llm = MagicMock()
    embedder = MagicMock()
    embedder.embed.return_value = [0.0]
    loader = MagicMock()
    neo4j = MagicMock()
    dispatcher = build_production_dispatcher(
        llm=llm, embedder=embedder, loader=loader, neo4j=neo4j
    )
    expected = {
        "movie", "feed", "comment",
        "feed_reembed", "comment_reembed",
        "feed_modify", "feed_delete", "feed_like",
        "comment_modify", "comment_delete", "comment_like",
        "movie_judge", "person_judge",
        "user", "persona", "persona_modify", "persona_delete",
    }
    assert set(dispatcher._handlers.keys()) == expected  # noqa: SLF001


def test_feed_like_handler_calls_loader() -> None:
    loader = MagicMock()
    from src.ingest.dispatcher.like import build_feed_like_handler

    handler = build_feed_like_handler(loader=loader)
    handler({"feed_id": "f-1", "user_id": "u-1", "is_like": True})
    loader.like_feed.assert_called_once()
    kwargs = loader.like_feed.call_args.kwargs
    assert kwargs["feed_id"] == "f-1"
    assert kwargs["is_like"] is True


def test_comment_like_handler_calls_loader() -> None:
    loader = MagicMock()
    from src.ingest.dispatcher.like import build_comment_like_handler

    handler = build_comment_like_handler(loader=loader)
    handler({"comment_id": "c-1", "user_id": "u-1", "is_like": False})
    loader.like_comment.assert_called_once()
    kwargs = loader.like_comment.call_args.kwargs
    assert kwargs["comment_id"] == "c-1"
    assert kwargs["is_like"] is False


def test_movie_judge_handler_calls_loader() -> None:
    loader = MagicMock()
    from src.ingest.dispatcher.judge import build_movie_judge_handler

    handler = build_movie_judge_handler(loader=loader)
    handler({"movie_id": "m-1", "user_id": "u-1", "judge_type": "like"})
    loader.judge_movie.assert_called_once()
    kwargs = loader.judge_movie.call_args.kwargs
    assert kwargs["movie_id"] == "m-1"
    assert kwargs["judge_type"] == "like"


def test_person_judge_handler_calls_loader() -> None:
    loader = MagicMock()
    from src.ingest.dispatcher.judge import build_person_judge_handler

    handler = build_person_judge_handler(loader=loader)
    handler({"person_id": "p-1", "user_id": "u-1", "judge_type": "dislike"})
    loader.judge_person.assert_called_once()
    kwargs = loader.judge_person.call_args.kwargs
    assert kwargs["person_id"] == "p-1"
    assert kwargs["judge_type"] == "dislike"


def test_feed_delete_handler_calls_loader() -> None:
    loader = MagicMock()
    from src.ingest.dispatcher.delete import build_feed_delete_handler

    handler = build_feed_delete_handler(loader=loader)
    handler({"feed_id": "f-1", "user_id": "u-1"})
    loader.delete_feed.assert_called_once()
    assert loader.delete_feed.call_args.kwargs["feed_id"] == "f-1"


def test_comment_delete_handler_calls_loader() -> None:
    loader = MagicMock()
    from src.ingest.dispatcher.delete import build_comment_delete_handler

    handler = build_comment_delete_handler(loader=loader)
    handler({"comment_id": "c-1", "user_id": "u-1"})
    loader.delete_comment.assert_called_once()
    assert loader.delete_comment.call_args.kwargs["comment_id"] == "c-1"


def test_user_handler_calls_loader() -> None:
    loader = MagicMock()
    from src.ingest.dispatcher.user import build_user_handler

    handler = build_user_handler(loader=loader)
    handler({"user_id": "u-1", "nickname": "영화광"})
    loader.upsert_user.assert_called_once()
    kwargs = loader.upsert_user.call_args.kwargs
    assert kwargs["user_id"] == "u-1"
    assert kwargs["nickname"] == "영화광"


def test_persona_handler_calls_loader() -> None:
    loader = MagicMock()
    from src.ingest.dispatcher.persona import build_persona_handler

    handler = build_persona_handler(loader=loader)
    handler(
        {
            "persona_id": "movie_buff",
            "user_id": "u-1",
            "label": "영화 덕후",
            "genres": ["SF", "스릴러"],
            "movies": ["m-1", "m-2"],
            "persons": ["p-1"],
        }
    )
    loader.upsert_persona.assert_called_once()
    kwargs = loader.upsert_persona.call_args.kwargs
    assert kwargs["persona_id"] == "movie_buff"
    assert kwargs["genres"] == ["SF", "스릴러"]
    assert kwargs["movies"] == ["m-1", "m-2"]
    assert kwargs["persons"] == ["p-1"]


def test_persona_delete_handler_calls_loader() -> None:
    loader = MagicMock()
    from src.ingest.dispatcher.persona import build_persona_delete_handler

    handler = build_persona_delete_handler(loader=loader)
    handler({"persona_id": "movie_buff", "user_id": "u-1"})
    loader.delete_persona.assert_called_once()
    assert loader.delete_persona.call_args.kwargs["persona_id"] == "movie_buff"
