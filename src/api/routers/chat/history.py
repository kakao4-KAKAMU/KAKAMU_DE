"""GET /chat/history/{session_id}"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from src.api.dependencies import AppContainer
from src.api.routers.deps import get_app_container
from src.api.schemas import ChatSessionResponse

router = APIRouter()


@router.get(
    "/chat/history/{session_id}",
    response_model=ChatSessionResponse,
    tags=["chat"],
    summary="세션 메시지 이력",
    description="세션 메시지 이력을 조회합니다.",
)
def chat_session(
    session_id: str,
    user_id: str = Query(min_length=1),
    cursor: int | None = Query(default=None, ge=1),
    limit: int = Query(default=20, ge=1, le=200),
    container: AppContainer = Depends(get_app_container),
) -> ChatSessionResponse:
    messages = container.chat_history.get_session_history(
        session_id=session_id,
        user_id=user_id,
        cursor=cursor,
        limit=limit,
    )
    return ChatSessionResponse(
        next_cursor=messages[0].id if messages else None,
        has_more=len(messages) == limit,
        messages=list(reversed(messages)),
    )
