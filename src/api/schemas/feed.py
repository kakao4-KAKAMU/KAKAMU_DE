"""피드(Feed) ingest payload 스키마.

온톨로지 피드 추출(build_feed_messages → FeedOntology)의 입력 구조와
1:1 로 대응한다.
"""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import Field

from src.api.schemas.shared import IngestPayload
from src.api.security.limits import DEFAULT_MAX_INGEST_CONTENT_LENGTH


class IngestFeedPayload(IngestPayload):
    """피드 등록/수정. FeedExtractor.extract() 의 입력 구조."""

    feed_id: str = Field(min_length=1, description="피드 고유 ID.")
    user_id: str = Field(min_length=1, description="작성자 ID.")
    persona_id: Optional[str] = Field(default=None, description="작성 페르소나 ID.")
    related_movie_id: Optional[str] = Field(
        default=None, description="피드가 직접 연결된 영화 ID."
    )
    known_movie_ids: List[str] = Field(
        default_factory=list,
        description="referenced_movie_ids 후보. 온톨로지는 이 목록 내에서만 참조 영화를 고른다.",
    )
    mentioned_user_ids: List[str] = Field(
        default_factory=list, description="본문에서 @언급된 사용자 ID."
    )
    content: str = Field(
        min_length=1,
        max_length=DEFAULT_MAX_INGEST_CONTENT_LENGTH,
        description="피드 원문 본문.",
    )
    created_at: Optional[datetime] = Field(default=None, description="작성 시각 (ISO 8601).")
    modified_at: Optional[datetime] = Field(default=None, description="수정 시각 (ISO 8601).")


class IngestFeedLikePayload(IngestPayload):
    """피드 좋아요/취소."""

    feed_id: str = Field(min_length=1)
    user_id: str = Field(min_length=1)
    persona_id: Optional[str] = Field(default=None)
    is_like: bool = Field(default=True, description="True=좋아요, False=취소.")
    created_at: Optional[datetime] = Field(default=None, description="반응 시각 (ISO 8601).")


class IngestFeedDeletePayload(IngestPayload):
    """피드 삭제."""

    feed_id: str = Field(min_length=1)
    user_id: str = Field(min_length=1)
    deleted_at: Optional[datetime] = Field(default=None, description="삭제 시각 (ISO 8601).")


__all__ = [
    "IngestFeedPayload",
    "IngestFeedLikePayload",
    "IngestFeedDeletePayload",
]
