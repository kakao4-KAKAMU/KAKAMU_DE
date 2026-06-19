"""POST /ingest/persona/delete"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from src.api.dependencies import AppContainer
from src.api.routers.deps import get_app_container
from src.api.routers.ingest.utils import enqueue
from src.api.schemas import IngestPersonaDeleteEnvelope, IngestResponse

router = APIRouter()


@router.post(
    "/ingest/persona/delete",
    response_model=IngestResponse,
    tags=["persona"],
    summary="페르소나 삭제",
    description="페르소나 삭제 이벤트를 ingest outbox에 적재합니다.",
)
def ingest_persona_delete(
    env: IngestPersonaDeleteEnvelope,
    container: AppContainer = Depends(get_app_container),
) -> IngestResponse:
    return enqueue(
        container,
        aggregate_type="persona_delete",
        aggregate_id=env.payload.persona_id,
        env=env,
    )
