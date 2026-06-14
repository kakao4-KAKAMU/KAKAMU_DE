"""POST /ingest/comment/create"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from src.api.dependencies import AppContainer
from src.api.routers.deps import get_app_container
from src.api.routers.ingest.utils import enqueue
from src.api.schemas import IngestCommentEnvelope, IngestResponse

router = APIRouter()


@router.post(
    "/ingest/comment/create",
    response_model=IngestResponse,
    tags=["ingest", "comment"],
    summary="댓글 등록",
    description="댓글 본문을 ingest outbox에 적재합니다. 워커가 부모 피드/댓글 맥락을 조회한 뒤 온톨로지 추출 및 그래프 반영을 수행합니다.",
)
def ingest_comment(
    env: IngestCommentEnvelope,
    container: AppContainer = Depends(get_app_container),
) -> IngestResponse:
    return enqueue(container, aggregate_type="comment", env=env)
