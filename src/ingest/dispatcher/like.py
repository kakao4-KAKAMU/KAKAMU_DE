"""Feed / Comment 좋아요 핸들러.

LLM 추출·임베딩 불필요. Loader 의 INTERACTED 관계만 적재한다.
"""

from __future__ import annotations

from typing import Any, Mapping

from src.api.schemas.comment import IngestCommentLikePayload
from src.api.schemas.feed import IngestFeedLikePayload
from src.graph.loader import OntologyLoader
from src.ingest.dispatcher.utils import Handler


def build_feed_like_handler(*, loader: OntologyLoader) -> Handler:
    def _handler(payload: Mapping[str, Any]) -> None:
        p = IngestFeedLikePayload.model_validate(payload)
        loader.like_feed(
            feed_id=p.feed_id,
            user_id=p.user_id,
            persona_id=p.persona_id,
            is_like=p.is_like,
            ts=p.created_at,
        )

    return _handler


def build_comment_like_handler(*, loader: OntologyLoader) -> Handler:
    def _handler(payload: Mapping[str, Any]) -> None:
        p = IngestCommentLikePayload.model_validate(payload)
        loader.like_comment(
            comment_id=p.comment_id,
            user_id=p.user_id,
            persona_id=p.persona_id,
            is_like=p.is_like,
            ts=p.created_at,
        )

    return _handler


__all__ = ["build_feed_like_handler", "build_comment_like_handler"]
