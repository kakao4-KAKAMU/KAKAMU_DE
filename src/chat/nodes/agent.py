"""Agent 노드: tool calling LLM으로 Neo4j 조회 후 structured reply 생성."""

from __future__ import annotations

import json
from typing import Any

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from src.chat.nodes.dependencies import ChatGraphDependencies
from src.chat.nodes.reply import build_structured_reply
from src.chat.state import ChatState
from src.config.settings import AppSettings, get_settings

_AGENT_SYSTEM_PROMPT = """\
당신은 영화/피드 추천 챗봇의 데이터 조회 에이전트입니다.

사용자 질문에 답하기 위해 Neo4j 지식그래프 조회가 필요한 경우에만 \
`query_neo4j_graph` tool을 호출하세요. 단순 인사·잡담(intent_scope=none)은 tool 없이 \
바로 응답 준비가 완료되었다고 판단하세요.

tool 호출 시:
- 분석된 movie_filters / feed_filters / intent_scope를 반영한 구체적 자연어 질문을 \
question 인자로 전달하세요.
- tool 응답 status=validation_failed 이면 errors를 읽고 조건을 수정해 재호출하세요.
- 충분한 데이터를 확보했거나 조회가 불필요하면 tool을 호출하지 마세요.

조회가 끝나 tool을 더 이상 호출하지 않을 때, 시스템이 조회 결과를 바탕으로 \
한국어 reply 와 reply_metadata(type/id)를 생성합니다.

분석 컨텍스트 (JSON):
{context}
"""


def build_agent_llm(settings: AppSettings | None = None) -> BaseChatModel:
    """vLLM OpenAI-compatible endpoint용 ChatOpenAI (tool calling)."""
    cfg = settings or get_settings()
    gen = cfg.vllm_gen
    return ChatOpenAI(
        base_url=gen.base_url,
        api_key=gen.api_key,
        model=gen.model_name,
        temperature=gen.temperature,
        max_tokens=gen.max_tokens,
    )


def build_cypher_llm(settings: AppSettings | None = None) -> BaseChatModel:
    """Cypher 생성 전용 ChatOpenAI (Qwen thinking 비활성화)."""
    cfg = settings or get_settings()
    gen = cfg.vllm_gen
    return ChatOpenAI(
        base_url=gen.base_url,
        api_key=gen.api_key,
        model=gen.model_name,
        temperature=gen.temperature,
        max_tokens=gen.max_tokens,
        extra_body={"chat_template_kwargs": {"enable_thinking": False}},
    )


def _build_agent_context(state: ChatState) -> str:
    context: dict[str, Any] = {
        "query": state.get("query", ""),
        "intent_scope": state.get("intent_scope"),
        "movie_filters": state.get("movie_filters") or {},
        "feed_filters": state.get("feed_filters") or {},
        "direct_reply_hint": state.get("direct_reply_hint") or "",
    }
    return json.dumps(context, ensure_ascii=False)


def _seed_messages(state: ChatState, deps: ChatGraphDependencies) -> list:
    existing = list(state.get("messages") or [])
    if existing:
        return existing

    system = SystemMessage(
        content=_AGENT_SYSTEM_PROMPT.format(context=_build_agent_context(state))
    )
    human = HumanMessage(content=state.get("query", ""))
    return [system, human]


def _has_tool_calls(response: AIMessage) -> bool:
    tool_calls = getattr(response, "tool_calls", None) or []
    return bool(tool_calls)


def call_agent(state: ChatState, deps: ChatGraphDependencies) -> ChatState:
    """LLM agent 노드: tool 호출 또는 structured reply 생성."""
    messages = _seed_messages(state, deps)
    llm = deps.agent_llm.bind_tools(deps.neo4j_tools)
    response = llm.invoke(messages)
    if not isinstance(response, AIMessage):
        response = AIMessage(content=str(response))

    update: ChatState = {"messages": [response]}
    if not _has_tool_calls(response):
        update.update(build_structured_reply(state, deps))
    return update


__all__ = ["build_agent_llm", "build_cypher_llm", "call_agent"]
