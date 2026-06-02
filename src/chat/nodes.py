"""LangGraph 노드 구현 (순수 함수 + 의존성 컨테이너).

각 노드는 ``(state, deps) -> partial ChatState`` 시그니처로 작성되어
LangGraph 의 closure 와 단위 테스트 모두에서 재사용 가능하다.

SOLID
-----
- SRP : 노드 함수는 1 책임(임베딩 / intent / arm 선택 / 검색 / 응답 / 영속화) 만 수행.
- DIP : 외부 IO 는 모두 ``ChatGraphDependencies`` 로 주입.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from textwrap import dedent
from typing import Any, Optional, Protocol

from src.chat.state import ChatState
from src.graph.template_executor import DEFAULT_TEMPLATE_ID, TemplateExecutor
from src.persistence.chat_history import ChatHistoryStore
from src.recommend.intent_resolver import IntentResolver, ResolvedIntent
from src.recommend.policy import RecommendPolicy

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Protocols (테스트에서 mock 하기 쉽도록 최소 인터페이스만 노출)
# ---------------------------------------------------------------------------


class EmbedderLike(Protocol):
    def embed(self, text: str) -> list[float]: ...


class ChatLLMLike(Protocol):
    def chat_json(
        self,
        messages: list[dict[str, str]],
        *,
        user_id: str | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
        response_format: dict[str, Any] | None = None,
        cache_salt: str | None = None,
        guided_json_schema: dict[str, Any] | None = None,
    ) -> dict[str, Any]: ...


# ---------------------------------------------------------------------------
# Dependencies
# ---------------------------------------------------------------------------


@dataclass
class ChatGraphDependencies:
    """LangGraph 노드가 사용하는 외부 IO 컨테이너."""

    embedder: EmbedderLike
    intent_resolver: IntentResolver
    policy: RecommendPolicy
    template_executor: TemplateExecutor
    llm: ChatLLMLike
    history: Optional[ChatHistoryStore] = None
    default_top_k: int = 10
    default_vec_top_k: int = 30
    default_max_toxicity: float = 0.7
    recommend_template_id: str = DEFAULT_TEMPLATE_ID
    reply_max_tokens: int = 512
    reply_temperature: float = 0.4
    extra_user_payload: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Node implementations (pure functions on state + deps)
# ---------------------------------------------------------------------------


def embed_query(state: ChatState, deps: ChatGraphDependencies) -> ChatState:
    query = state.get("query", "")
    if not query:
        raise ValueError("ChatState.query is required")
    embedding = deps.embedder.embed(query)
    return {"query_embedding": list(embedding)}


def plan_intent(state: ChatState, deps: ChatGraphDependencies) -> ChatState:
    query = state.get("query", "")
    intent: ResolvedIntent = deps.intent_resolver.resolve(query)
    return {
        "keywords": list(intent.keywords),
        "themes": list(intent.themes),
        "moods": list(intent.moods),
    }


def select_weights(state: ChatState, deps: ChatGraphDependencies) -> ChatState:
    user_id = state.get("user_id", "anonymous")
    arm = deps.policy.select_arm(context_key=user_id)
    return {"arm_id": arm.arm_id, "weights": dict(arm.weights)}


def retrieve_movies(state: ChatState, deps: ChatGraphDependencies) -> ChatState:
    weights = state.get("weights") or {
        "w_vec": 0.55,
        "w_kw": 0.15,
        "w_theme": 0.10,
        "w_mood": 0.05,
        "w_user": 0.15,
    }
    params = {
        "user_id": state.get("user_id", "anonymous"),
        "query_embedding": state.get("query_embedding") or [],
        "query_keywords": state.get("keywords") or [],
        "query_themes": state.get("themes") or [],
        "query_moods": state.get("moods") or [],
        "top_k": int(state.get("top_k") or deps.default_top_k),
        "vec_top_k": int(state.get("vec_top_k") or deps.default_vec_top_k),
        "max_toxicity": float(state.get("max_toxicity") or deps.default_max_toxicity),
        **weights,
    }
    rows = deps.template_executor.execute(
        deps.recommend_template_id, params, fallback=True
    )
    return {"retrieved": list(rows)}


_REPLY_SYSTEM_PROMPT = dedent(
    f"""
    너는 한국어 영화 추천 도우미다.
    아래 추천 후보 목록(JSON)을 근거로 사용자의 요청에 1~3 문장으로 답하라.
    추천된 영화가 없다면 다른 키워드를 제시하라.
    출력은 단일 JSON 객체: {{"reply": "문장", "metadata": {{ "type": "movie", "id": "<영화 ID>" }}}}.
    metadata 는 추천 결과의 타입과 ID를 나타낸다.
    """
).strip()


_REPLY_RESPONSE_FORMAT = {
    "type": "json_schema",
    "json_schema": {
        "name": "reply_knowledge_ontology",
        "strict": True,
        "schema": {
            "type": "object",
            "properties": {
                "reply": {"type": "string"},
                "metadata": {
                    "type": "object",
                    "properties": {
                        "type": { "type": "string", "enum": ["movie"] },
                        "id": {"type": "string"},
                    },
                }
            },
        },
    },
}

def generate_reply(state: ChatState, deps: ChatGraphDependencies) -> ChatState:
    user_query = state.get("query", "")
    retrieved = state.get("retrieved") or []
    payload = {
        "query": user_query,
        "candidates": retrieved[: deps.default_top_k],
        **deps.extra_user_payload,
    }
    messages = [
        {"role": "system", "content": _REPLY_SYSTEM_PROMPT},
        {
            "role": "user",
            "content": json.dumps(payload, ensure_ascii=False),
        },
    ]
    try:
        raw = deps.llm.chat_json(
            messages,
            response_format=_REPLY_RESPONSE_FORMAT,
            user_id=state.get("user_id"),
            max_tokens=deps.reply_max_tokens,
            temperature=deps.reply_temperature,
        )
        reply = str(raw.get("reply") or "").strip()
    except Exception:
        logger.exception("Reply generation failed; falling back to deterministic answer.")
        reply = _fallback_reply(retrieved)
    if not reply:
        reply = _fallback_reply(retrieved)
    return {"reply": reply, "reply_metadata": raw.get("metadata")}


def _fallback_reply(retrieved: list[dict[str, Any]]) -> str:
    if not retrieved:
        return "조건에 맞는 추천을 찾지 못했어요. 다른 키워드로 시도해 보세요."
    titles = ", ".join(str(r.get("title") or r.get("movie_id")) for r in retrieved[:3])
    return f"이런 영화를 추천드려요: {titles}."


def persist_history(state: ChatState, deps: ChatGraphDependencies) -> ChatState:
    retrieved = state.get("retrieved") or []
    ontology_ref = {
        "arm_id": state.get("arm_id"),
        "movie_ids": [str(r.get("movie_id")) for r in retrieved if r.get("movie_id")],
        "themes": state.get("themes") or [],
        "moods": state.get("moods") or [],
    }
    
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


__all__ = [
    "ChatGraphDependencies",
    "ChatLLMLike",
    "EmbedderLike",
    "embed_query",
    "generate_reply",
    "persist_history",
    "plan_intent",
    "retrieve_movies",
    "select_weights",
]
