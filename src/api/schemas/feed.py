from pydantic import BaseModel, Field
from typing import Optional

class IngestFeedPayload(BaseModel):
    feed_id: str = Field(min_length=1)
    user_id: str = Field(min_length=1)
    persona_id: Optional[str] = Field(default=None)
    related_movie_id: str = Field(default=None)
    known_movie_ids: list[str] = Field(default=[])
    mentioned_user_ids: list[str] = Field(default=[])
    content: str = Field(min_length=1)
    created_at: str = Field(default=None)
    modified_at: str = Field(default=None)

class IngestFeedLikePayload(BaseModel):
    feed_id: str = Field(min_length=1)
    user_id: str = Field(min_length=1)
    persona_id: Optional[str] = Field(default=None)
    is_like: bool = Field(default=True)
    created_at: str = Field(default=None)

class IngestFeedDeletePayload(BaseModel):
    feed_id: str = Field(min_length=1)
    user_id: str = Field(min_length=1)
    deleted_at: str = Field(default=None)

__all__ = [
    "IngestFeedPayload",
    "IngestFeedLikePayload",
    "IngestFeedDeletePayload",
]
