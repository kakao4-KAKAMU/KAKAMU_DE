"""채팅 이력 PostgreSQL 적재.

LangGraph 의 `PostgresSaver` 와 호환되는 chat history 스토어.

설계 원칙
---------
- SRP : 채팅 메시지의 영속화만 책임.
- DIP : 상위 LangGraph 그래프는 본 인터페이스(저장/조회) 에만 의존한다.
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any, List, Optional

import psycopg

from src.config.settings import PostgresSettings, get_settings


DDL = """
CREATE TABLE IF NOT EXISTS chat_session (
    session_id   UUID PRIMARY KEY,
    user_id      TEXT NOT NULL,
    started_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_active  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    metadata     JSONB DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_chat_session_user ON chat_session(user_id);

CREATE TABLE IF NOT EXISTS chat_message (
    id           BIGSERIAL PRIMARY KEY,
    session_id   UUID NOT NULL REFERENCES chat_session(session_id) ON DELETE CASCADE,
    user_id      TEXT NOT NULL,
    role         TEXT NOT NULL CHECK (role IN ('system','user','assistant','tool')),
    content      TEXT NOT NULL,
    tool_name    TEXT,
    tokens_in    INTEGER,
    tokens_out   INTEGER,
    ontology_ref JSONB,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_chat_message_session
    ON chat_message(session_id, created_at);

CREATE INDEX IF NOT EXISTS idx_chat_message_user_time
    ON chat_message(user_id, created_at DESC);
"""


class ChatHistoryStore:
    def __init__(self, settings: Optional[PostgresSettings] = None) -> None:
        self._settings = settings or get_settings().postgres

    # ------------------------------------------------------------------
    def _connect(self) -> psycopg.Connection:
        return psycopg.connect(
            host=self._settings.host,
            port=self._settings.port,
            dbname=self._settings.database,
            user=self._settings.user,
            password=self._settings.password,
        )

    def init_schema(self) -> None:
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(DDL)
            conn.commit()

    # ------------------------------------------------------------------
    def open_session(self, *, session_id: str, user_id: str, metadata: dict | None = None) -> None:
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO chat_session (session_id, user_id, metadata)
                VALUES (%s, %s, %s)
                ON CONFLICT (session_id) DO UPDATE
                    SET last_active = NOW()
                """,
                (session_id, user_id, json.dumps(metadata or {})),
            )
            conn.commit()

    def append(
        self,
        *,
        session_id: str,
        user_id: str,
        role: str,
        content: str,
        tool_name: Optional[str] = None,
        tokens_in: Optional[int] = None,
        tokens_out: Optional[int] = None,
        ontology_ref: Optional[dict[str, Any]] = None,
    ) -> int:
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO chat_message
                  (session_id, user_id, role, content, tool_name,
                   tokens_in, tokens_out, ontology_ref)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                (
                    session_id,
                    user_id,
                    role,
                    content,
                    tool_name,
                    tokens_in,
                    tokens_out,
                    json.dumps(ontology_ref) if ontology_ref else None,
                ),
            )
            (msg_id,) = cur.fetchone()
            cur.execute(
                "UPDATE chat_session SET last_active = NOW() WHERE session_id = %s",
                (session_id,),
            )
            conn.commit()
            return int(msg_id)

    def recent(self, *, session_id: str, limit: int = 50) -> List[dict]:
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, role, content, created_at
                FROM chat_message
                WHERE session_id = %s
                ORDER BY created_at DESC
                LIMIT %s
                """,
                (session_id, limit),
            )
            rows = cur.fetchall()
            return [
                {"id": r[0], "role": r[1], "content": r[2], "created_at": r[3]}
                for r in reversed(rows)
            ]


__all__ = ["ChatHistoryStore"]
