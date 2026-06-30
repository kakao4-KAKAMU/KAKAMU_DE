from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field

from src.config.limits import DEFAULT_MAX_RECOMMEND_QUERY_LENGTH


class MovieTitleSearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=DEFAULT_MAX_RECOMMEND_QUERY_LENGTH)
    country: Optional[str] = Field(
        default=None,
        description="제목 국가/시장 필터. 미지정 시 전체 검색.",
    )
    top_k: int = Field(default=10, ge=1, le=50)


class MovieTitleSearchItem(BaseModel):
    movie_id: str = Field(description="영화 ID.")
    title: str = Field(description="Movie canonical 제목.")
    matched_title: str = Field(description="매칭된 MovieTitle 제목.")
    title_country: str = Field(description="매칭된 MovieTitle 국가/시장.")
    score: float = Field(description="fulltext 검색 점수.")


class MovieTitleSearchResponse(BaseModel):
    movies: list[MovieTitleSearchItem] = Field(description="검색 결과 영화 목록.")


__all__ = [
    "MovieTitleSearchItem",
    "MovieTitleSearchRequest",
    "MovieTitleSearchResponse",
]
