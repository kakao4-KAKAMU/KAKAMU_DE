"""페르소나(Persona) ingest payload 스키마."""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import Field

from src.api.schemas.shared import IngestPayload


class IngestPersonaPayload(IngestPayload):
    """페르소나 등록/수정. Persona 노드와 선호 관계의 원천."""

    persona_id: str = Field(min_length=1, description="페르소나 고유 ID.")
    user_id: str = Field(min_length=1, description="소속 사용자 ID.")
    label: Optional[str] = Field(default=None, description="페르소나 표시명.")
    genres: List[str] = Field(
        default_factory=list,
        description="좋아하는 장르. (:Persona)-[:PREFERS]->(:Genre).",
    )
    movies: List[str] = Field(
        default_factory=list,
        description="관심 영화 ID 목록. (:Persona)-[:INTERACTED]->(:Movie).",
    )
    persons: List[str] = Field(
        default_factory=list,
        description="좋아하는 감독/배우 ID 목록. (:Persona)-[:INTERACTED]->(:Person).",
    )
    created_at: Optional[datetime] = Field(default=None, description="생성 시각 (ISO 8601).")
    modified_at: Optional[datetime] = Field(default=None, description="수정 시각 (ISO 8601).")


class IngestPersonaDeletePayload(IngestPayload):
    """페르소나 삭제."""

    persona_id: str = Field(min_length=1)
    user_id: str = Field(min_length=1)


__all__ = [
    "IngestPersonaPayload",
    "IngestPersonaDeletePayload",
]
