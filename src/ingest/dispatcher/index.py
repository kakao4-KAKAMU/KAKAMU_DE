"""aggregate_type → 처리 핸들러 (extract + load).

SOLID
-----
- SRP: dispatcher 는 "aggregate_type → handler" 매핑만 책임. 추출/적재는 외부에 위임.
- OCP: 신규 aggregate_type 은 register() 로 추가만으로 확장.
- DIP: production handler 는 LLMClient / Embedder / Loader 추상에만 의존한다.
"""

from __future__ import annotations

import logging
from typing import Any, Mapping

from src.extractor.comment_extractor import CommentExtractor
from src.extractor.feed_extractor import FeedExtractor
from src.extractor.movie_extractor import MoviePlotExtractor
from src.graph.client import Neo4jClient
from src.graph.context_reader import Neo4jCommentContextReader
from src.graph.loader import OntologyLoader
from src.ingest.dispatcher.utils import Embedder, Handler, LLMClient
from src.ingest.dispatcher.movie import build_movie_handler
from src.ingest.dispatcher.feed import build_feed_handler
from src.ingest.dispatcher.comment import build_comment_handler
from src.ingest.dispatcher.like import build_feed_like_handler, build_comment_like_handler
from src.ingest.dispatcher.judge import build_movie_judge_handler, build_person_judge_handler
from src.ingest.dispatcher.delete import build_feed_delete_handler, build_comment_delete_handler
from src.ingest.dispatcher.user import build_user_handler
from src.ingest.dispatcher.persona import build_persona_handler, build_persona_delete_handler
from src.ingest.dispatcher.reembed import (
    build_comment_reembed_handler,
    build_feed_reembed_handler,
    build_movie_reembed_handler,
)
from src.embedding.dual_writer import PlotEmbeddingDualWriter
from src.embedding.version_registry import EmbeddingVersionRegistry

logger = logging.getLogger(__name__)

ALL_AGGREGATE_TYPES = (
    "movie", "feed", "comment",
    "movie_reembed", "feed_reembed", "comment_reembed",
    "feed_modify", "feed_delete", "feed_like",
    "comment_modify", "comment_delete", "comment_like",
    "movie_judge", "person_judge",
    "user", "persona", "persona_modify", "persona_delete",
)


# ---------------------------------------------------------------------------
# Mock (테스트/스텁용)
# ---------------------------------------------------------------------------


def mock_extract(aggregate_type: str, payload: Mapping[str, Any]) -> dict[str, Any]:
    """테스트/스텁용 온톨로지 추출."""
    return {"aggregate_type": aggregate_type, "source": dict(payload)}


def mock_load(aggregate_type: str, extracted: Mapping[str, Any]) -> None:
    """테스트/스텁용 Neo4j 적재."""
    logger.debug("mock_load %s keys=%s", aggregate_type, list(extracted.keys()))


def mock_extract_load_handler(aggregate_type: str) -> Handler:
    def _handler(payload: Mapping[str, Any]) -> None:
        extracted = mock_extract(aggregate_type, payload)
        mock_load(aggregate_type, extracted)

    return _handler


# ---------------------------------------------------------------------------
# Dispatcher
# ---------------------------------------------------------------------------


class IngestDispatcher:
    def __init__(self) -> None:
        self._handlers: dict[str, Handler] = {}

    def register(self, aggregate_type: str, handler: Handler) -> None:
        self._handlers[aggregate_type] = handler

    def dispatch(self, aggregate_type: str, payload: Mapping[str, Any]) -> None:
        handler = self._handlers.get(aggregate_type)
        if handler is None:
            raise ValueError(f"No handler for aggregate_type={aggregate_type}")
        handler(payload)


def default_dispatcher() -> IngestDispatcher:
    """전체 aggregate_type → mock extract+load. (테스트/로컬 smoke)"""
    d = IngestDispatcher()
    for t in ALL_AGGREGATE_TYPES:
        d.register(t, mock_extract_load_handler(t))
    return d


def build_production_dispatcher(
    *,
    llm: LLMClient,
    embedder: Embedder,
    loader: OntologyLoader,
    neo4j: Neo4jClient,
    embedding_registry: EmbeddingVersionRegistry | None = None,
) -> IngestDispatcher:
    """실 Extractor + Embedder + Loader 를 묶은 production dispatcher."""
    context_reader = Neo4jCommentContextReader(neo4j)
    d = IngestDispatcher()
    registry = embedding_registry

    movie_handler = build_movie_handler(
        extractor=MoviePlotExtractor(llm), embedder=embedder, loader=loader,
    )
    feed_handler = build_feed_handler(
        extractor=FeedExtractor(llm), embedder=embedder, loader=loader,
    )
    comment_handler = build_comment_handler(
        extractor=CommentExtractor(llm), embedder=embedder, loader=loader,
        context_reader=context_reader,
    )

    d.register("movie", movie_handler)
    d.register("feed", feed_handler)
    d.register("comment", comment_handler)

    if registry is not None:
        dual_writer = PlotEmbeddingDualWriter(neo4j, registry)
        d.register(
            "movie_reembed",
            build_movie_reembed_handler(embedder=embedder, dual_writer=dual_writer),
        )
    d.register(
        "feed_reembed",
        build_feed_reembed_handler(
            embedder=embedder,
            neo4j=neo4j,
            embedding_registry=registry,
        ),
    )
    d.register(
        "comment_reembed",
        build_comment_reembed_handler(
            embedder=embedder,
            neo4j=neo4j,
            embedding_registry=registry,
        ),
    )

    # modify 는 create 와 동일한 MERGE/SET 로직 (멱등)
    d.register("feed_modify", feed_handler)
    d.register("comment_modify", comment_handler)

    d.register("feed_like", build_feed_like_handler(loader=loader))
    d.register("comment_like", build_comment_like_handler(loader=loader))

    d.register("movie_judge", build_movie_judge_handler(loader=loader))
    d.register("person_judge", build_person_judge_handler(loader=loader))

    d.register("feed_delete", build_feed_delete_handler(loader=loader))
    d.register("comment_delete", build_comment_delete_handler(loader=loader))

    user_handler = build_user_handler(loader=loader)
    persona_handler = build_persona_handler(loader=loader)
    d.register("user", user_handler)
    d.register("persona", persona_handler)
    d.register("persona_modify", persona_handler)
    d.register("persona_delete", build_persona_delete_handler(loader=loader))

    return d


__all__ = [
    "ALL_AGGREGATE_TYPES",
    "IngestDispatcher",
    "build_production_dispatcher",
    "default_dispatcher",
    "mock_extract",
    "mock_extract_load_handler",
    "mock_load",
]
