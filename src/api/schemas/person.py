from pydantic import BaseModel, Field
from src.api.schemas.shared import JudgeType


class IngestPersonPayload(BaseModel):
    person_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    job: str = Field(min_length=1)

class IngestPersonJudgePayload(BaseModel):
    person_id: str = Field(min_length=1)
    user_id: str = Field(min_length=1)
    judge_type: JudgeType = Field(default="like")
    created_at: str = Field(default=None)

__all__ = ["IngestPersonPayload", "IngestPersonJudgePayload"]
