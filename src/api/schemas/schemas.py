"""FastAPI 요청/응답 Pydantic 스키마.

SOLID
-----
- SRP : HTTP 표면 스키마만 정의. 도메인 객체로의 변환은 라우터에서.
"""

from __future__ import annotations

from typing import Any, Literal, Optional
from uuid import uuid4

from src.persistence.chat_history import ChatMessage
from src.api.schemas.movie import IngestMoviePayload, IngestMovieJudgePayload
from src.api.schemas.feed import (
    IngestFeedPayload,
    IngestFeedDeletePayload,
    IngestFeedLikePayload,
)
from src.api.schemas.comment import (
    IngestCommentPayload,
    IngestCommentLikePayload,
    IngestCommentDeletePayload,
)
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


# ---------------------------------------------------------------------------
# /chat/session
# ---------------------------------------------------------------------------

class ChatSessionResponse(BaseModel):
    next_cursor: Optional[int]
    has_more: bool
    messages: list[ChatMessage]


class ChatSessionRequest(BaseModel):
    cursor: Optional[int] = None
    limit: int = 20


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
    payload: dict[str, Any]


# ------- MOVIE -------
class IngestMovieEnvelope(IngestEnvelope):
    payload: IngestMoviePayload

class IngestMovieJudgeEnvelope(IngestEnvelope):
    payload: IngestMovieJudgePayload

# ------- FEED -------
class IngestFeedEnvelope(IngestEnvelope):
    payload: IngestFeedPayload

class IngestFeedDeleteEnvelope(IngestEnvelope):
    payload: IngestFeedDeletePayload

class IngestFeedLikeEnvelope(IngestEnvelope):
    payload: IngestFeedLikePayload


# ------- COMMENT -------
class IngestCommentEnvelope(IngestEnvelope):
    payload: IngestCommentPayload

class IngestCommentDeleteEnvelope(IngestEnvelope):
    payload: IngestCommentDeletePayload

class IngestCommentLikeEnvelope(IngestEnvelope):
    payload: IngestCommentLikePayload


# ------- RESPONSE -------
class IngestResponse(BaseModel):
    outbox_id: int


# ---------------------------------------------------------------------------
# /feedback
# ---------------------------------------------------------------------------


Action = Literal["click", "dwell", "like", "skip", "dislike"]
ContentType = Literal["feed", "comment", "movie"]

class FeedbackRequest(BaseModel):
    user_id: str = Field(min_length=1)
    arm_id: str = Field(min_length=1)
    action: Action
    content_type: ContentType
    dwell_seconds: float = Field(default=0.0, ge=0.0)


class FeedbackResponse(BaseModel):
    arm_id: str
    reward: float


__all__ = [
    "Action",
    "ChatRequest",
    "ChatResponse",
    "ChatSessionRequest",
    "ChatSessionResponse",
    "FeedbackRequest",
    "FeedbackResponse",
    "IngestEnvelope",
    "IngestMovieEnvelope",
    "IngestResponse",
    "RecommendRequest",
    "RecommendResponse",
]
