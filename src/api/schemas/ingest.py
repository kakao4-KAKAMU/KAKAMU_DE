"""FastAPI 요청/응답 Pydantic 스키마.

SOLID
-----
- SRP : HTTP 표면 스키마만 정의. 도메인 객체로의 변환은 라우터에서.
"""

from __future__ import annotations

from typing import Any

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
from pydantic import BaseModel

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



__all__ = [
    "IngestEnvelope",
    "IngestMovieEnvelope",
    "IngestMovieJudgeEnvelope",
    "IngestFeedEnvelope",
    "IngestFeedDeleteEnvelope",
    "IngestFeedLikeEnvelope",
    "IngestCommentEnvelope",
    "IngestCommentDeleteEnvelope",
    "IngestCommentLikeEnvelope",
    "IngestResponse",
]
