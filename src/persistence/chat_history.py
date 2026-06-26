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
from typing import Any, List, Optional
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel
from src.config.settings import PostgresSettings, get_settings
from src.persistence.db import get_connection
from src.chat.state import ReplyMetadata
DDL = """
CREATE TABLE IF NOT EXISTS chat_session (
    session_id   UUID PRIMARY KEY,
    user_id      TEXT NOT NULL,
    persona_id   TEXT DEFAULT NULL,
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
    reply_metadata     JSONB DEFAULT '{}'::jsonb,
    ontology_ref JSONB,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_chat_message_session
    ON chat_message(session_id, created_at);

CREATE INDEX IF NOT EXISTS idx_chat_message_user_time
    ON chat_message(user_id, created_at DESC);
"""

class ChatSession(BaseModel):
    session_id: UUID
    user_id: str
    persona_id: Optional[str]
    started_at: datetime
    last_active: datetime
    metadata: dict[str, Any]

class ChatSessionList(BaseModel):
    sessions: list[ChatSession]

class ChatMessage(BaseModel):
    id: int
    session_id: UUID
    user_id: str
    role: str
    content: str
    created_at: datetime
    reply_metadata: Optional[ReplyMetadata]


class ChatHistoryStore:
    def __init__(self, settings: Optional[PostgresSettings] = None) -> None:
        self._settings = settings or get_settings().postgres

    def init_schema(self) -> None:
        with get_connection(self._settings) as conn, conn.cursor() as cur:
            cur.execute(DDL)
            conn.commit()

    def open_session(self, *, session_id: str, user_id: str, persona_id: Optional[str] = None, metadata: dict | None = None) -> None:
        with get_connection(self._settings) as conn, conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO chat_session (session_id, user_id, persona_id, metadata)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (session_id) DO UPDATE
                    SET last_active = NOW()
                """,
                (session_id, user_id, persona_id, json.dumps(metadata or {})),
            )
            conn.commit()
    
    def get_session_by_id(self, *, session_id: str) -> Optional[ChatSession]:
        with get_connection(self._settings) as conn, conn.cursor() as cur:
            cur.execute(
                """
                SELECT session_id, user_id, persona_id, started_at, last_active, metadata
                FROM chat_session
                WHERE session_id = %s
            """, (session_id,))
            row = cur.fetchone()
            if row:
                return ChatSession(
                    session_id=row[0],
                    user_id=row[1],
                    persona_id=row[2],
                    started_at=row[3],
                    last_active=row[4],
                    metadata=row[5],
                )
            return None

    def list_sessions(self, *, user_id: str, cursor: Optional[int] = None, limit: int = 20) -> list[ChatSession]:
        with get_connection(self._settings) as conn, conn.cursor() as cur:
            cur.execute(
                """
                SELECT session_id, user_id, persona_id, started_at, last_active, metadata
                FROM chat_session
                WHERE user_id = %s
                ORDER BY started_at DESC
                LIMIT %s
                OFFSET %s
            """, (user_id, limit, cursor))
            rows = cur.fetchall()
            return [
                ChatSession(
                    session_id=r[0],
                    user_id=r[1],
                    persona_id=r[2],
                    started_at=r[3],
                    last_active=r[4],
                    metadata=r[5],
                )
                for r in rows
            ]

    def get_session_history(
        self, *, session_id: str, user_id: str, cursor: Optional[int] = None, limit: int = 20
    ) -> list[ChatMessage]:
        with get_connection(self._settings) as conn, conn.cursor() as cur:
            if cursor is None:
                cur.execute(
                    """
                    SELECT id, session_id, user_id, role, content, reply_metadata, created_at
                    FROM chat_message
                    WHERE session_id = %s
                    AND user_id = %s
                    ORDER BY id DESC
                    LIMIT %s
                    """,
                    (session_id, user_id, limit),
                )
            else:
                cur.execute(
                    """
                    SELECT id, session_id, user_id, role, content, reply_metadata, created_at
                    FROM chat_message
                    WHERE session_id = %s AND id < %s AND user_id = %s
                    ORDER BY id DESC
                    LIMIT %s
                    """,
                    (session_id, cursor, user_id, limit),
                )
            rows = cur.fetchall()
            messages = [
                ChatMessage.model_validate({
                    "id": r[0],
                    "session_id": r[1],
                    "user_id": r[2],
                    "role": r[3],
                    "content": r[4],
                    "reply_metadata": r[5],
                    "created_at": r[6],
                })
                for r in rows
            ]
            # API 응답은 오래된 메시지 -> 최신 메시지 순으로 반환한다.
            return list(reversed(messages))

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
        reply_metadata: Optional[dict[str, Any]] = None,
    ) -> int:
        with get_connection(self._settings) as conn, conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO chat_message
                  (session_id, user_id, role, content, tool_name,
                   tokens_in, tokens_out, ontology_ref, reply_metadata)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
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
                    json.dumps(reply_metadata) if reply_metadata else None,
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


__all__ = ["ChatHistoryStore", "ChatSession", "ChatSessionList", "ChatMessage"]
