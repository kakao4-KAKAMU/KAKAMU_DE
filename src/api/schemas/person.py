"""인물(Person) ingest payload 스키마.

온톨로지 영화 추출(build_movie_plot_messages)의 persons 입력 구조와 동일하다.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import Field

from src.api.schemas.shared import IngestPayload, JudgeType


class IngestPersonPayload(IngestPayload):
    """영화 참여 인물. Neo4j Person 노드/HAS_PERSON 관계의 원천."""

    person_id: str = Field(min_length=1, description="인물 고유 ID.")
    name: str = Field(min_length=1, description="인물 이름.")
    job: str = Field(min_length=1, description="직무 (director/actor 등).")


class IngestPersonJudgePayload(IngestPayload):
    """인물에 대한 사용자 선호 판정."""

    person_id: str = Field(min_length=1)
    user_id: str = Field(min_length=1)
    judge_type: JudgeType = Field(default="like", description="like/dislike.")
    created_at: Optional[datetime] = Field(default=None, description="판정 시각 (ISO 8601).")


__all__ = [
    "IngestPersonPayload",
    "IngestPersonJudgePayload",
]
