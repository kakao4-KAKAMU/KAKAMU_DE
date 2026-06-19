"""FastAPI 요청/응답 Pydantic 스키마.

SOLID
-----
- SRP : HTTP 표면 스키마만 정의. 도메인 객체로의 변환은 라우터에서.
"""

from __future__ import annotations

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
from src.api.schemas.person import IngestPersonJudgePayload
from src.api.schemas.user import IngestUserPayload
from src.api.schemas.persona import IngestPersonaPayload, IngestPersonaDeletePayload
from src.api.schemas.shared import IngestPayload
from pydantic import BaseModel

# ---------------------------------------------------------------------------
# /ingest
# ---------------------------------------------------------------------------


class IngestEnvelope(BaseModel):
    payload: IngestPayload


# ------- MOVIE -------
class IngestMovieEnvelope(IngestEnvelope):
    payload: IngestMoviePayload

class IngestMovieJudgeEnvelope(IngestEnvelope):
    payload: IngestMovieJudgePayload

class IngestPersonJudgeEnvelope(IngestEnvelope):
    payload: IngestPersonJudgePayload

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


# ------- USER -------
class IngestUserEnvelope(IngestEnvelope):
    payload: IngestUserPayload


# ------- PERSONA -------
class IngestPersonaEnvelope(IngestEnvelope):
    payload: IngestPersonaPayload


class IngestPersonaDeleteEnvelope(IngestEnvelope):
    payload: IngestPersonaDeletePayload


# ------- RESPONSE -------
class IngestResponse(BaseModel):
    outbox_id: int


__all__ = [
    "IngestEnvelope",
    "IngestMovieEnvelope",
    "IngestMovieJudgeEnvelope",
    "IngestPersonJudgeEnvelope",
    "IngestFeedEnvelope",
    "IngestFeedDeleteEnvelope",
    "IngestFeedLikeEnvelope",
    "IngestCommentEnvelope",
    "IngestCommentDeleteEnvelope",
    "IngestCommentLikeEnvelope",
    "IngestUserEnvelope",
    "IngestPersonaEnvelope",
    "IngestPersonaDeleteEnvelope",
    "IngestResponse",
]
