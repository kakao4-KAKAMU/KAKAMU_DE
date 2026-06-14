"""POST /ingest/feed/like"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from src.api.dependencies import AppContainer
from src.api.routers.deps import get_app_container
from src.api.routers.ingest.utils import enqueue
from src.api.schemas import IngestFeedLikeEnvelope, IngestResponse

router = APIRouter()


@router.post(
    "/ingest/feed/like",
    response_model=IngestResponse,
    tags=["feed"],
    summary="피드 좋아요",
    description="피드 좋아요/취소 이벤트를 ingest outbox에 적재합니다.",
)
def ingest_feed_like(
    env: IngestFeedLikeEnvelope,
    container: AppContainer = Depends(get_app_container),
) -> IngestResponse:
    return enqueue(
        container,
        aggregate_type="feed_like",
        aggregate_id=f"{env.payload.feed_id}_{env.payload.user_id}",
        env=env,
    )
