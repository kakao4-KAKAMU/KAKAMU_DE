from pydantic import BaseModel, Field
from src.api.schemas.shared import JudgeType

from src.api.schemas.person import IngestPersonPayload
class IngestMoviePayload(BaseModel):
    movie_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    producing_year: int = Field(default=None)
    country: str = Field(default=None)
    genres: list[str] = Field(default=[])
    plot: str = Field(default=None)
    persons: list[IngestPersonPayload] = Field(default=[])
    reviews: list[str] = Field(
        default=[],
        description="관객 리뷰 샘플. 온톨로지 추출 시 themes/moods 보강 컨텍스트로 사용.",
    )



class IngestMovieJudgePayload(BaseModel):
    movie_id: str = Field(min_length=1)
    user_id: str = Field(min_length=1)
    judge_type: JudgeType = Field(default="like")
    created_at: str = Field(default=None)

__all__ = [
    "IngestMoviePayload",
    "IngestMovieJudgePayload",
]