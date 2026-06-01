"""채팅 이력 PostgreSQL 적재.

LangGraph 의 `PostgresSaver` 와 호환되는 chat history 스토어.

설계 원칙
---------
- SRP : 채팅 메시지의 영속화만 책임.
- DIP : 상위 LangGraph 그래프는 본 인터페이스(저장/조회) 에만 의존한다.
- 공유 풀(`src/persistence/db.py`) 을 사용해 매 호출 connect 비용을 제거한다.
"""

from __future__ import annotations

import json
from typing import Any, List, Optional, TypedDict
from datetime import datetime
from src.config.settings import PostgresSettings, get_settings
from src.persistence.db import get_connection

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

class ChatSession(TypedDict):
    session_id: str
    user_id: str
    started_at: datetime
    last_active: datetime
    metadata: dict[str, Any]

class ChatHistoryStore:
    def __init__(self, settings: Optional[PostgresSettings] = None) -> None:
        self._settings = settings or get_settings().postgres

    def init_schema(self) -> None:
        with get_connection(self._settings) as conn, conn.cursor() as cur:
            cur.execute(DDL)
            conn.commit()

    def open_session(self, *, session_id: str, user_id: str, metadata: dict | None = None) -> None:
        with get_connection(self._settings) as conn, conn.cursor() as cur:
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

    def list_sessions(self) -> list[ChatSession]:
        with get_connection(self._settings) as conn, conn.cursor() as cur:
            cur.execute(
                """
                SELECT session_id, user_id, started_at, last_active, metadata
                FROM chat_session
                ORDER BY started_at DESC
            """)
            rows = cur.fetchall()
            return [
                {
                    "session_id": r[0],
                    "user_id": r[1],
                    "started_at": r[2],
                    "last_active": r[3],
                    "metadata": r[4],
                }
                for r in rows
            ]

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
        with get_connection(self._settings) as conn, conn.cursor() as cur:
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
        with get_connection(self._settings) as conn, conn.cursor() as cur:
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


__all__ = ["ChatHistoryStore", "ChatSession"]
