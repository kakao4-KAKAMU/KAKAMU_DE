"""Persona ingest 핸들러."""

from __future__ import annotations

from typing import Any, Mapping

from src.api.schemas.persona import IngestPersonaDeletePayload, IngestPersonaPayload
from src.graph.loader import OntologyLoader
from src.ingest.dispatcher.utils import Handler


def build_persona_handler(*, loader: OntologyLoader) -> Handler:
    def _handler(payload: Mapping[str, Any]) -> None:
        p = IngestPersonaPayload.model_validate(payload)
        loader.upsert_persona(
            persona_id=p.persona_id,
            user_id=p.user_id,
            label=p.label,
            genres=p.genres,
            movies=p.movies,
            persons=p.persons,
            created_at=p.created_at,
            modified_at=p.modified_at,
        )

    return _handler


def build_persona_delete_handler(*, loader: OntologyLoader) -> Handler:
    def _handler(payload: Mapping[str, Any]) -> None:
        p = IngestPersonaDeletePayload.model_validate(payload)
        loader.delete_persona(persona_id=p.persona_id)

    return _handler


__all__ = ["build_persona_handler", "build_persona_delete_handler"]
