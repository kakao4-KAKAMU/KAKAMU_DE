"""영화(Movie) ingest payload 스키마.

온톨로지 영화 추출(build_movie_plot_messages → MoviePlotOntology)의
입력 구조와 1:1 로 대응한다.
"""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field

from src.api.schemas.person import IngestPersonPayload
from src.api.schemas.shared import IngestPayload, JudgeType


class MovieTitlePayload(BaseModel):
    """국가/시장별 영화 제목."""

    title: str = Field(min_length=1, description="영화 제목.")
    country: str = Field(min_length=1, description="제목이 사용되는 국가 코드/명.")


class IngestMoviePayload(IngestPayload):
    """영화 등록/갱신. MoviePlotExtractor.extract() 의 입력 구조."""

    movie_id: str = Field(min_length=1, description="영화 고유 ID.")
    title: str = Field(min_length=1, description="영화 제목.")
    producing_year: int = Field(default=None, description="제작 연도.")
    country: str = Field(default=None, description="제작 국가 코드/명.")
    genres: List[str] = Field(default_factory=list, description="장르 목록.")
    plot: str = Field(default=None, description="원문 줄거리.")
    persons: List[IngestPersonPayload] = Field(
        default_factory=list, description="참여 인물 (감독/배우 등)."
    )
    reviews: List[str] = Field(
        default_factory=list,
        description="관객 리뷰 샘플. 온톨로지 추출 시 themes/moods 보강 컨텍스트로 사용.",
    )
    titles: List[MovieTitlePayload] = Field(
        default_factory=list,
        description="국가/시장별 제목 목록. 비어 있으면 title+country 로 MovieTitle 1건 생성.",
    )


class IngestMovieJudgePayload(IngestPayload):
    """영화에 대한 사용자 선호 판정."""

    movie_id: str = Field(min_length=1)
    user_id: str = Field(min_length=1)
    persona_id: Optional[str] = Field(default=None, description="Persona ID.")
    judge_type: JudgeType = Field(default="like", description="like/dislike.")
    created_at: Optional[datetime] = Field(default=None, description="판정 시각 (ISO 8601).")


__all__ = [
    "IngestMoviePayload",
    "IngestMovieJudgePayload",
    "MovieTitlePayload",
]
