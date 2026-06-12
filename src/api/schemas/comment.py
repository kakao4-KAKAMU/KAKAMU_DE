"""댓글(Comment) ingest payload 스키마.

온톨로지 댓글 추출(build_comment_messages → CommentOntology)의 입력 구조와
1:1 로 대응한다. parent_feed_summary / parent_comment_summary 는 프롬프트의
맥락(context) 입력으로 그대로 전달된다.
"""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import Field

from src.api.schemas.shared import IngestPayload


class IngestCommentPayload(IngestPayload):
    """댓글 등록/수정. CommentExtractor.extract() 의 입력 구조."""

    comment_id: str = Field(min_length=1, description="댓글 고유 ID.")
    feed_id: str = Field(min_length=1, description="댓글이 달린 피드 ID.")
    user_id: str = Field(min_length=1, description="작성자 ID.")
    persona_id: Optional[str] = Field(default=None, description="작성 페르소나 ID.")
    mentioned_user_ids: List[str] = Field(
        default_factory=list,
        description="@언급된 사용자 ID. targets_user_id 는 이 목록 내에서만 선택된다.",
    )
    parent_comment_id: Optional[str] = Field(
        default=None, description="대댓글인 경우 부모 댓글 ID."
    )
    parent_feed_summary: Optional[str] = Field(
        default=None, description="부모 피드 요약. 온톨로지 추출 맥락으로 사용."
    )
    parent_comment_summary: Optional[str] = Field(
        default=None, description="부모 댓글 요약. 온톨로지 추출 맥락으로 사용."
    )
    content: str = Field(min_length=1, description="댓글 원문.")
    created_at: Optional[datetime] = Field(default=None, description="작성 시각 (ISO 8601).")
    modified_at: Optional[datetime] = Field(default=None, description="수정 시각 (ISO 8601).")


class IngestCommentLikePayload(IngestPayload):
    """댓글 좋아요/취소."""

    comment_id: str = Field(min_length=1)
    user_id: str = Field(min_length=1)
    persona_id: Optional[str] = Field(default=None)
    is_like: bool = Field(default=True, description="True=좋아요, False=취소.")
    created_at: Optional[datetime] = Field(default=None, description="반응 시각 (ISO 8601).")


class IngestCommentDeletePayload(IngestPayload):
    """댓글 삭제."""

    comment_id: str = Field(min_length=1)
    user_id: str = Field(min_length=1)
    deleted_at: Optional[datetime] = Field(default=None, description="삭제 시각 (ISO 8601).")


__all__ = [
    "IngestCommentPayload",
    "IngestCommentLikePayload",
    "IngestCommentDeletePayload",
]
