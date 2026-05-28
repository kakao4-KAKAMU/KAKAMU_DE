"""aggregate_type → 처리 핸들러 (extract + load).

SOLID
-----
- SRP: dispatcher 는 "aggregate_type → handler" 매핑만 책임. 추출/적재는 외부에 위임.
- OCP: 신규 aggregate_type 은 register() 로 추가만으로 확장.
- DIP: production handler 는 LLMClient / Embedder / Loader 추상에만 의존한다.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Callable, Mapping, Optional, Protocol

from src.extractor.comment_extractor import CommentExtractor
from src.extractor.feed_extractor import FeedExtractor
from src.extractor.movie_extractor import MoviePlotExtractor
from src.graph.client import Neo4jClient
from src.graph.loader import OntologyLoader

logger = logging.getLogger(__name__)

Handler = Callable[[Mapping[str, Any]], None]


class Embedder(Protocol):
    """경량 임베딩 추상화. 실제 구현은 VLLMEmbeddingClient."""

    def embed(self, text: str) -> list[float]: ...


class LLMClient(Protocol):
    def chat_json(
        self,
        messages: list[dict[str, str]],
        *,
        user_id: str | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
        response_format: dict[str, Any] | None = None,
        guided_json_schema: dict[str, Any] | None = None,
    ) -> dict[str, Any]: ...


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
# Production handlers (extract + embed + upsert)
# ---------------------------------------------------------------------------


def _parse_dt(value: Any) -> Optional[datetime]:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(str(value))
    except ValueError:
        return None


def build_movie_handler(
    *,
    extractor: MoviePlotExtractor,
    embedder: Embedder,
    loader: OntologyLoader,
) -> Handler:
    """payload: {movie_id, title, producing_year?, country?, genres?, plot, toxicity_score?}"""

    def _handler(payload: Mapping[str, Any]) -> None:
        movie_id = str(payload["movie_id"])
        title = str(payload["title"])
        plot = str(payload.get("plot") or "")
        ontology = extractor.extract(
            movie_id=movie_id,
            title=title,
            producing_year=payload.get("producing_year"),
            country=payload.get("country"),
            genres=list(payload.get("genres") or []),
            plot=plot,
        )
        embedding = embedder.embed(ontology.summary or plot)
        loader.upsert_movie(
            movie_id=movie_id,
            title=title,
            producing_year=payload.get("producing_year"),
            country=payload.get("country"),
            genres=list(payload.get("genres") or []),
            plot_raw=plot,
            ontology=ontology,
            plot_embedding=embedding,
        )

    return _handler


def build_feed_handler(
    *,
    extractor: FeedExtractor,
    embedder: Embedder,
    loader: OntologyLoader,
) -> Handler:
    """payload: {feed_id, author_id, related_movie_id?, known_movie_ids?, content, created_at?}"""

    def _handler(payload: Mapping[str, Any]) -> None:
        feed_id = str(payload["feed_id"])
        author_id = str(payload["author_id"])
        content = str(payload.get("content") or "")
        ontology = extractor.extract(
            feed_id=feed_id,
            author_id=author_id,
            related_movie_id=payload.get("related_movie_id"),
            known_movie_ids=list(payload.get("known_movie_ids") or []),
            content=content,
        )
        embedding = embedder.embed(ontology.summary or content)
        loader.upsert_feed(
            feed_id=feed_id,
            author_id=author_id,
            related_movie_id=payload.get("related_movie_id"),
            content_raw=content,
            ontology=ontology,
            summary_embedding=embedding,
            created_at=_parse_dt(payload.get("created_at")),
        )

    return _handler


def build_comment_handler(
    *,
    extractor: CommentExtractor,
    embedder: Embedder,
    loader: OntologyLoader,
) -> Handler:
    """payload: {comment_id, feed_id, author_id, mentioned_user_ids?, parent_feed_summary?, content}"""

    def _handler(payload: Mapping[str, Any]) -> None:
        comment_id = str(payload["comment_id"])
        feed_id = str(payload["feed_id"])
        author_id = str(payload["author_id"])
        content = str(payload.get("content") or "")
        ontology = extractor.extract(
            comment_id=comment_id,
            feed_id=feed_id,
            author_id=author_id,
            mentioned_user_ids=list(payload.get("mentioned_user_ids") or []),
            parent_feed_summary=payload.get("parent_feed_summary"),
            content=content,
        )
        embedding = embedder.embed(ontology.summary or content)
        loader.upsert_comment(
            comment_id=comment_id,
            feed_id=feed_id,
            author_id=author_id,
            content_raw=content,
            ontology=ontology,
            summary_embedding=embedding,
            created_at=_parse_dt(payload.get("created_at")),
        )

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
