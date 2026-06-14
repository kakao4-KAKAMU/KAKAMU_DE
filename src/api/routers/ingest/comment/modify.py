"""POST /ingest/comment/modify"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from src.api.dependencies import AppContainer
from src.api.routers.deps import get_app_container
from src.api.routers.ingest.utils import enqueue
from src.api.schemas import IngestCommentEnvelope, IngestResponse

router = APIRouter()


@router.post(
    "/ingest/comment/modify",
    response_model=IngestResponse,
    tags=["comment"],
    summary="댓글 수정",
    description="수정된 댓글 내용을 ingest outbox에 적재합니다. 워커가 온톨로지를 재추출해 그래프를 갱신합니다.",
)
def ingest_comment_modify(
    env: IngestCommentEnvelope,
    container: AppContainer = Depends(get_app_container),
) -> IngestResponse:
    return enqueue(container, aggregate_type="comment_modify", env=env)
