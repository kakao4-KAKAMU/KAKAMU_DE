"""POST /ingest/persona/create"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from src.api.dependencies import AppContainer
from src.api.routers.deps import get_app_container
from src.api.routers.ingest.utils import enqueue
from src.api.schemas import IngestPersonaEnvelope, IngestResponse

router = APIRouter()


@router.post(
    "/ingest/persona/create",
    response_model=IngestResponse,
    tags=["persona"],
    summary="페르소나 등록",
    description="페르소나 프로필과 선호 관계를 ingest outbox에 적재합니다.",
)
def ingest_persona_create(
    env: IngestPersonaEnvelope,
    container: AppContainer = Depends(get_app_container),
) -> IngestResponse:
    return enqueue(
        container,
        aggregate_type="persona",
        aggregate_id=env.payload.persona_id,
        env=env,
    )
