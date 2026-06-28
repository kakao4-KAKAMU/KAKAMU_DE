from __future__ import annotations
from typing import Optional
from pydantic import BaseModel, Field
from uuid import uuid4
from src.api.security.limits import DEFAULT_MAX_CHAT_MESSAGE_LENGTH
from src.persistence.chat_history import ChatMessage

# ---------------------------------------------------------------------------
# /chat
# ---------------------------------------------------------------------------


class ChatRequest(BaseModel):
    user_id: str = Field(min_length=1)
    persona_id: Optional[str] = Field(default=None)
    session_id: Optional[str] = Field(default=None)
    message: str = Field(min_length=1, max_length=DEFAULT_MAX_CHAT_MESSAGE_LENGTH)
    top_k: int = Field(default=20, ge=1, le=50)
    max_toxicity: float = Field(default=0.7, ge=0.0, le=1.0)

    def ensure_session_id(self) -> str:
        return self.session_id or str(uuid4())


# ---------------------------------------------------------------------------
# /chat/session
# ---------------------------------------------------------------------------


class ChatSessionResponse(BaseModel):
    next_cursor: Optional[int]
    has_more: bool
    messages: list[ChatMessage]


class ChatSessionRequest(BaseModel):
    cursor: Optional[int] = None
    limit: int = 20
