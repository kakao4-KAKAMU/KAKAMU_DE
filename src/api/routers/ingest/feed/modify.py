"""POST /ingest/feed/modify"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from src.api.dependencies import AppContainer
from src.api.routers.deps import get_app_container
from src.api.routers.ingest.utils import enqueue
from src.api.schemas import IngestFeedEnvelope, IngestResponse

router = APIRouter()


@router.post("/ingest/feed/modify", response_model=IngestResponse)
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
