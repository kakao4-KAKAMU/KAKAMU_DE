from __future__ import annotations

from unittest.mock import MagicMock, patch

from src.ingest.dispatcher import IngestDispatcher
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
