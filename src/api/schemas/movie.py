from pydantic import BaseModel, Field
from typing import Literal

class IngestMoviePayload(BaseModel):
    movie_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    producing_year: int = Field(default=None)
    country: str = Field(default=None)
    genres: list[str] = Field(default=[])
    plot: str = Field(default=None)


JudgeType = Literal["like", "dislike"]

class IngestMovieJudgePayload(BaseModel):
    movie_id: str = Field(min_length=1)
    user_id: str = Field(min_length=1)
    judge_type: JudgeType = Field(default="like")
    created_at: str = Field(default=None)

__all__ = [
    "IngestMoviePayload",
    "IngestMovieJudgePayload",
]