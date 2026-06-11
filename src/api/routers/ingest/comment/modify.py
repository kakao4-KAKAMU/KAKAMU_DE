"""POST /ingest/comment/modify"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from src.api.dependencies import AppContainer
from src.api.routers.deps import get_app_container
from src.api.routers.ingest.utils import enqueue
from src.api.schemas.schemas import IngestCommentEnvelope, IngestResponse

router = APIRouter()


@router.post("/ingest/comment/modify", response_model=IngestResponse)
def ingest_comment_modify(
    env: IngestCommentEnvelope,
    container: AppContainer = Depends(get_app_container),
) -> IngestResponse:
    return enqueue(container, aggregate_type="comment_modify", env=env)
