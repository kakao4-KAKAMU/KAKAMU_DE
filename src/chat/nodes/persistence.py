"""persist_history 노드: 응답/온톨로지 참조를 세션 이력에 영속화."""

from __future__ import annotations

import logging
from typing import Any

from src.chat.nodes.dependencies import ChatGraphDependencies
from src.chat.state import ChatState, IntentScope

logger = logging.getLogger(__name__)


def _build_ontology_ref(state: ChatState) -> dict[str, Any]:
    scope: IntentScope = state.get("intent_scope") or state.get("media_type") or "movie"  # type: ignore[assignment]
    retrieved_movies = state.get("retrieved_movies") or []
    retrieved_feeds = state.get("retrieved_feeds") or []
    if not retrieved_movies and scope in ("movie", "both"):
        retrieved_movies = [
            r for r in (state.get("retrieved") or []) if r.get("movie_id")
        ]
    if not retrieved_feeds and scope in ("feed", "both"):
        retrieved_feeds = [
            r for r in (state.get("retrieved") or []) if r.get("feed_id")
        ]

    ontology_ref: dict[str, Any] = {
        "intent_scope": scope,
        "arm_id": state.get("arm_id"),
        "themes": state.get("themes") or [],
        "moods": state.get("moods") or [],
        "movie_filters": state.get("movie_filters") or {},
        "feed_filters": state.get("feed_filters") or {},
    }
    if retrieved_movies:
        ontology_ref["movie_ids"] = [
            str(r.get("movie_id")) for r in retrieved_movies if r.get("movie_id")
        ]
    if retrieved_feeds:
        ontology_ref["feed_ids"] = [
            str(r.get("feed_id")) for r in retrieved_feeds if r.get("feed_id")
        ]
    return ontology_ref


def persist_history(state: ChatState, deps: ChatGraphDependencies) -> ChatState:
    ontology_ref = _build_ontology_ref(state)

    if deps.history is not None and state.get("session_id"):
        try:
            deps.history.append(
                session_id=str(state["session_id"]),
                user_id=str(state.get("user_id", "anonymous")),
                role="assistant",
                content=str(state.get("reply") or ""),
                ontology_ref=ontology_ref,
                reply_metadata=state.get("reply_metadata"),
            )
        except Exception:
            logger.exception("Chat history persistence failed")
    return {"ontology_ref": ontology_ref}


__all__ = ["persist_history"]
