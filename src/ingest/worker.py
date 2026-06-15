"""Outbox worker (SKIP LOCKED + backoff + DLQ + dependency waiting)."""

from __future__ import annotations

import asyncio
import json
import logging
import threading
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from typing import Any, Iterator, Optional, Sequence

import psycopg

from src.config.settings import PostgresSettings, get_settings
from src.ingest.dependency import Dependency, DependencyResolver
from src.ingest.dispatcher import IngestDispatcher
from src.ingest.outbox_writer import OutboxWriter
from src.persistence.db import get_connection

logger = logging.getLogger(__name__)

MAX_ATTEMPTS = 3
BATCH_SIZE = 10

_RELEASE_READY_SQL = """
UPDATE ingest_outbox o
SET status = 'pending', updated_at = NOW()
WHERE o.status = 'waiting'
  AND NOT EXISTS (
    SELECT 1 FROM ingest_dependencies d
    WHERE d.outbox_id = o.id
      AND NOT EXISTS (
        SELECT 1 FROM ingest_outbox p
        WHERE p.aggregate_type = d.dep_type
          AND p.aggregate_id = d.dep_id
          AND p.status = 'done'
      )
  )
"""

_CHECK_DEPS_MET_SQL = """
SELECT d.dep_type, d.dep_id
FROM ingest_dependencies d
WHERE d.outbox_id = %s
  AND NOT EXISTS (
    SELECT 1 FROM ingest_outbox p
    WHERE p.aggregate_type = d.dep_type
      AND p.aggregate_id = d.dep_id
      AND p.status = 'done'
  )
LIMIT 1
"""


