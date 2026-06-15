from __future__ import annotations
from typing import Optional, Any
from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# /recommend
# ---------------------------------------------------------------------------


class RecommendRequest(BaseModel):
    user_id: str = Field(min_length=1)
    persona_id: Optional[str] = Field(default=None)
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
# /recommend/feed
# ---------------------------------------------------------------------------


class FeedRecommendResponse(BaseModel):
    arm_id: str
    feeds: list[dict[str, Any]]
    keywords: list[str]
    themes: list[str]
    moods: list[str]
