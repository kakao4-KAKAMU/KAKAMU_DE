"""POST /ingest/person/judge"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from src.api.dependencies import AppContainer
from src.api.routers.deps import get_app_container
from src.api.routers.ingest.utils import enqueue
from src.api.schemas import IngestPersonJudgeEnvelope, IngestResponse

router = APIRouter()


@router.post(
    "/ingest/person/judge",
    response_model=IngestResponse,
    tags=["person"],
    summary="인물 선호 판정",
    description="사용자의 인물 like/dislike 판정을 ingest outbox에 적재합니다.",
)
def ingest_person_judge(
    env: IngestPersonJudgeEnvelope,
    container: AppContainer = Depends(get_app_container),
) -> IngestResponse:
    return enqueue(
        container,
        aggregate_type="person_judge",
        aggregate_id=f"{env.payload.person_id}_{env.payload.user_id}",
        env=env,
    )
