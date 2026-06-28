"""Agent 노드: tool calling LLM으로 Neo4j 조회 후 structured reply 생성."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from src.chat.nodes.dependencies import ChatGraphDependencies
from src.chat.state import ChatState
from src.config.settings import AppSettings, get_settings

import logging

logger = logging.getLogger(__name__)


_AGENT_SYSTEM_PROMPT = """\
당신은 영화/피드 추천 챗봇의 데이터 조회 에이전트입니다.
사용자 질문에 답하기 위해 Neo4j 지식그래프 조회가 필요한 경우에만 \
`query_neo4j_graph` tool을 호출하세요. 단순 인사·잡담(intent_scope=none)은 tool 없이 바로 응답 준비가 완료되었다고 판단하세요.

tool 호출 시:
- 분석된 retrieved_movies / retrieved_feeds / intent_scope를 반영한 구체적 자연어 질문을 question 인자로 전달하세요.
- tool 응답 status=validation_failed 이면 errors를 읽고 조건을 수정해 재호출하세요.
- 충분한 데이터를 확보했거나 조회가 불필요하면 tool을 호출하지 마세요.

tool 호출 판단에 집중하세요. 영화/피드 추천 결과는 절대로 제공하지 마세요.

Ontology Analysis Context (JSON):
{context}
"""

_AGENT_RESPONSE_PROMPT = """\
당신은 영화/피드 추천 챗봇의 데이터 조회 에이전트입니다.
결과를 출력할때는 neo4j에 관련된 요소들은 숨겨야 합니다.
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
        "intent_scope": state.get("intent_scope", 'none'),
        "retrieved_movies": state.get("retrieved_movies", []),
        "retrieved_feeds": state.get("retrieved_feeds", []),
        "direct_reply_hint": state.get("direct_reply_hint", ''),
    }
    return json.dumps(context, ensure_ascii=False)


def _seed_messages(state: ChatState) -> list:
    existing = list(state.get("messages") or [])
    if existing:
        return existing

    system = SystemMessage(
        content=_AGENT_SYSTEM_PROMPT.format(
            context=_build_agent_context(state),
        )
    )
    year=datetime.now().year
    month=datetime.now().month
    day=datetime.now().day
    human = HumanMessage(
        content=state.get("query", "")
        + f"""\
        Current Date: {year}-{month}-{day}
        현재 날짜는 {year}년 {month}월 {day}일 입니다.
        movie나 feed의 id값은 노출되어선 안됩니다.
        """
    )
    return [system, human]

def call_agent(state: ChatState, deps: ChatGraphDependencies) -> ChatState:
    """LLM agent 노드: tool 호출 또는 structured reply 생성."""
    messages = _seed_messages(state)
    llm = deps.agent_llm.bind_tools(deps.neo4j_tools)
    response = llm.invoke(messages)
    if not isinstance(response, AIMessage):
        response = AIMessage(content=str(response))
    update: ChatState = {"messages": [response]}
    return update


__all__ = ["build_agent_llm", "build_cypher_llm", "call_agent"]
