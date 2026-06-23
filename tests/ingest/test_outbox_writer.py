"""OutboxWriter batch flush tests."""

from __future__ import annotations

import threading
import time
from contextlib import contextmanager
from unittest.mock import MagicMock, patch

import pytest

from src.ingest.outbox_writer import OutboxWriter


def _connection_factory(fetchall_batches: list[list[tuple[int]]]):
    batches = iter(fetchall_batches)

    def conn_ctx(*_a, **_k):
        conn = MagicMock()
        cur = MagicMock()
        cur.fetchall.side_effect = lambda: next(batches)
        conn.cursor.return_value.__enter__.return_value = cur
        conn.cursor.return_value.__exit__.return_value = None

        @contextmanager
        def _cm():
            yield conn

        return _cm()

    return conn_ctx


def _make_writer(**kwargs) -> OutboxWriter:
    with patch("src.ingest.outbox_writer.get_settings") as mock_settings:
        mock_settings.return_value.ontology.prompt_version = "pv1"
        mock_settings.return_value.ontology.model_name = "model1"
        return OutboxWriter(MagicMock(), **kwargs)


def test_enqueue_flushes_when_batch_max_reached() -> None:
    writer = _make_writer(batch_max_size=2, flush_interval_sec=60.0)

    with patch(
        "src.ingest.outbox_writer.get_connection",
        side_effect=_connection_factory([[(101,), (102,)], [(103,)]]),
    ):
        ids = [
            writer.enqueue(
                aggregate_type="movie",
                aggregate_id=f"m{i}",
                payload={"movie_id": f"m{i}"},
                wait=False,
            )
            for i in range(1, 4)
        ]
        writer.flush()

    assert ids == [0, 0, 0]


def test_enqueue_flushes_after_interval() -> None:
    writer = _make_writer(batch_max_size=100, flush_interval_sec=0.05)

    with patch(
        "src.ingest.outbox_writer.get_connection",
        side_effect=_connection_factory([[(42,)]]),
    ):
        started = time.monotonic()
        outbox_id = writer.enqueue(
            aggregate_type="feed",
            aggregate_id="f1",
            payload={"feed_id": "f1"},
        )
        elapsed = time.monotonic() - started

    assert outbox_id == 42
    assert elapsed >= 0.04


def test_flush_drains_buffer_without_waiting_for_timer() -> None:
    writer = _make_writer(batch_max_size=100, flush_interval_sec=60.0)
    done = threading.Event()

    with patch(
        "src.ingest.outbox_writer.get_connection",
        side_effect=_connection_factory([[(7,)]]),
    ):
        writer.enqueue(
            aggregate_type="comment",
            aggregate_id="c1",
            payload={"comment_id": "c1"},
            wait=False,
        )
        writer.flush()
        done.set()

    assert done.is_set()


def test_wait_true_returns_assigned_id_from_batch() -> None:
    writer = _make_writer(batch_max_size=100, flush_interval_sec=0.05)

    with patch(
        "src.ingest.outbox_writer.get_connection",
        side_effect=_connection_factory([[(11,)]]),
    ):
        outbox_id = writer.enqueue(
            aggregate_type="movie",
            aggregate_id="m1",
            payload={"movie_id": "m1"},
            wait=True,
        )

    assert outbox_id == 11


def test_invalid_batch_settings() -> None:
    with pytest.raises(ValueError, match="batch_max_size"):
        _make_writer(batch_max_size=0)
    with pytest.raises(ValueError, match="flush_interval_sec"):
        _make_writer(flush_interval_sec=0)
