"""POST /ingest/feed/modify"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from src.api.dependencies import AppContainer
from src.api.routers.deps import get_app_container
from src.api.routers.ingest.utils import enqueue
from src.api.schemas import IngestFeedEnvelope, IngestResponse

router = APIRouter()


@router.post(
    "/ingest/feed/modify",
    response_model=IngestResponse,
    tags=["ingest", "feed"],
    summary="피드 수정",
    description="수정된 피드 내용을 ingest outbox에 적재합니다. 워커가 온톨로지를 재추출해 그래프를 갱신합니다.",
)
def ingest_feed_modify(
    env: IngestFeedEnvelope,
    container: AppContainer = Depends(get_app_container),
) -> IngestResponse:
    return enqueue(
        container,
        aggregate_type="feed_modify",
        aggregate_id=env.payload.feed_id,
        env=env,
    )
