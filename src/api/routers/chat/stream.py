"""POST /chat/stream"""

from __future__ import annotations

import asyncio
import json
import logging

from fastapi import APIRouter, Depends
from fastapi.sse import EventSourceResponse, ServerSentEvent
from fastapi import HTTPException
from src.api.dependencies import AppContainer
from src.api.routers.chat.utils import initial_chat_state, jsonify
from src.api.routers.deps import get_app_container
from src.api.schemas import ChatRequest

from collections.abc import AsyncIterable


logger = logging.getLogger(__name__)

router = APIRouter()

@router.post(
    "/chat/stream",
    responses={
        404: {"description": "Session not found"},
    },
    tags=["chat"],
    summary="노드 단위 SSE 스트리밍",
    description="노드 단위 SSE 스트리밍을 시작합니다.",
    response_class=EventSourceResponse,
)
async def chat_stream(
    req: ChatRequest,
    container: AppContainer = Depends(get_app_container),
) -> AsyncIterable[ServerSentEvent]:
    """노드 단위 SSE 스트리밍 (디버깅/관측용)."""
    session_id = req.ensure_session_id()
    msg_id = None
    try:
        container.chat_history.open_session(
            session_id=session_id, user_id=req.user_id, persona_id=req.persona_id
        )
        msg_id = container.chat_history.append(
            session_id=session_id,
            user_id=req.user_id,
            role="user",
            content=req.message,
        )
    except Exception:
        logger.exception("Failed to persist user message; continuing")

    session = container.chat_history.get_session_by_id(session_id=session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    state = initial_chat_state(req, req.user_id, session_id, session.persona_id)
    config = {"configurable": {"thread_id": session_id}}

    async def event_gen():
        yield {"event": "open", "data": json.dumps({"session_id": session_id, "message_id": msg_id})}
        try:
            async for chunk in container.chat_graph.astream(state, config=config):
                yield {"event": "node", "data": json.dumps(jsonify(chunk))}
        except Exception as exc:
            logger.exception("chat stream failed")
            yield {"event": "error", "data":  json.dumps({"detail": str(exc)})}
        await asyncio.sleep(0.1)
        yield {"event": "done", "data": json.dumps({"session_id": session_id})}

    return EventSourceResponse(event_gen())
