"""Feed / Comment 삭제(soft-delete) 핸들러.

LLM 추출·임베딩 불필요. Loader 의 soft-delete SET 만 수행한다.
"""

from __future__ import annotations

from typing import Any, Mapping

from src.api.schemas.comment import IngestCommentDeletePayload
from src.api.schemas.feed import IngestFeedDeletePayload
from src.graph.loader import OntologyLoader
from src.ingest.dispatcher.utils import Handler


def build_feed_delete_handler(*, loader: OntologyLoader) -> Handler:
    def _handler(payload: Mapping[str, Any]) -> None:
        p = IngestFeedDeletePayload.model_validate(payload)
        loader.delete_feed(
            feed_id=p.feed_id,
            deleted_at=p.deleted_at,
        )

    return _handler


def build_comment_delete_handler(*, loader: OntologyLoader) -> Handler:
    def _handler(payload: Mapping[str, Any]) -> None:
        p = IngestCommentDeletePayload.model_validate(payload)
        loader.delete_comment(
            comment_id=p.comment_id,
            deleted_at=p.deleted_at,
        )

    return _handler


__all__ = ["build_feed_delete_handler", "build_comment_delete_handler"]
