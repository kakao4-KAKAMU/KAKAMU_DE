from __future__ import annotations
from typing import Optional, Literal
from pydantic import BaseModel, Field

Action = Literal["click", "dwell", "like", "skip", "dislike"]
ContentType = Literal["feed", "comment", "movie"]


class FeedbackRequest(BaseModel):
    user_id: str = Field(min_length=1)
    persona_id: Optional[str] = Field(default=None)
    arm_id: str = Field(min_length=1)
    action: Action
    content_type: ContentType
    dwell_seconds: float = Field(default=0.0, ge=0.0)


class FeedbackResponse(BaseModel):
    arm_id: str
    reward: float
