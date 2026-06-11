from pydantic import BaseModel, Field
from typing import Optional

class IngestCommentPayload(BaseModel):
    comment_id: str = Field(min_length=1)
    feed_id: str = Field(min_length=1)
    user_id: str = Field(min_length=1)
    persona_id: Optional[str] = Field(default=None)
    mentioned_user_ids: list[str] = Field(default=[])
    parent_comment_id: str = Field(default=None)
    content: str = Field(min_length=1)
    created_at: str = Field(default=None)
    modified_at: str = Field(default=None)

class IngestCommentLikePayload(BaseModel):
    comment_id: str = Field(min_length=1)
    user_id: str = Field(min_length=1)
    persona_id: Optional[str] = Field(default=None)
    is_like: bool = Field(default=True)
    created_at: str = Field(default=None)

class IngestCommentDeletePayload(BaseModel):
    comment_id: str = Field(min_length=1)
    user_id: str = Field(min_length=1)
    deleted_at: str = Field(default=None)

__all__ = [
    "IngestCommentPayload",
    "IngestCommentLikePayload",
    "IngestCommentDeletePayload",
]
