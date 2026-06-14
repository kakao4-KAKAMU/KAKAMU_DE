"""POST /ingest/comment/like"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from src.api.dependencies import AppContainer
from src.api.routers.deps import get_app_container
from src.api.routers.ingest.utils import enqueue
from src.api.schemas import IngestCommentLikeEnvelope, IngestResponse

router = APIRouter()


@router.post(
    "/ingest/comment/like",
    response_model=IngestResponse,
    tags=["ingest", "comment"],
    summary="댓글 좋아요",
    description="댓글 좋아요/취소 이벤트를 ingest outbox에 적재합니다.",
)
def ingest_comment_like(
    env: IngestCommentLikeEnvelope,
    container: AppContainer = Depends(get_app_container),
) -> IngestResponse:
    return enqueue(container, aggregate_type="comment_like", env=env)
