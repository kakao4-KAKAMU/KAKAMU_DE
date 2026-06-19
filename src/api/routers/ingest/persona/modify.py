"""POST /ingest/persona/modify"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from src.api.dependencies import AppContainer
from src.api.routers.deps import get_app_container
from src.api.routers.ingest.utils import enqueue
from src.api.schemas import IngestPersonaEnvelope, IngestResponse

router = APIRouter()


@router.post(
    "/ingest/persona/modify",
    response_model=IngestResponse,
    tags=["persona"],
    summary="페르소나 수정",
    description="수정된 페르소나 프로필을 ingest outbox에 적재합니다. 선호 관계는 payload 기준으로 동기화됩니다.",
)
def ingest_persona_modify(
    env: IngestPersonaEnvelope,
    container: AppContainer = Depends(get_app_container),
) -> IngestResponse:
    return enqueue(
        container,
        aggregate_type="persona_modify",
        aggregate_id=env.payload.persona_id,
        env=env,
    )
