"""GET /chat/list"""

from __future__ import annotations

from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Header, Query

from src.api.dependencies import AppContainer
from src.api.routers.deps import get_app_container
from src.persistence.chat_history import ChatSession

router = APIRouter()


@router.get("/chat/list", response_model=list[ChatSession])
def chat_list(
    persona_id: Annotated[Optional[str], Header(alias="X-Persona-Id")] = None,
    user_id: str = Query(min_length=1),
    cursor: int | None = Query(default=None, ge=1),
    limit: int = Query(default=20, ge=1, le=200),
    container: AppContainer = Depends(get_app_container),
) -> list[ChatSession]:
    return container.chat_history.list_sessions(
        user_id=user_id,
        persona_id=persona_id,
        cursor=cursor,
        limit=limit,
    )
