"""POST /ingest/feed/delete"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from src.api.dependencies import AppContainer
from src.api.routers.deps import get_app_container
from src.api.routers.ingest.utils import enqueue
from src.api.schemas import IngestFeedDeleteEnvelope, IngestResponse

router = APIRouter()


@router.post("/ingest/feed/delete", response_model=IngestResponse)
def ingest_feed_delete(
    env: IngestFeedDeleteEnvelope,
    container: AppContainer = Depends(get_app_container),
) -> IngestResponse:
    return enqueue(
        container,
        aggregate_type="feed_delete",
        aggregate_id=env.payload.feed_id,
        env=env,
    )
