"""Outbox worker (SKIP LOCKED + backoff + DLQ)."""

from __future__ import annotations

import asyncio
import json
import logging
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from typing import Any, Iterator, Optional

import psycopg

from src.config.settings import PostgresSettings, get_settings
from src.ingest.dispatcher import IngestDispatcher
from src.ingest.outbox_writer import OutboxWriter
from src.persistence.db import get_connection

logger = logging.getLogger(__name__)

MAX_ATTEMPTS = 3
BATCH_SIZE = 10


class IngestWorker:
    def __init__(
        self,
        dispatcher: IngestDispatcher,
        settings: Optional[PostgresSettings] = None,
        *,
        outbox_writer: Optional[OutboxWriter] = None,
    ) -> None:
        self._dispatcher = dispatcher
        self._settings = settings or get_settings().postgres
        self._outbox = outbox_writer or OutboxWriter(self._settings)

    @contextmanager
    def _connect(self) -> Iterator[psycopg.Connection]:
        """공유 풀에서 connection 을 빌려오는 context manager.

        테스트는 ``patch.object(worker, "_connect")`` 로 mock 한다.
        """

        with get_connection(self._settings) as conn:
            yield conn

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
                print(row["payload"], type(row["payload"]))
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
        self._dispatcher.dispatch(row["aggregate_type"], row["payload"])
        self.ack(row["id"])

    def run_once(self) -> int:
        rows = self.claim_batch()
        for row in rows:
            try:
                self.process_row(row)
            except Exception as exc:
                logger.exception("Ingest failed id=%s", row["id"])
                self.nack(row, str(exc))
        return len(rows)

    async def run_loop(self, *, concurrency: int = 4, poll_interval: float = 1.0) -> None:
        sem = asyncio.Semaphore(concurrency)

        async def _tick() -> None:
            async with sem:
                await asyncio.to_thread(self.run_once)

        while True:
            try:
                await asyncio.gather(*[_tick() for _ in range(concurrency)])
            except Exception as exc:
                logger.exception("Ingest loop failed", exc_info=True)
            await asyncio.sleep(poll_interval)


__all__ = ["IngestWorker", "MAX_ATTEMPTS"]
