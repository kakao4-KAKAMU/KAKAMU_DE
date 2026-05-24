"""FastAPI 요청/응답 Pydantic 스키마.

SOLID
-----
- SRP : HTTP 표면 스키마만 정의. 도메인 객체로의 변환은 라우터에서.
"""

from __future__ import annotations

from typing import Any, Literal, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# /chat
# ---------------------------------------------------------------------------


class ChatRequest(BaseModel):
    user_id: str = Field(min_length=1)
    session_id: Optional[str] = Field(default=None)
    message: str = Field(min_length=1)
    top_k: int = Field(default=10, ge=1, le=50)
    max_toxicity: float = Field(default=0.7, ge=0.0, le=1.0)

    def ensure_session_id(self) -> str:
        return self.session_id or str(uuid4())


class ChatResponse(BaseModel):
    session_id: str
    reply: str
    arm_id: str
    movies: list[dict[str, Any]] = Field(default_factory=list)
    ontology_ref: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# /recommend
# ---------------------------------------------------------------------------


class RecommendRequest(BaseModel):
    user_id: str = Field(min_length=1)
    query: str = Field(min_length=1)
    top_k: int = Field(default=10, ge=1, le=50)
    vec_top_k: int = Field(default=30, ge=1, le=100)
    max_toxicity: float = Field(default=0.7, ge=0.0, le=1.0)


class RecommendResponse(BaseModel):
    arm_id: str
    movies: list[dict[str, Any]]
    keywords: list[str]
    themes: list[str]
    moods: list[str]


# ---------------------------------------------------------------------------
# /ingest
# ---------------------------------------------------------------------------


class IngestEnvelope(BaseModel):
    aggregate_id: str = Field(min_length=1)
    payload: dict[str, Any]


class IngestResponse(BaseModel):
    outbox_id: int


# ---------------------------------------------------------------------------
# /feedback
# ---------------------------------------------------------------------------


Action = Literal["click", "dwell", "like", "skip", "dislike"]


class FeedbackRequest(BaseModel):
    user_id: str = Field(min_length=1)
    arm_id: str = Field(min_length=1)
    action: Action
    dwell_seconds: float = Field(default=0.0, ge=0.0)


class FeedbackResponse(BaseModel):
    arm_id: str
    reward: float


__all__ = [
    "Action",
    "ChatRequest",
    "ChatResponse",
    "FeedbackRequest",
    "FeedbackResponse",
    "IngestEnvelope",
    "IngestResponse",
    "RecommendRequest",
    "RecommendResponse",
]
