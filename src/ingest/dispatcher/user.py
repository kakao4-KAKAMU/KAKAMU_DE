"""User ingest 핸들러."""

from __future__ import annotations

from typing import Any, Mapping

from src.api.schemas.user import IngestUserPayload
from src.graph.loader import OntologyLoader
from src.ingest.dispatcher.utils import Handler


def build_user_handler(*, loader: OntologyLoader) -> Handler:
    def _handler(payload: Mapping[str, Any]) -> None:
        p = IngestUserPayload.model_validate(payload)
        loader.upsert_user(
            user_id=p.user_id,
            nickname=p.nickname,
            created_at=p.created_at,
        )

    return _handler


__all__ = ["build_user_handler"]
