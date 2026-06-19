"""사용자(User) ingest payload 스키마."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import Field

from src.api.schemas.shared import IngestPayload


class IngestUserPayload(IngestPayload):
    """사용자 등록/갱신. Neo4j User 노드의 원천."""

    user_id: str = Field(min_length=1, description="사용자 고유 ID.")
    nickname: Optional[str] = Field(default=None, description="표시 이름.")
    created_at: Optional[datetime] = Field(default=None, description="가입 시각 (ISO 8601).")


__all__ = ["IngestUserPayload"]
