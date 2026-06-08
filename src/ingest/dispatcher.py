"""aggregate_type → 처리 핸들러 (extract + load).

SOLID
-----
- SRP: dispatcher 는 "aggregate_type → handler" 매핑만 책임. 추출/적재는 외부에 위임.
- OCP: 신규 aggregate_type 은 register() 로 추가만으로 확장.
- DIP: production handler 는 LLMClient / Embedder / Loader 추상에만 의존한다.
"""

from __future__ import annotations

import logging
from typing import Any, Mapping, Optional

from src.extractor.comment_extractor import CommentExtractor
from src.extractor.feed_extractor import FeedExtractor
from src.extractor.movie_extractor import MoviePlotExtractor
from src.graph.client import Neo4jClient
from src.graph.loader import OntologyLoader
from src.ingest.dispatcher.utils import Embedder, Handler, LLMClient
from src.ingest.dispatcher.movie import build_movie_handler
from src.ingest.dispatcher.feed import build_feed_handler
from src.ingest.dispatcher.comment import build_comment_handler

logger = logging.getLogger(__name__)



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
    """movie / feed / comment → mock extract+load. (테스트/로컬 smoke)"""
    d = IngestDispatcher()
    for t in ("movie", "feed", "comment"):
        d.register(t, mock_extract_load_handler(t))
    return d


def build_production_dispatcher(
    *,
    llm: LLMClient,
    embedder: Embedder,
    loader: OntologyLoader,
    neo4j: Optional[Neo4jClient] = None,  # noqa: ARG001 - 향후 확장용 hook
) -> IngestDispatcher:
    """실 Extractor + Embedder + Loader 를 묶은 production dispatcher."""
    d = IngestDispatcher()
    d.register(
        "movie",
        build_movie_handler(
            extractor=MoviePlotExtractor(llm),
            embedder=embedder,
            loader=loader,
        ),
    )
    d.register(
        "feed",
        build_feed_handler(
            extractor=FeedExtractor(llm),
            embedder=embedder,
            loader=loader,
        ),
    )
    d.register(
        "comment",
        build_comment_handler(
            extractor=CommentExtractor(llm),
            embedder=embedder,
            loader=loader,
        ),
    )
    return d


__all__ = [
    "Embedder",
    "Handler",
    "IngestDispatcher",
    "LLMClient",
    "build_comment_handler",
    "build_feed_handler",
    "build_movie_handler",
    "build_production_dispatcher",
    "default_dispatcher",
    "mock_extract",
    "mock_extract_load_handler",
    "mock_load",
]
