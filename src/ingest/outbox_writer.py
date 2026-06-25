"""Outbox enqueue (batched)."""

from __future__ import annotations

import hashlib
import json
import logging
import threading
from dataclasses import dataclass, field
from typing import Any, Mapping, Optional

from pydantic import BaseModel

from src.config.settings import PostgresSettings, get_settings
from src.persistence.db import get_connection

logger = logging.getLogger(__name__)

DEFAULT_BATCH_MAX_SIZE = 100
DEFAULT_FLUSH_INTERVAL_SEC = 1.0

_ROW_PLACEHOLDERS = "(%s, %s, %s, %s::jsonb, %s, %s, %s)"


def _build_batch_insert_sql(row_count: int) -> str:
    if row_count < 1:
        raise ValueError("row_count must be >= 1")
    values = ", ".join(_ROW_PLACEHOLDERS for _ in range(row_count))
    return f"""
INSERT INTO ingest_outbox
  (aggregate_type, aggregate_id, op, payload, prompt_version, model_name, content_hash)
VALUES {values}
RETURNING id
"""


def _flatten_rows(rows: list[tuple[Any, ...]]) -> list[Any]:
    return [value for row in rows for value in row]


def json_dumps(payload: Mapping[str, Any] | BaseModel) -> str:
    if isinstance(payload, BaseModel):
        payload = payload.model_dump(mode="json")
    return json.dumps(payload, sort_keys=True, ensure_ascii=False)


def content_hash(payload: Mapping[str, Any] | BaseModel) -> str:
    raw = json_dumps(payload)
    return hashlib.sha256(raw.encode()).hexdigest()


@dataclass
class _PendingItem:
    row: tuple[Any, ...]
    event: threading.Event = field(default_factory=threading.Event)
    result_id: int | None = None
    error: BaseException | None = None


class OutboxWriter:
    """ingest_outbox 적재. 최대 ``batch_max_size`` 건 또는 ``flush_interval_sec`` 경과 시 일괄 INSERT."""

    def __init__(
        self,
        settings: Optional[PostgresSettings] = None,
        *,
        batch_max_size: int = DEFAULT_BATCH_MAX_SIZE,
        flush_interval_sec: float = DEFAULT_FLUSH_INTERVAL_SEC,
    ) -> None:
        if batch_max_size < 1:
            raise ValueError("batch_max_size must be >= 1")
        if flush_interval_sec <= 0:
            raise ValueError("flush_interval_sec must be > 0")

        self._settings = settings or get_settings().postgres
        self._batch_max_size = batch_max_size
        self._flush_interval_sec = flush_interval_sec
        self._lock = threading.Lock()
        self._buffer: list[_PendingItem] = []
        self._timer: threading.Timer | None = None

    def enqueue(
        self,
        *,
        aggregate_type: str,
        aggregate_id: str,
        payload: Mapping[str, Any] | BaseModel,
        op: str = "upsert",
        prompt_version: Optional[str] = None,
        model_name: Optional[str] = None,
        wait: bool = True,
    ) -> int:
        app = get_settings()
        pv = prompt_version or app.ontology.prompt_version
        mn = model_name or app.ontology.model_name
        ch = content_hash(payload)
        raw = json_dumps(payload)

        item = _PendingItem(
            row=(aggregate_type, aggregate_id, op, raw, pv, mn, ch),
        )
        to_flush: list[_PendingItem] | None = None

        with self._lock:
            self._buffer.append(item)
            if len(self._buffer) >= self._batch_max_size:
                to_flush = self._drain_buffer_locked()
            else:
                self._schedule_flush_locked()

        if to_flush is not None:
            self._flush_items(to_flush)

        if not wait:
            return 0

        item.event.wait()
        if item.error is not None:
            raise item.error
        assert item.result_id is not None
        return item.result_id

    def flush(self) -> None:
        """버퍼에 남은 항목을 즉시 INSERT 한다 (종료·배치 작업 마무리용)."""
        with self._lock:
            to_flush = self._drain_buffer_locked()
        if to_flush:
            self._flush_items(to_flush)

    def _drain_buffer_locked(self) -> list[_PendingItem] | None:
        if not self._buffer:
            self._cancel_timer_locked()
            return None
        items = self._buffer
        self._buffer = []
        self._cancel_timer_locked()
        return items

    def _schedule_flush_locked(self) -> None:
        if self._timer is not None:
            return
        timer = threading.Timer(self._flush_interval_sec, self._on_timer)
        timer.daemon = True
        self._timer = timer
        timer.start()

    def _cancel_timer_locked(self) -> None:
        if self._timer is not None:
            self._timer.cancel()
            self._timer = None

    def _on_timer(self) -> None:
        with self._lock:
            to_flush = self._drain_buffer_locked()
        if to_flush:
            self._flush_items(to_flush)

    def _flush_items(self, items: list[_PendingItem]) -> None:
        rows = [item.row for item in items]
        try:
            ids = self._insert_batch(rows)
        except Exception as exc:
            logger.exception("Outbox batch insert failed (size=%d)", len(items))
            for item in items:
                item.error = exc
                item.event.set()
            return

        for item, row_id in zip(items, ids, strict=True):
            item.result_id = int(row_id)
            item.event.set()

        logger.debug("Outbox batch flushed: count=%d", len(ids))

    def _insert_batch(self, rows: list[tuple[Any, ...]]) -> list[int]:
        if not rows:
            return []
        with get_connection(self._settings) as conn, conn.cursor() as cur:
            cur.execute(_build_batch_insert_sql(len(rows)), _flatten_rows(rows))
            ids = [int(row[0]) for row in cur.fetchall()]
            conn.commit()
        return ids


__all__ = [
    "DEFAULT_BATCH_MAX_SIZE",
    "DEFAULT_FLUSH_INTERVAL_SEC",
    "OutboxWriter",
    "content_hash",
]
