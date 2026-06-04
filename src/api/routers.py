"""FastAPI routers (/chat, /recommend, /ingest, /feedback, /healthz).

SOLID
-----
- SRP : HTTP 핸들러는 입출력 스키마 변환과 도메인 호출만 담당.
- DIP : 모든 도메인 객체는 ``get_container`` 의존성으로 주입된다.
"""

from __future__ import annotations

import json
import logging
import asyncio
from typing import Any, Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Header
from sse_starlette.sse import EventSourceResponse

from src.api.dependencies import AppContainer, get_container
from src.api.schemas.schemas import (
    ChatRequest,
    ChatSessionResponse,
    FeedbackRequest,
    FeedbackResponse,
    IngestEnvelope,
    IngestMovieEnvelope,
    IngestMovieJudgeEnvelope,
    IngestFeedEnvelope,
    IngestFeedDeleteEnvelope,
    IngestFeedLikeEnvelope,
    IngestCommentEnvelope,
    IngestCommentLikeEnvelope,
    IngestCommentDeleteEnvelope,
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


def _initial_chat_state(req: ChatRequest, user_id: str, session_id: str) -> ChatState:
    return ChatState(
        user_id=user_id,
        session_id=session_id,
        query=req.message,
        top_k=req.top_k,
        max_toxicity=req.max_toxicity,
    )


@router.get("/chat/list", response_model=list[ChatSession])
def chat_list(
    x_persona_id: Annotated[str, Header(alias="X-Persona-Id")],
    cursor: int | None = Query(default=None, ge=1),
    limit: int = Query(default=20, ge=1, le=200),
    container: AppContainer = Depends(get_app_container),
) -> list[ChatSession]:
    return container.chat_history.list_sessions(
        user_id=x_persona_id,
        cursor=cursor,
        limit=limit,
    )


# 채팅 세션 히스토리 조회
@router.get("/chat/history/{session_id}", response_model=ChatSessionResponse)
def chat_session(
    x_persona_id: Annotated[str, Header(alias="X-Persona-Id")],
    session_id: str,
    cursor: int | None = Query(default=None, ge=1),
    limit: int = Query(default=20, ge=1, le=200),
    container: AppContainer = Depends(get_app_container),
) -> ChatSessionResponse:
    messages = container.chat_history.get_session_history(
        session_id=session_id,
        user_id=x_persona_id,
        cursor=cursor,
        limit=limit,
    )
    return ChatSessionResponse(
        next_cursor=messages[0].id if messages else None,
        has_more=len(messages) == limit,
        messages=list(reversed(messages)),
    )

@router.post("/chat/stream")
async def chat_stream(
    req: ChatRequest,
    x_persona_id: Annotated[str, Header(alias="X-Persona-Id")],
    container: AppContainer = Depends(get_app_container),
):
    """노드 단위 SSE 스트리밍 (디버깅/관측용)."""
    session_id = req.ensure_session_id()
    try:
        container.chat_history.open_session(session_id=session_id, user_id=x_persona_id)
        msg_id = container.chat_history.append(
            session_id=session_id,
            user_id=x_persona_id,
            role="user",
            content=req.message,
        )
    except Exception:
        logger.exception("Failed to persist user message; continuing")
    state = _initial_chat_state(req, x_persona_id, session_id)
    config = {"configurable": {"thread_id": session_id}}

    async def event_gen():
        yield {
            "event": "open",
            "data": json.dumps({"session_id": session_id, "message_id": msg_id}),
        }
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
        await asyncio.sleep(0.1)
        yield {"event": "done", "data": json.dumps({"session_id": session_id })}

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
            payload=env.payload,
        )
    except Exception as exc:
        logger.exception("Ingest enqueue failed")
        raise HTTPException(status_code=500, detail=f"enqueue failed: {exc}") from exc
    return IngestResponse(outbox_id=outbox_id)


@router.post("/ingest/movie/regist", response_model=IngestResponse)
def ingest_movie(
    env: IngestMovieEnvelope,
    container: AppContainer = Depends(get_app_container),
) -> IngestResponse:
    return _enqueue(container, aggregate_type="movie", env=env)


@router.post("/ingest/movie/judge", response_model=IngestResponse)
def ingest_movie_judge(
    env: IngestMovieJudgeEnvelope,
    container: AppContainer = Depends(get_app_container),
) -> IngestResponse:
    return _enqueue(container, aggregate_type="movie_judge", env=env)

@router.post("/ingest/feed/create", response_model=IngestResponse)
def ingest_feed(
    env: IngestFeedEnvelope,
    container: AppContainer = Depends(get_app_container),
) -> IngestResponse:
    return _enqueue(container, aggregate_type="feed", env=env)


@router.post("/ingest/feed/modify", response_model=IngestResponse)
def ingest_feed_modify(
    env: IngestFeedEnvelope,
    container: AppContainer = Depends(get_app_container),
) -> IngestResponse:
    return _enqueue(container, aggregate_type="feed_modify", env=env)


@router.post("/ingest/feed/delete", response_model=IngestResponse)
def ingest_feed_modify(
    env: IngestFeedDeleteEnvelope,
    container: AppContainer = Depends(get_app_container),
) -> IngestResponse:
    return _enqueue(container, aggregate_type="feed_delete", env=env)


@router.post("/ingest/feed/like", response_model=IngestResponse)
def ingest_feed_like(
    env: IngestFeedLikeEnvelope,
    container: AppContainer = Depends(get_app_container),
) -> IngestResponse:
    return _enqueue(container, aggregate_type="feed_like", env=env)


@router.post("/ingest/comment/create", response_model=IngestResponse)
def ingest_comment(
    env: IngestCommentEnvelope,
    container: AppContainer = Depends(get_app_container),
) -> IngestResponse:
    return _enqueue(container, aggregate_type="comment", env=env)

@router.post("/ingest/comment/modify", response_model=IngestResponse)
def ingest_comment_modify(
    env: IngestCommentEnvelope,
    container: AppContainer = Depends(get_app_container),
) -> IngestResponse:
    return _enqueue(container, aggregate_type="comment_modify", env=env)

@router.post("/ingest/comment/delete", response_model=IngestResponse)
def ingest_comment_delete(
    env: IngestCommentDeleteEnvelope,
    container: AppContainer = Depends(get_app_container),
) -> IngestResponse:
    return _enqueue(container, aggregate_type="comment_delete", env=env)

@router.post("/ingest/comment/like", response_model=IngestResponse)
def ingest_comment_like(
    env: IngestCommentLikeEnvelope,
    container: AppContainer = Depends(get_app_container),
) -> IngestResponse:
    return _enqueue(container, aggregate_type="comment_like", env=env)

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
