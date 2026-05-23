"""Outbox worker (SKIP LOCKED + backoff + DLQ)."""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import psycopg

from src.config.settings import PostgresSettings, get_settings
from src.ingest.dispatcher import IngestDispatcher

logger = logging.getLogger(__name__)

MAX_ATTEMPTS = 3
BATCH_SIZE = 10


class IngestWorker:
    def __init__(
        self,
        dispatcher: IngestDispatcher,
        settings: Optional[PostgresSettings] = None,
    ) -> None:
        self._dispatcher = dispatcher
        self._settings = settings or get_settings().postgres

    def _connect(self) -> psycopg.Connection:
        return psycopg.connect(
            host=self._settings.host,
            port=self._settings.port,
            dbname=self._settings.database,
            user=self._settings.user,
            password=self._settings.password,
        )

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
                RETURNING o.id, o.aggregate_type, o.aggregate_id, o.payload,
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
                    "payload": r[3] if isinstance(r[3], dict) else json.loads(r[3]),
                    "prompt_version": r[4],
                    "model_name": r[5],
                    "attempts": r[6],
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
                cur.execute("UPDATE ingest_outbox SET status='dlq', last_error=%s WHERE id=%s", (error, row["id"]))
            else:
                delay = 2 ** attempts
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

    def process_row(self, row: dict[str, Any]) -> None:
        app = get_settings()
        if row["prompt_version"] != app.ontology.prompt_version:
            logger.info("Reprocess due to prompt_version mismatch id=%s", row["id"])
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
            await asyncio.gather(*[_tick() for _ in range(concurrency)])
            await asyncio.sleep(poll_interval)


__all__ = ["IngestWorker", "MAX_ATTEMPTS"]
