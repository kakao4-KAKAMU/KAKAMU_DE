"""FastAPI routers (/chat, /recommend, /ingest, /feedback, /healthz).

SOLID
-----
- SRP : HTTP 핸들러는 입출력 스키마 변환과 도메인 호출만 담당.
- DIP : 모든 도메인 객체는 ``get_container`` 의존성으로 주입된다.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sse_starlette.sse import EventSourceResponse

from src.api.dependencies import AppContainer, get_container
from src.api.schemas import (
    ChatRequest,
    ChatResponse,
    FeedbackRequest,
    FeedbackResponse,
    IngestEnvelope,
    IngestResponse,
    RecommendRequest,
    RecommendResponse,
)
from src.chat.state import ChatState
from src.persistence.chat_history import ChatSession

logger = logging.getLogger(__name__)


def get_app_container() -> AppContainer:
    return get_container()


router = APIRouter()


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------


@router.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# /chat
# ---------------------------------------------------------------------------


def _initial_chat_state(req: ChatRequest, session_id: str) -> ChatState:
    return ChatState(
        user_id=req.user_id,
        session_id=session_id,
        query=req.message,
        top_k=req.top_k,
        max_toxicity=req.max_toxicity,
    )


@router.get("/chat/list")
def chat_list(
    container: AppContainer = Depends(get_app_container),
) -> list[ChatSession]:
    return container.chat_history.list_sessions()

@router.post("/chat", response_model=ChatResponse)
def chat(
    req: ChatRequest,
    container: AppContainer = Depends(get_app_container),
) -> ChatResponse:
    session_id = req.ensure_session_id()
    try:
        container.chat_history.open_session(
            session_id=session_id, user_id=req.user_id
        )
        container.chat_history.append(
            session_id=session_id,
            user_id=req.user_id,
            role="user",
            content=req.message,
        )
    except Exception:
        logger.exception("Failed to persist user message; continuing")

    state = _initial_chat_state(req, session_id)
    config = {"configurable": {"thread_id": session_id}}
    final: dict[str, Any] = container.chat_graph.invoke(state, config=config)

    return ChatResponse(
        session_id=session_id,
        reply=str(final.get("reply") or ""),
        arm_id=str(final.get("arm_id") or ""),
        movies=list(final.get("retrieved") or []),
        ontology_ref=dict(final.get("ontology_ref") or {}),
    )


@router.post("/chat/stream")
async def chat_stream(
    req: ChatRequest,
    container: AppContainer = Depends(get_app_container),
):
    """노드 단위 SSE 스트리밍 (디버깅/관측용)."""
    session_id = req.ensure_session_id()
    state = _initial_chat_state(req, session_id)
    config = {"configurable": {"thread_id": session_id}}

    async def event_gen():
        try:
            async for chunk in container.chat_graph.astream(state, config=config):
                yield {
                    "event": "node",
                    "data": json.dumps(_jsonify(chunk), ensure_ascii=False),
                }
        except Exception as exc:
            logger.exception("chat stream failed")
            yield {
                "event": "error",
                "data": json.dumps({"detail": str(exc)}),
            }
        yield {"event": "done", "data": json.dumps({"session_id": session_id})}

    return EventSourceResponse(event_gen())


def _jsonify(value: Any) -> Any:
    """SSE 직렬화: dict/list 만 통과, 그 외 객체는 repr."""
    if isinstance(value, dict):
        return {k: _jsonify(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_jsonify(v) for v in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return repr(value)


# ---------------------------------------------------------------------------
# /recommend
# ---------------------------------------------------------------------------


@router.post("/recommend", response_model=RecommendResponse)
def recommend(
    req: RecommendRequest,
    container: AppContainer = Depends(get_app_container),
) -> RecommendResponse:
    intent = container.intent_resolver.resolve(req.query)
    embedding = container.embedder.embed(req.query)
    arm = container.policy.select_arm(context_key=req.user_id)
    params = {
        "user_id": req.user_id,
        "query_embedding": list(embedding),
        "query_keywords": list(intent.keywords),
        "query_themes": list(intent.themes),
        "query_moods": list(intent.moods),
        "top_k": req.top_k,
        "vec_top_k": req.vec_top_k,
        "max_toxicity": req.max_toxicity,
        **dict(arm.weights),
    }
    movies = container.template_executor.execute("hybrid_recommend", params)
    return RecommendResponse(
        arm_id=arm.arm_id,
        movies=list(movies),
        keywords=list(intent.keywords),
        themes=list(intent.themes),
        moods=list(intent.moods),
    )


# ---------------------------------------------------------------------------
# /ingest
# ---------------------------------------------------------------------------


def _enqueue(
    container: AppContainer, *, aggregate_type: str, env: IngestEnvelope
) -> IngestResponse:
    try:
        outbox_id = container.outbox.enqueue(
            aggregate_type=aggregate_type,
            aggregate_id=env.aggregate_id,
            payload=env.payload,
        )
    except Exception as exc:
        logger.exception("Ingest enqueue failed")
        raise HTTPException(status_code=500, detail=f"enqueue failed: {exc}") from exc
    return IngestResponse(outbox_id=outbox_id)


@router.post("/ingest/movie", response_model=IngestResponse)
def ingest_movie(
    env: IngestEnvelope,
    container: AppContainer = Depends(get_app_container),
) -> IngestResponse:
    return _enqueue(container, aggregate_type="movie", env=env)


@router.post("/ingest/feed", response_model=IngestResponse)
def ingest_feed(
    env: IngestEnvelope,
    container: AppContainer = Depends(get_app_container),
) -> IngestResponse:
    return _enqueue(container, aggregate_type="feed", env=env)


@router.post("/ingest/comment", response_model=IngestResponse)
def ingest_comment(
    env: IngestEnvelope,
    container: AppContainer = Depends(get_app_container),
) -> IngestResponse:
    return _enqueue(container, aggregate_type="comment", env=env)


# ---------------------------------------------------------------------------
# /feedback
# ---------------------------------------------------------------------------


@router.post("/feedback", response_model=FeedbackResponse)
def feedback(
    req: FeedbackRequest,
    container: AppContainer = Depends(get_app_container),
) -> FeedbackResponse:
    result = container.feedback_recorder.record(
        arm_id=req.arm_id,
        context_key=req.user_id,
        action=req.action,
        dwell_seconds=req.dwell_seconds,
    )
    return FeedbackResponse(arm_id=result.arm_id, reward=result.reward)


__all__ = ["get_app_container", "router"]
