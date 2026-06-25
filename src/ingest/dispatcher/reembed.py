"""Neo4j summary 기반 embedding-only 재처리 핸들러."""

from __future__ import annotations

from src.api.schemas.reembed import (
    ReembedCommentPayload,
    ReembedFeedPayload,
    ReembedMoviePayload,
)
from src.embedding.dual_writer import PlotEmbeddingDualWriter
from src.embedding.summary_dual_writer import SummaryEmbeddingDualWriter
from src.embedding.version_registry import EmbeddingVersionRegistry
from src.graph.client import Neo4jClient
from src.graph.cypher_statements.comment import UPDATE_COMMENT_SUMMARY_EMBEDDING
from src.graph.cypher_statements.feed import UPDATE_FEED_SUMMARY_EMBEDDING
from src.ingest.dispatcher.utils import Embedder, Handler


def build_movie_reembed_handler(
    *,
    embedder: Embedder,
    dual_writer: PlotEmbeddingDualWriter,
) -> Handler:
    def _handler(payload: ReembedMoviePayload | dict) -> None:
        data = ReembedMoviePayload.model_validate(payload)
        embedding = embedder.embed(
            f"""
Instruct: Represent this movie's narrative content for semantic similarity search
Title: {data.title}
Summary: {data.summary}
Year: {data.producing_year}
Country: {data.country}
        """
        )
        dual_writer.write_movie_plot_embedding(data.movie_id, embedding)

    return _handler


def build_feed_reembed_handler(
    *,
    embedder: Embedder,
    neo4j: Neo4jClient,
    embedding_registry: EmbeddingVersionRegistry | None = None,
) -> Handler:
    summary_writer = (
        SummaryEmbeddingDualWriter(neo4j, embedding_registry)
        if embedding_registry is not None
        else None
    )

    def _handler(payload: ReembedFeedPayload | dict) -> None:
        data = ReembedFeedPayload.model_validate(payload)
        embedding = embedder.embed(data.summary)
        if summary_writer is not None:
            summary_writer.write_summary_embedding("feed", data.feed_id, embedding)
            return
        neo4j.execute_write(
            UPDATE_FEED_SUMMARY_EMBEDDING,
            {
                "feed_id": data.feed_id,
                "summary_embedding": embedding,
            },
        )

    return _handler


def build_comment_reembed_handler(
    *,
    embedder: Embedder,
    neo4j: Neo4jClient,
    embedding_registry: EmbeddingVersionRegistry | None = None,
) -> Handler:
    summary_writer = (
        SummaryEmbeddingDualWriter(neo4j, embedding_registry)
        if embedding_registry is not None
        else None
    )

    def _handler(payload: ReembedCommentPayload | dict) -> None:
        data = ReembedCommentPayload.model_validate(payload)
        embedding = embedder.embed(data.summary)
        if summary_writer is not None:
            summary_writer.write_summary_embedding("comment", data.comment_id, embedding)
            return
        neo4j.execute_write(
            UPDATE_COMMENT_SUMMARY_EMBEDDING,
            {
                "comment_id": data.comment_id,
                "summary_embedding": embedding,
            },
        )

    return _handler


__all__ = [
    "build_comment_reembed_handler",
    "build_feed_reembed_handler",
    "build_movie_reembed_handler",
]
