from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from src.ingest.dispatcher import IngestDispatcher, mock_extract, mock_extract_load_handler
from src.ingest.outbox_writer import content_hash
from src.ingest.worker import IngestWorker, MAX_ATTEMPTS


def test_content_hash_stable() -> None:
    h1 = content_hash({"a": 1})
    h2 = content_hash({"a": 1})
    assert h1 == h2


def test_nack_moves_to_dlq_after_max_attempts() -> None:
    dispatcher = MagicMock(spec=IngestDispatcher)
    worker = IngestWorker(dispatcher)
    row = {
        "id": 1,
        "aggregate_type": "movie",
        "aggregate_id": "m1",
        "op": "upsert",
        "payload": {},
        "prompt_version": "1.0",
        "model_name": "test",
        "attempts": MAX_ATTEMPTS - 1,
    }
    with patch.object(worker, "_connect") as mock_conn:
        conn = MagicMock()
        cur = MagicMock()
        mock_conn.return_value.__enter__ = MagicMock(return_value=conn)
        mock_conn.return_value.__exit__ = MagicMock(return_value=False)
        conn.cursor.return_value.__enter__ = MagicMock(return_value=cur)
        conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        worker.nack(row, "boom")
        assert cur.execute.call_count >= 2


def test_nack_exponential_backoff_before_dlq() -> None:
    dispatcher = MagicMock(spec=IngestDispatcher)
    worker = IngestWorker(dispatcher)
    row = {
        "id": 2,
        "aggregate_type": "feed",
        "aggregate_id": "f1",
        "op": "upsert",
        "payload": {},
        "prompt_version": "1.0",
        "model_name": "test",
        "attempts": 0,
    }
    with patch.object(worker, "_connect") as mock_conn:
        conn = MagicMock()
        cur = MagicMock()
        mock_conn.return_value.__enter__ = MagicMock(return_value=conn)
        mock_conn.return_value.__exit__ = MagicMock(return_value=False)
        conn.cursor.return_value.__enter__ = MagicMock(return_value=cur)
        conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        worker.nack(row, "transient")
        sql = cur.execute.call_args[0][0]
        assert "next_attempt_at" in sql
        assert cur.execute.call_count == 1


def test_needs_reprocess_when_payload_prompt_version_stale() -> None:
    dispatcher = MagicMock(spec=IngestDispatcher)
    worker = IngestWorker(dispatcher)
    row = {
        "id": 3,
        "aggregate_type": "movie",
        "aggregate_id": "m1",
        "op": "upsert",
        "payload": {"prompt_version": "0.9"},
        "prompt_version": "1.0",
        "model_name": "test",
        "attempts": 0,
    }
    with patch("src.ingest.worker.get_settings") as mock_settings:
        mock_settings.return_value.ontology.prompt_version = "1.0"
        assert worker.needs_reprocess(row) is True


def test_process_row_reenqueue_on_prompt_version_mismatch() -> None:
    dispatcher = MagicMock(spec=IngestDispatcher)
    outbox = MagicMock()
    outbox.enqueue.return_value = 99
    worker = IngestWorker(dispatcher, outbox_writer=outbox)
    row = {
        "id": 4,
        "aggregate_type": "comment",
        "aggregate_id": "c1",
        "op": "upsert",
        "payload": {"prompt_version": "0.9", "text": "hi"},
        "prompt_version": "0.9",
        "model_name": "test",
        "attempts": 0,
    }
    with patch("src.ingest.worker.get_settings") as mock_settings:
        mock_settings.return_value.ontology.prompt_version = "1.0"
        with patch.object(worker, "ack") as mock_ack:
            worker.process_row(row)
    outbox.enqueue.assert_called_once()
    dispatcher.dispatch.assert_not_called()
    mock_ack.assert_called_once_with(4)


def test_process_row_dispatches_when_versions_match() -> None:
    dispatcher = MagicMock(spec=IngestDispatcher)
    outbox = MagicMock()
    worker = IngestWorker(dispatcher, outbox_writer=outbox)
    row = {
        "id": 5,
        "aggregate_type": "movie",
        "aggregate_id": "m2",
        "op": "upsert",
        "payload": {"title": "Inception"},
        "prompt_version": "1.0",
        "model_name": "test",
        "attempts": 0,
    }
    with patch("src.ingest.worker.get_settings") as mock_settings:
        mock_settings.return_value.ontology.prompt_version = "1.0"
        with patch.object(worker, "ack") as mock_ack:
            worker.process_row(row)
    dispatcher.dispatch.assert_called_once_with("movie", row["payload"])
    outbox.enqueue.assert_not_called()
    mock_ack.assert_called_once_with(5)


def test_mock_extract_load_handler() -> None:
    handler = mock_extract_load_handler("movie")
    handler({"movie_id": 42})
    extracted = mock_extract("movie", {"movie_id": 42})
    assert extracted["aggregate_type"] == "movie"
    assert extracted["source"]["movie_id"] == 42


def test_dispatcher_unknown_aggregate_raises() -> None:
    d = IngestDispatcher()
    with pytest.raises(ValueError, match="No handler"):
        d.dispatch("unknown", {})
