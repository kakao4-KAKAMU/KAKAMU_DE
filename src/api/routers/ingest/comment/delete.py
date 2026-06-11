"""POST /ingest/comment/delete"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from src.api.dependencies import AppContainer
from src.api.routers.deps import get_app_container
from src.api.routers.ingest.utils import enqueue
from src.api.schemas.schemas import IngestCommentDeleteEnvelope, IngestResponse

router = APIRouter()


@router.post("/ingest/comment/delete", response_model=IngestResponse)
def ingest_comment_delete(
    env: IngestCommentDeleteEnvelope,
    container: AppContainer = Depends(get_app_container),
) -> IngestResponse:
    return enqueue(container, aggregate_type="comment_delete", env=env)
