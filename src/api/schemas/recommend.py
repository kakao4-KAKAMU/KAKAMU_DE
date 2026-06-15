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


class MovieRecommendResponse(BaseModel):
    arm_id: str = Field(description="ARM ID.")
    movies: list[dict[str, Any]] = Field(description="영화 목록.")
    keywords: list[str] = Field(description="키워드 목록.")
    themes: list[str] = Field(description="테마 목록.")
    moods: list[str] = Field(description="무드 목록.")


# ---------------------------------------------------------------------------
# /recommend/feed
# ---------------------------------------------------------------------------


class FeedRecommendResponse(BaseModel):
    arm_id: str = Field(description="ARM ID.")
    feeds: list[dict[str, Any]] = Field(description="피드 목록.")
    keywords: list[str] = Field(description="키워드 목록.")
    themes: list[str] = Field(description="테마 목록.")
    moods: list[str] = Field(description="무드 목록.")
