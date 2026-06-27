from __future__ import annotations
from typing import Optional, Any
from pydantic import BaseModel, Field
from src.api.security.limits import DEFAULT_MAX_RECOMMEND_QUERY_LENGTH

# ---------------------------------------------------------------------------
# /recommend/movie
# ---------------------------------------------------------------------------


class RecommendRequest(BaseModel):
    user_id: str = Field(min_length=1)
    persona_id: Optional[str] = Field(default=None)
    query: str = Field(min_length=1, max_length=DEFAULT_MAX_RECOMMEND_QUERY_LENGTH)
    top_k: int = Field(default=10, ge=1, le=50)
    vec_top_k: int = Field(default=30, ge=1, le=100)
    max_toxicity: float = Field(default=0.7, ge=0.0, le=1.0)

class MovieRecommendItem(BaseModel):
    movie_id: str = Field(description="영화 ID.")
    title: str = Field(description="영화 제목.")
    plot_summary: str = Field(description="영화 줄거리.")
    score: float = Field(description="영화 추천 점수.")

class MovieRecommendResponse(BaseModel):
    arm_id: str = Field(description="ARM ID.")
    movies: list[MovieRecommendItem] = Field(description="영화 목록.")
    keywords: list[str] = Field(description="키워드 목록.")
    themes: list[str] = Field(description="테마 목록.")
    moods: list[str] = Field(description="무드 목록.")

# ---------------------------------------------------------------------------
# /recommend/feed
# ---------------------------------------------------------------------------

class FeedRecommendItem(BaseModel):
    feed_id: str = Field(description="피드 ID.")
    summary: str = Field(description="피드 요약.")
    sentiment_score: float = Field(description="피드 감정 점수.")
    score: float = Field(description="피드 추천 점수.")

class FeedRecommendResponse(BaseModel):
    arm_id: str = Field(description="ARM ID.")
    feeds: list[FeedRecommendItem] = Field(description="피드 목록.")
    keywords: list[str] = Field(description="키워드 목록.")
    themes: list[str] = Field(description="테마 목록.")
    moods: list[str] = Field(description="무드 목록.")
