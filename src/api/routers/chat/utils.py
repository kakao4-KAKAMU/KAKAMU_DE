"""채팅 라우터 공용 유틸."""

from __future__ import annotations

from typing import Any, Optional

from src.api.schemas.schemas import ChatRequest
from src.chat.state import ChatState


def initial_chat_state(
    req: ChatRequest,
    user_id: str,
    session_id: str,
    persona_id: Optional[str] = None,
) -> ChatState:
    return ChatState(
        user_id=user_id,
        persona_id=persona_id,
        session_id=session_id,
        query=req.message,
        top_k=req.top_k,
        max_toxicity=req.max_toxicity,
    )


def jsonify(value: Any) -> Any:
    """SSE 직렬화: dict/list 만 통과, 그 외 객체는 repr."""
    if isinstance(value, dict):
        return {k: jsonify(v) for k, v in value.items()}
    if isinstance(value, list):
        return [jsonify(v) for v in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return repr(value)
