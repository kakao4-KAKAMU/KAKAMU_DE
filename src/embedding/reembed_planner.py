"""Embedding 버전 변경 시 Neo4j summary → ingest_outbox 재적재."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Sequence

from src.api.schemas.reembed import (
    ReembedCommentPayload,
    ReembedFeedPayload,
    ReembedMoviePayload,
)
from src.config.settings import EmbeddingSettings, get_settings
from src.embedding.version_registry import plot_embedding_property
from src.graph.client import Neo4jClient
from src.ingest.outbox_writer import OutboxWriter

ReembedEntityType = Literal["movie", "feed", "comment"]

REEMBED_AGGREGATE_TYPES: dict[ReembedEntityType, str] = {
    "movie": "movie_reembed",
    "feed": "feed_reembed",
    "comment": "comment_reembed",
}

_FETCH_MOVIES_FOR_REEMBED = """
MATCH (m:Movie)
WHERE coalesce(m.plot_summary, '') <> ''
  AND (
    m.plot_embedding IS NOT NULL
    OR size([k IN keys(m) WHERE k STARTS WITH 'plot_embedding_v']) > 0
  )
  AND ($missing_target_only = false OR m[$target_property] IS NULL)
RETURN m.movie_id AS aggregate_id,
       m.title AS title,
       m.plot_summary AS summary,
       m.country AS country,
       m.producing_year AS producing_year
ORDER BY m.movie_id
"""

_FETCH_FEEDS_FOR_REEMBED = """
MATCH (f:Feed)
WHERE coalesce(f.summary, '') <> ''
  AND f.summary_embedding IS NOT NULL
  AND coalesce(f.deleted, false) = false
RETURN f.feed_id AS aggregate_id,
       f.summary AS summary
ORDER BY f.feed_id
"""

_FETCH_COMMENTS_FOR_REEMBED = """
MATCH (c:Comment)-[:ON_FEED]->(f:Feed)
WHERE coalesce(c.summary, '') <> ''
  AND c.summary_embedding IS NOT NULL
  AND coalesce(c.deleted, false) = false
RETURN c.comment_id AS aggregate_id,
       f.feed_id AS feed_id,
       c.summary AS summary
ORDER BY c.comment_id
"""


@dataclass(frozen=True)
class ReembedCandidate:
    entity_type: ReembedEntityType
    aggregate_id: str
    summary: str
    feed_id: str | None = None


@dataclass(frozen=True)
class ReembedEnqueueReport:
    target_embedding_version: str
    enqueued: dict[str, int]
    skipped_empty_summary: int = 0

    @property
    def total(self) -> int:
        return sum(self.enqueued.values())


def fetch_reembed_candidates(
    client: Neo4jClient,
    *,
    entity_types: Sequence[ReembedEntityType],
    target_version: str,
    missing_target_only: bool = False,
    limit: int | None = None,
) -> list[ReembedCandidate]:
    """Neo4j 에서 summary 가 있는 기존 임베딩 대상을 수집한다."""
    candidates: list[ReembedCandidate] = []
    target_property = plot_embedding_property(target_version)

    if "movie" in entity_types:
        rows = client.execute_read(
            _FETCH_MOVIES_FOR_REEMBED,
            {
                "target_property": target_property,
                "missing_target_only": missing_target_only,
            },
        )
        for row in rows:
            summary = str(row.get("summary") or "").strip()
            if not summary:
                continue
            candidates.append(
                ReembedCandidate(
                    entity_type="movie",
                    aggregate_id=str(row["aggregate_id"]),
                    summary=summary,
                )
            )

    if "feed" in entity_types:
        rows = client.execute_read(_FETCH_FEEDS_FOR_REEMBED)
        for row in rows:
            summary = str(row.get("summary") or "").strip()
            if not summary:
                continue
            candidates.append(
                ReembedCandidate(
                    entity_type="feed",
                    aggregate_id=str(row["aggregate_id"]),
                    summary=summary,
                )
            )

    if "comment" in entity_types:
        rows = client.execute_read(_FETCH_COMMENTS_FOR_REEMBED)
        for row in rows:
            summary = str(row.get("summary") or "").strip()
            if not summary:
                continue
            candidates.append(
                ReembedCandidate(
                    entity_type="comment",
                    aggregate_id=str(row["aggregate_id"]),
                    summary=summary,
                    feed_id=str(row["feed_id"]),
                )
            )

    if limit is not None and limit > 0:
        return candidates[:limit]
    return candidates


def _build_payload(
    candidate: ReembedCandidate,
    target_version: str,
) -> ReembedMoviePayload | ReembedFeedPayload | ReembedCommentPayload:
    if candidate.entity_type == "movie":
        return ReembedMoviePayload(
            movie_id=candidate.aggregate_id,
            summary=candidate.summary,
            title=candidate.title,
            country=candidate.country,
            producing_year=candidate.producing_year,
            target_embedding_version=target_version,
        )
    if candidate.entity_type == "feed":
        return ReembedFeedPayload(
            feed_id=candidate.aggregate_id,
            summary=candidate.summary,
            target_embedding_version=target_version,
        )
    if candidate.feed_id is None:
        raise ValueError(f"comment reembed candidate missing feed_id: {candidate.aggregate_id}")
    return ReembedCommentPayload(
        comment_id=candidate.aggregate_id,
        feed_id=candidate.feed_id,
        summary=candidate.summary,
        target_embedding_version=target_version,
    )


def enqueue_reembed_jobs(
    candidates: Sequence[ReembedCandidate],
    *,
    target_version: str,
    writer: OutboxWriter | None = None,
    embedding_settings: EmbeddingSettings | None = None,
) -> ReembedEnqueueReport:
    """수집된 summary 를 ingest_outbox 에 movie/feed/comment_reembed 로 적재한다."""
    outbox = writer or OutboxWriter()
    settings = embedding_settings or get_settings().embedding
    enqueued: dict[str, int] = {t: 0 for t in REEMBED_AGGREGATE_TYPES.values()}

    for candidate in candidates:
        payload = _build_payload(candidate, target_version)
        aggregate_type = REEMBED_AGGREGATE_TYPES[candidate.entity_type]
        outbox.enqueue(
            aggregate_type=aggregate_type,
            aggregate_id=candidate.aggregate_id,
            payload=payload.model_dump(mode="json"),
            model_name=settings.model_name,
            wait=True,
        )
        enqueued[aggregate_type] += 1

    outbox.flush()

    return ReembedEnqueueReport(
        target_embedding_version=target_version,
        enqueued=enqueued,
    )


def count_reembed_candidates_by_type(
    candidates: Sequence[ReembedCandidate],
) -> dict[ReembedEntityType, int]:
    counts: dict[ReembedEntityType, int] = {"movie": 0, "feed": 0, "comment": 0}
    for candidate in candidates:
        counts[candidate.entity_type] += 1
    return counts


__all__ = [
    "ReembedCandidate",
    "ReembedEnqueueReport",
    "ReembedEntityType",
    "REEMBED_AGGREGATE_TYPES",
    "count_reembed_candidates_by_type",
    "enqueue_reembed_jobs",
    "fetch_reembed_candidates",
]
