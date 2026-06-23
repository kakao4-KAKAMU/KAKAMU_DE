"""Tests for embedding re-embed planner and dispatcher handlers."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from src.config.settings import EmbeddingSettings
from src.embedding.reembed_planner import (
    ReembedCandidate,
    count_reembed_candidates_by_type,
    enqueue_reembed_jobs,
    fetch_reembed_candidates,
)
from src.embedding.version_registry import EmbeddingVersionRegistry
from src.ingest.dispatcher.reembed import (
    build_comment_reembed_handler,
    build_feed_reembed_handler,
    build_movie_reembed_handler,
)
from tests.embedding.test_version_registry import FakeStore


class FakeNeo4j:
    def __init__(self, rows_by_query: dict[str, list[dict]]) -> None:
        self.rows_by_query = rows_by_query
        self.calls: list[tuple[str, dict | None]] = []

    def execute_read(self, cypher: str, params: dict | None = None) -> list[dict]:
        self.calls.append((cypher, params))
        for key, rows in self.rows_by_query.items():
            if key in cypher:
                return rows
        return []

    def execute_write(self, cypher: str, params: dict | None = None) -> list[dict]:
        self.calls.append((cypher, params))
        return [{"ok": True}]


class FakeOutboxWriter:
    def __init__(self) -> None:
        self.rows: list[dict] = []

    def enqueue(self, **kwargs) -> int:
        row_id = len(self.rows) + 1
        self.rows.append(kwargs)
        return row_id

    def flush(self) -> None:
        return None


def test_fetch_reembed_candidates_movie_feed_comment() -> None:
    client = FakeNeo4j(
        {
            "MATCH (m:Movie)": [
                {"aggregate_id": "m-1", "summary": "plot one"},
            ],
            "MATCH (f:Feed)": [
                {"aggregate_id": "f-1", "summary": "feed one"},
            ],
            "MATCH (c:Comment)": [
                {
                    "aggregate_id": "c-1",
                    "feed_id": "f-1",
                    "summary": "comment one",
                },
            ],
        }
    )
    candidates = fetch_reembed_candidates(
        client,
        entity_types=["movie", "feed", "comment"],
        target_version="2",
    )
    assert len(candidates) == 3
    assert count_reembed_candidates_by_type(candidates) == {
        "movie": 1,
        "feed": 1,
        "comment": 1,
    }


def test_enqueue_reembed_jobs_writes_outbox_rows() -> None:
    writer = FakeOutboxWriter()
    candidates = [
        ReembedCandidate("movie", "m-1", "plot"),
        ReembedCandidate("feed", "f-1", "feed"),
        ReembedCandidate("comment", "c-1", "comment", feed_id="f-1"),
    ]
    settings = EmbeddingSettings()
    report = enqueue_reembed_jobs(
        candidates,
        target_version="2",
        writer=writer,
        embedding_settings=settings,
    )
    assert report.total == 3
    assert {row["aggregate_type"] for row in writer.rows} == {
        "movie_reembed",
        "feed_reembed",
        "comment_reembed",
    }
    assert writer.rows[0]["model_name"] == settings.model_name
    assert writer.rows[0]["payload"]["target_embedding_version"] == "2"


def test_movie_reembed_handler_dual_writes() -> None:
    embedder = MagicMock()
    embedder.embed.return_value = [0.5, 0.5]
    dual_writer = MagicMock()
    handler = build_movie_reembed_handler(embedder=embedder, dual_writer=dual_writer)
    handler(
        {
            "movie_id": "m-1",
            "summary": "A hero saves the city.",
            "target_embedding_version": "2",
        }
    )
    embedder.embed.assert_called_once_with("A hero saves the city.")
    dual_writer.write_movie_plot_embedding.assert_called_once_with("m-1", [0.5, 0.5])


def test_feed_reembed_handler_updates_neo4j() -> None:
    embedder = MagicMock()
    embedder.embed.return_value = [0.1, 0.2]
    neo4j = FakeNeo4j({})
    handler = build_feed_reembed_handler(embedder=embedder, neo4j=neo4j)
    handler(
        {
            "feed_id": "f-1",
            "summary": "Great movie!",
            "target_embedding_version": "2",
        }
    )
    assert "summary_embedding" in neo4j.calls[0][0]
    assert neo4j.calls[0][1] == {
        "feed_id": "f-1",
        "summary_embedding": [0.1, 0.2],
    }


def test_comment_reembed_handler_updates_neo4j() -> None:
    embedder = MagicMock()
    embedder.embed.return_value = [0.3]
    neo4j = FakeNeo4j({})
    handler = build_comment_reembed_handler(embedder=embedder, neo4j=neo4j)
    handler(
        {
            "comment_id": "c-1",
            "feed_id": "f-1",
            "summary": "I agree.",
            "target_embedding_version": "2",
        }
    )
    assert neo4j.calls[0][1] == {
        "comment_id": "c-1",
        "summary_embedding": [0.3],
    }


def test_production_dispatcher_registers_movie_reembed_with_registry() -> None:
    from src.ingest.dispatcher import build_production_dispatcher

    llm = MagicMock()
    embedder = MagicMock()
    loader = MagicMock()
    neo4j = MagicMock()
    registry = EmbeddingVersionRegistry(FakeStore(), settings=EmbeddingSettings())
    dispatcher = build_production_dispatcher(
        llm=llm,
        embedder=embedder,
        loader=loader,
        neo4j=neo4j,
        embedding_registry=registry,
    )
    assert "movie_reembed" in dispatcher._handlers  # noqa: SLF001
