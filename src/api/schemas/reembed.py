"""Neo4j summary 기반 embedding 재처리 outbox payload."""

from __future__ import annotations

from pydantic import Field

from src.api.schemas.shared import IngestPayload


class ReembedMoviePayload(IngestPayload):
    """Movie plot_summary 재임베딩."""

    movie_id: str = Field(min_length=1)
    summary: str = Field(min_length=1)
    target_embedding_version: str = Field(min_length=1)


class ReembedFeedPayload(IngestPayload):
    """Feed summary 재임베딩."""

    feed_id: str = Field(min_length=1)
    summary: str = Field(min_length=1)
    target_embedding_version: str = Field(min_length=1)


class ReembedCommentPayload(IngestPayload):
    """Comment summary 재임베딩."""

    comment_id: str = Field(min_length=1)
    feed_id: str = Field(min_length=1)
    summary: str = Field(min_length=1)
    target_embedding_version: str = Field(min_length=1)


__all__ = [
    "ReembedCommentPayload",
    "ReembedFeedPayload",
    "ReembedMoviePayload",
]
