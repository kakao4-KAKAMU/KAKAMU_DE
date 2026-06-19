"""POST /ingest/user/regist"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from src.api.dependencies import AppContainer
from src.api.routers.deps import get_app_container
from src.api.routers.ingest.utils import enqueue
from src.api.schemas import IngestResponse, IngestUserEnvelope

router = APIRouter()


@router.post(
    "/ingest/user/regist",
    response_model=IngestResponse,
    tags=["user"],
    summary="사용자 등록",
    description="사용자 계정을 ingest outbox에 적재합니다. 워커가 지식 그래프에 User 노드를 반영합니다.",
)
def ingest_user(
    env: IngestUserEnvelope,
    container: AppContainer = Depends(get_app_container),
) -> IngestResponse:
    return enqueue(
        container,
        aggregate_type="user",
        aggregate_id=env.payload.user_id,
        env=env,
    )
