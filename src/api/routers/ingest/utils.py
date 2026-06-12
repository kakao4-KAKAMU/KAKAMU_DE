"""ingest 라우터 공용 유틸."""

from __future__ import annotations

import logging

from fastapi import HTTPException

from src.api.dependencies import AppContainer
from src.api.schemas import IngestEnvelope, IngestResponse

logger = logging.getLogger(__name__)


def enqueue(
    container: AppContainer,*, aggregate_type: str, aggregate_id: str, env: IngestEnvelope
) -> IngestResponse:
    try:
        outbox_id = container.outbox.enqueue(
            aggregate_type=aggregate_type,
            aggregate_id=aggregate_id,
            payload=env.payload,
        )
    except Exception as exc:
        logger.exception("Ingest enqueue failed")
        raise HTTPException(status_code=500, detail=f"enqueue failed: {exc}") from exc
    return IngestResponse(outbox_id=outbox_id)
