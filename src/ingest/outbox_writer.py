"""Outbox enqueue."""

from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping, Optional

from src.config.settings import PostgresSettings, get_settings
from src.persistence.db import get_connection


def content_hash(payload: Mapping[str, Any]) -> str:
    raw = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(raw.encode()).hexdigest()


class OutboxWriter:
    def __init__(self, settings: Optional[PostgresSettings] = None) -> None:
        self._settings = settings or get_settings().postgres

    def enqueue(
        self,
        *,
        aggregate_type: str,
        aggregate_id: str,
        payload: Mapping[str, Any],
        op: str = "upsert",
        prompt_version: Optional[str] = None,
        model_name: Optional[str] = None,
    ) -> int:
        app = get_settings()
        pv = prompt_version or app.ontology.prompt_version
        mn = model_name or app.ontology.model_name
        ch = content_hash(payload)
        with get_connection(self._settings) as conn, conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO ingest_outbox
                  (aggregate_type, aggregate_id, op, payload, prompt_version, model_name, content_hash)
                VALUES (%s, %s, %s, %s::jsonb, %s, %s, %s)
                RETURNING id
                """,
                (
                    aggregate_type,
                    aggregate_id,
                    op,
                    json.dumps(payload),
                    pv,
                    mn,
                    ch,
                ),
            )
            (row_id,) = cur.fetchone()
            conn.commit()
            return int(row_id)


__all__ = ["OutboxWriter", "content_hash"]