class IngestWorker:
    def __init__(
        self,
        dispatcher: IngestDispatcher,
        settings: Optional[PostgresSettings] = None,
        *,
        outbox_writer: Optional[OutboxWriter] = None,
        dependency_resolver: Optional[DependencyResolver] = None,
    ) -> None:
        self._dispatcher = dispatcher
        self._settings = settings or get_settings().postgres
        self._outbox = outbox_writer or OutboxWriter(self._settings)
        self._resolver = dependency_resolver or DependencyResolver()
        self._in_flight: set[int] = set()
        self._in_flight_lock = threading.Lock()

    @contextmanager
    def _connect(self) -> Iterator[psycopg.Connection]:
        """공유 풀에서 connection 을 빌려오는 context manager.

        테스트는 ``patch.object(worker, "_connect")`` 로 mock 한다.
        """

        with get_connection(self._settings) as conn:
            yield conn

    # ------------------------------------------------------------------
    # Sweep: waiting → pending (모든 dep 충족)
    # ------------------------------------------------------------------
    def release_ready(self) -> int:
        """waiting 상태 row 중 모든 의존성이 done 인 것을 pending 으로 복귀."""
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(_RELEASE_READY_SQL)
            released = cur.rowcount
            conn.commit()
        if released:
            logger.info("Released %d waiting rows to pending", released)
        return released

    def release_in_flight(self) -> int:
        """Worker 종료 시 claim 후 미완료 processing row 를 pending 으로 복귀."""
        with self._in_flight_lock:
            ids = list(self._in_flight)
            self._in_flight.clear()
        if not ids:
            return 0
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                """
                UPDATE ingest_outbox
                SET status = 'pending', updated_at = NOW()
                WHERE id = ANY(%s) AND status = 'processing'
                """,
                (ids,),
            )
            released = cur.rowcount
            conn.commit()
        if released:
            logger.info(
                "Released %d in-flight processing rows to pending (ids=%s)",
                released,
                ids,
            )
        return released

    def _track_in_flight(self, outbox_id: int) -> None:
        with self._in_flight_lock:
            self._in_flight.add(outbox_id)

    def _untrack_in_flight(self, outbox_id: int) -> None:
        with self._in_flight_lock:
            self._in_flight.discard(outbox_id)

    # ------------------------------------------------------------------
    # Claim
    # ------------------------------------------------------------------
    def claim_batch(self) -> list[dict[str, Any]]:
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                """
                WITH cte AS (
                    SELECT id FROM ingest_outbox
                    WHERE status = 'pending' AND next_attempt_at <= NOW()
                    ORDER BY id
                    FOR UPDATE SKIP LOCKED
                    LIMIT %s
                )
                UPDATE ingest_outbox o
                SET status = 'processing', updated_at = NOW()
                FROM cte
                WHERE o.id = cte.id
                RETURNING o.id, o.aggregate_type, o.aggregate_id, o.op, o.payload,
                          o.prompt_version, o.model_name, o.attempts
                """,
                (BATCH_SIZE,),
            )
            rows = cur.fetchall()
            conn.commit()
            return [
                {
                    "id": r[0],
                    "aggregate_type": r[1],
                    "aggregate_id": r[2],
                    "op": r[3],
                    "payload": r[4] if isinstance(r[4], dict) else json.loads(r[4]),
                    "prompt_version": r[5],
                    "model_name": r[6],
                    "attempts": r[7],
                }
                for r in rows
            ]

    # ------------------------------------------------------------------
    # Ack / Nack
    # ------------------------------------------------------------------
    def ack(self, outbox_id: int) -> None:
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                "UPDATE ingest_outbox SET status='done', updated_at=NOW() WHERE id=%s",
                (outbox_id,),
            )
            conn.commit()

    def nack(self, row: dict[str, Any], error: str) -> None:
        attempts = int(row["attempts"]) + 1
        with self._connect() as conn, conn.cursor() as cur:
            if attempts >= MAX_ATTEMPTS:
                cur.execute(
                    """
                    INSERT INTO ingest_dlq
                      (outbox_id, aggregate_type, aggregate_id, payload,
                       prompt_version, model_name, last_error)
                    VALUES (%s, %s, %s, %s::jsonb, %s, %s, %s)
                    """,
                    (
                        row["id"],
                        row["aggregate_type"],
                        row["aggregate_id"],
                        json.dumps(row["payload"]),
                        row["prompt_version"],
                        row["model_name"],
                        error,
                    ),
                )
                cur.execute(
                    "UPDATE ingest_outbox SET status='dlq', last_error=%s WHERE id=%s",
                    (error, row["id"]),
                )
            else:
                delay = 2**attempts
                next_at = datetime.now(timezone.utc) + timedelta(seconds=delay)
                cur.execute(
                    """
                    UPDATE ingest_outbox
                    SET status='pending', attempts=%s, last_error=%s,
                        next_attempt_at=%s, updated_at=NOW()
                    WHERE id=%s
                    """,
                    (attempts, error, next_at, row["id"]),
                )
            conn.commit()

    # ------------------------------------------------------------------
    # Dependency: mark_waiting
    # ------------------------------------------------------------------
    def mark_waiting(
        self, row: dict[str, Any], deps: Sequence[Dependency]
    ) -> None:
        """processing → waiting 전이 + ingest_dependencies 기록.

        트랜잭션 내에서 dep 을 insert 한 뒤 이미 모두 충족됐으면 바로 pending 으로 복귀.
        """
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                "UPDATE ingest_outbox SET status='waiting', updated_at=NOW() WHERE id=%s",
                (row["id"],),
            )
            for dep in deps:
                cur.execute(
                    "INSERT INTO ingest_dependencies (outbox_id, dep_type, dep_id) VALUES (%s, %s, %s)",
                    (row["id"], dep.dep_type, dep.dep_id),
                )
            cur.execute(_CHECK_DEPS_MET_SQL, (row["id"],))
            unmet = cur.fetchone()
            if unmet is None:
                cur.execute(
                    "UPDATE ingest_outbox SET status='pending', updated_at=NOW() WHERE id=%s",
                    (row["id"],),
                )
                logger.info("Deps already met for id=%s, back to pending", row["id"])
            else:
                logger.info(
                    "Waiting id=%s for dep_type=%s dep_id=%s",
                    row["id"], unmet[0], unmet[1],
                )
            conn.commit()

    def _check_deps(self, row: dict[str, Any]) -> Sequence[Dependency] | None:
        """의존성 해석 후 미충족 dep 이 있으면 전체 dep 목록 반환, 없으면 None."""
        deps = self._resolver.resolve(row["aggregate_type"], row["payload"])
        if not deps:
            return None
        with self._connect() as conn, conn.cursor() as cur:
            for dep in deps:
                cur.execute(
                    "SELECT 1 FROM ingest_outbox WHERE aggregate_type=%s AND aggregate_id=%s AND status='done' LIMIT 1",
                    (dep.dep_type, dep.dep_id),
                )
                if cur.fetchone() is None:
                    return deps
        return None

    # ------------------------------------------------------------------
    # Re-process / Dispatch
    # ------------------------------------------------------------------
    def needs_reprocess(self, row: dict[str, Any]) -> bool:
        """payload 또는 row 의 prompt_version 이 현재 설정과 다르면 재적재."""
        current = get_settings().ontology.prompt_version
        payload = row["payload"]
        payload_pv = payload.get("prompt_version")
        if payload_pv is not None and payload_pv != current:
            return True
        return row["prompt_version"] != current

    def reenqueue(self, row: dict[str, Any]) -> int:
        new_id = self._outbox.enqueue(
            aggregate_type=row["aggregate_type"],
            aggregate_id=row.get("aggregate_id", ""),
            op=row.get("op", "upsert"),
            payload=row["payload"],
        )
        logger.info(
            "Re-enqueued outbox id=%s -> new_id=%s (prompt_version=%s)",
            row["id"],
            new_id,
            get_settings().ontology.prompt_version,
        )
        return new_id

    def process_row(self, row: dict[str, Any]) -> None:
        if self.needs_reprocess(row):
            self.reenqueue(row)
            self.ack(row["id"])
            return

        unmet_deps = self._check_deps(row)
        if unmet_deps is not None:
            self.mark_waiting(row, unmet_deps)
            return

        self._dispatcher.dispatch(row["aggregate_type"], row["payload"])
        self.ack(row["id"])

    # ------------------------------------------------------------------
    # Run loop
    # ------------------------------------------------------------------
    def run_once(self) -> int:
        self.release_ready()
        rows = self.claim_batch()
        for row in rows:
            self._track_in_flight(row["id"])
            try:
                self.process_row(row)
            except Exception as exc:
                logger.exception("Ingest failed id=%s", row["id"])
                self.nack(row, str(exc))
            finally:
                self._untrack_in_flight(row["id"])
        return len(rows)

    async def run_loop(
        self,
        *,
        concurrency: int = 4,
        poll_interval: float = 1.0,
        stop_event: Optional[asyncio.Event] = None,
    ) -> None:
        stop = stop_event or asyncio.Event()
        sem = asyncio.Semaphore(concurrency)

        async def _tick() -> None:
            if stop.is_set():
                return
            async with sem:
                if stop.is_set():
                    return
                await asyncio.to_thread(self.run_once)

        try:
            while not stop.is_set():
                try:
                    await asyncio.gather(*[_tick() for _ in range(concurrency)])
                except Exception:
                    logger.exception("Ingest loop failed")
                if stop.is_set():
                    break
                try:
                    await asyncio.wait_for(stop.wait(), timeout=poll_interval)
                except asyncio.TimeoutError:
                    pass
        finally:
            self.release_in_flight()


__all__ = ["IngestWorker", "MAX_ATTEMPTS"]
