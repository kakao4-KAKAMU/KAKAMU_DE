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
        "aggregate_id": "m-1",
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


# ---------------------------------------------------------------------------
# Dependency waiting / sweep 테스트
# ---------------------------------------------------------------------------

from src.ingest.dependency import Dependency, DependencyResolver


def test_process_row_marks_waiting_when_deps_unmet() -> None:
    """comment 가 feed(done) 없이 도착하면 waiting 전이."""
    dispatcher = MagicMock(spec=IngestDispatcher)
    resolver = DependencyResolver()
    worker = IngestWorker(dispatcher, dependency_resolver=resolver)
    row = {
        "id": 10,
        "aggregate_type": "comment",
        "aggregate_id": "c-1",
        "op": "upsert",
        "payload": {"comment_id": "c-1", "feed_id": "f-1", "user_id": "u-1", "content": "hello"},
        "prompt_version": "1.0",
        "model_name": "test",
        "attempts": 0,
    }
    with patch("src.ingest.worker.get_settings") as mock_settings:
        mock_settings.return_value.ontology.prompt_version = "1.0"
        with patch.object(worker, "mark_waiting") as mock_wait:
            with patch.object(worker, "_check_deps") as mock_check:
                mock_check.return_value = [Dependency("feed", "f-1")]
                worker.process_row(row)

    mock_wait.assert_called_once()
    deps_arg = mock_wait.call_args[0][1]
    assert Dependency("feed", "f-1") in deps_arg
    dispatcher.dispatch.assert_not_called()


def test_process_row_dispatches_when_deps_met() -> None:
    """comment 의 선행 feed 가 done 이면 정상 dispatch."""
    dispatcher = MagicMock(spec=IngestDispatcher)
    resolver = DependencyResolver()
    worker = IngestWorker(dispatcher, dependency_resolver=resolver)
    row = {
        "id": 11,
        "aggregate_type": "comment",
        "aggregate_id": "c-2",
        "op": "upsert",
        "payload": {"comment_id": "c-2", "feed_id": "f-1", "user_id": "u-1", "content": "hi"},
        "prompt_version": "1.0",
        "model_name": "test",
        "attempts": 0,
    }
    with patch("src.ingest.worker.get_settings") as mock_settings:
        mock_settings.return_value.ontology.prompt_version = "1.0"
        with patch.object(worker, "_check_deps", return_value=None):
            with patch.object(worker, "ack") as mock_ack:
                worker.process_row(row)
    dispatcher.dispatch.assert_called_once()
    mock_ack.assert_called_once_with(11)


def test_release_ready_calls_sweep_sql() -> None:
    """release_ready 가 sweep SQL 을 실행하는지 확인."""
    dispatcher = MagicMock(spec=IngestDispatcher)
    worker = IngestWorker(dispatcher)
    with patch.object(worker, "_connect") as mock_conn:
        conn = MagicMock()
        cur = MagicMock()
        cur.rowcount = 2
        mock_conn.return_value.__enter__ = MagicMock(return_value=conn)
        mock_conn.return_value.__exit__ = MagicMock(return_value=False)
        conn.cursor.return_value.__enter__ = MagicMock(return_value=cur)
        conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        released = worker.release_ready()
    assert released == 2
    sql = cur.execute.call_args[0][0]
    assert "waiting" in sql
    assert "ingest_dependencies" in sql


def test_release_in_flight_reverts_processing_rows() -> None:
    """release_in_flight 는 추적 중인 processing row 를 pending 으로 복귀."""
    dispatcher = MagicMock(spec=IngestDispatcher)
    worker = IngestWorker(dispatcher)
    worker._track_in_flight(7)
    worker._track_in_flight(8)
    with patch.object(worker, "_connect") as mock_conn:
        conn = MagicMock()
        cur = MagicMock()
        cur.rowcount = 2
        mock_conn.return_value.__enter__ = MagicMock(return_value=conn)
        mock_conn.return_value.__exit__ = MagicMock(return_value=False)
        conn.cursor.return_value.__enter__ = MagicMock(return_value=cur)
        conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        released = worker.release_in_flight()
    assert released == 2
    sql, params = cur.execute.call_args[0]
    assert "processing" in sql
    assert set(params[0]) == {7, 8}
    assert worker._in_flight == set()


def test_release_in_flight_noop_when_empty() -> None:
    dispatcher = MagicMock(spec=IngestDispatcher)
    worker = IngestWorker(dispatcher)
    with patch.object(worker, "_connect") as mock_conn:
        released = worker.release_in_flight()
    assert released == 0
    mock_conn.assert_not_called()


def test_run_once_untracks_in_flight_after_processing() -> None:
    dispatcher = MagicMock(spec=IngestDispatcher)
    worker = IngestWorker(dispatcher)
    row = {"id": 21, "aggregate_type": "movie", "payload": {}, "prompt_version": "1.0", "model_name": "test", "attempts": 0}
    with patch.object(worker, "release_ready"):
        with patch.object(worker, "claim_batch", return_value=[row]):
            with patch.object(worker, "process_row"):
                worker.run_once()
    assert worker._in_flight == set()


def test_run_once_calls_release_ready_before_claim() -> None:
    """run_once 는 claim_batch 전에 release_ready 를 호출한다."""
    dispatcher = MagicMock(spec=IngestDispatcher)
    worker = IngestWorker(dispatcher)
    call_order = []
    with patch.object(worker, "release_ready", side_effect=lambda: call_order.append("release")):
        with patch.object(worker, "claim_batch", side_effect=lambda: (call_order.append("claim"), [])[1]):
            worker.run_once()
    assert call_order == ["release", "claim"]


def test_no_deps_aggregate_dispatches_directly() -> None:
    """movie 는 deps 없이 바로 dispatch."""
    dispatcher = MagicMock(spec=IngestDispatcher)
    resolver = DependencyResolver()
    worker = IngestWorker(dispatcher, dependency_resolver=resolver)
    row = {
        "id": 12,
        "aggregate_type": "movie",
        "aggregate_id": "m-1",
        "op": "upsert",
        "payload": {"movie_id": "m-1", "title": "test"},
        "prompt_version": "1.0",
        "model_name": "test",
        "attempts": 0,
    }
    with patch("src.ingest.worker.get_settings") as mock_settings:
        mock_settings.return_value.ontology.prompt_version = "1.0"
        with patch.object(worker, "_check_deps", return_value=None):
            with patch.object(worker, "ack"):
                worker.process_row(row)
    dispatcher.dispatch.assert_called_once_with("movie", row["payload"])
