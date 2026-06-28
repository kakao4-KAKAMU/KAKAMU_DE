"""LangGraph 노드 단위 테스트 (in-memory state, mock deps)."""

from __future__ import annotations

import json
from unittest.mock import MagicMock

from langchain_core.messages import AIMessage, ToolMessage

from src.chat.cypher.service import CypherExecutionResult, Neo4jCypherService
from src.chat.feedback import FeedbackRecorder
from src.chat.graph import AGENT_RECURSION_LIMIT, build_chat_graph
from src.chat.nodes import (
    ChatGraphDependencies,
    build_structured_reply,
    call_agent,
    embed_query,
    persist_history,
)
from src.chat.nodes.tools import merge_tool_results_into_state
from src.chat.tools.neo4j_query import build_neo4j_tools


def _mock_agent_llm(*, with_tool_call: bool = False) -> MagicMock:
    agent_llm = MagicMock()
    bound = MagicMock()
    if with_tool_call:
        calls = {"n": 0}

        def side_effect(messages):
            calls["n"] += 1
            if calls["n"] == 1:
                return AIMessage(
                    content="",
                    tool_calls=[
                        {
                            "name": "query_neo4j_graph",
                            "args": {"question": "잔잔한 성장 영화 추천"},
                            "id": "call_1",
                            "type": "tool_call",
                        }
                    ],
                )
            return AIMessage(content="조회 완료")

        bound.invoke.side_effect = side_effect
    else:
        bound.invoke.return_value = AIMessage(content="조회 불필요")
    agent_llm.bind_tools.return_value = bound
    return agent_llm


def _mock_cypher_tools(
    *,
    feed_rows: list | None = None,
) -> list:
    cypher_service = MagicMock(spec=Neo4jCypherService)
    rows = feed_rows or [{"movie_id": "m1", "title": "Movie 1", "score": 0.9}]
    cypher_service.query.return_value = CypherExecutionResult(
        valid=True,
        cypher="MATCH (m:Movie) RETURN m.movie_id AS movie_id",
        rows=rows,
    )
    return build_neo4j_tools(cypher_service)


def _deps(*, agent_with_tool: bool = False, feed_tool: bool = False) -> ChatGraphDependencies:
    embedder = MagicMock()
    embedder.embed.return_value = [0.1, 0.2, 0.3]

    llm = MagicMock()
    llm.chat_json.return_value = {
        "reply": "이런 영화를 추천드려요",
        "metadata": {"movie": [{"type": "movie", "id": "m1"}]},
    }

    history = MagicMock()
    feed_rows = [{"feed_id": "f1", "summary": "후기", "score": 0.9}] if feed_tool else None

    return ChatGraphDependencies(
        embedder=embedder,
        llm=llm,
        agent_llm=_mock_agent_llm(with_tool_call=agent_with_tool),
        neo4j_tools=_mock_cypher_tools(feed_rows=feed_rows),
        history=history,
    )


def test_embed_query_writes_vector_to_state() -> None:
    deps = _deps()
    out = embed_query({"query": "잔잔한 영화"}, deps)
    assert out == {"query_embedding": [0.1, 0.2, 0.3]}


def test_call_agent_seeds_messages_on_first_invoke() -> None:
    deps = _deps()
    out = call_agent(
        {
            "query": "잔잔한 영화",
            "intent_scope": "movie",
            "retrieved_movies": [{"movie_id": "m1", "title": "Movie 1"}],
        },
        deps,
    )
    assert "messages" in out
    assert len(out["messages"]) == 1
    assert isinstance(out["messages"][0], AIMessage)
    assert "reply" not in out


def test_call_agent_skips_reply_while_tool_calls_pending() -> None:
    deps = _deps(agent_with_tool=True)
    out = call_agent(
        {
            "query": "잔잔한 성장 영화",
            "intent_scope": "movie",
        },
        deps,
    )
    assert out["messages"][0].tool_calls
    assert "reply" not in out


def test_merge_tool_results_syncs_retrieved_movies() -> None:
    tool_payload = json.dumps(
        {
            "status": "ok",
            "cypher": "MATCH (m:Movie) RETURN m",
            "rows": [{"movie_id": "m1", "title": "Movie 1"}],
        },
        ensure_ascii=False,
    )
    out = merge_tool_results_into_state(
        {"messages": [ToolMessage(content=tool_payload, tool_call_id="call_1")]},
        {},
    )
    assert out["retrieved_movies"][0]["movie_id"] == "m1"
    assert out["graph_query_results"][0]["rows"][0]["movie_id"] == "m1"


def test_build_chat_graph_routes_feed_query_via_agent_tool() -> None:
    deps = _deps(agent_with_tool=True, feed_tool=True)
    deps.llm.chat_json.return_value = {
        "reply": "이런 피드를 추천드려요",
        "metadata": {"feed": [{"type": "feed", "id": "f1"}]},
    }
    graph = build_chat_graph(deps)
    final = graph.invoke(
        {"user_id": "u1", "session_id": "s1", "query": "영화 감상 후기 피드 추천"},
        config={"recursion_limit": AGENT_RECURSION_LIMIT},
    )
    assert final["retrieved_feeds"][0]["feed_id"] == "f1"
    assert final["ontology_ref"]["feed_ids"] == ["f1"]


def test_build_structured_reply_uses_llm_json() -> None:
    deps = _deps()
    out = build_structured_reply(
        {
            "query": "추천",
            "intent_scope": "movie",
            "retrieved_movies": [{"movie_id": "m1", "title": "Foo"}],
        },
        deps,
    )
    assert out["reply"] == "이런 영화를 추천드려요"
    assert out["reply_metadata"] == {"movie": [{"type": "movie", "id": "m1"}]}


def test_merge_tool_results_flattens_nested_movie_node() -> None:
    tool_payload = json.dumps(
        {
            "status": "ok",
            "cypher": "MATCH (m:Movie) RETURN m, 0.9 AS score",
            "rows": [
                {
                    "m": {
                        "movie_id": "m1",
                        "title": "Movie 1",
                        "plot_raw": "줄거리",
                    },
                    "score": 0.9,
                }
            ],
        },
        ensure_ascii=False,
    )
    out = merge_tool_results_into_state(
        {"messages": [ToolMessage(content=tool_payload, tool_call_id="call_1")]},
        {},
    )
    movie = out["retrieved_movies"][0]
    assert movie["movie_id"] == "m1"
    assert movie["title"] == "Movie 1"
    assert movie["plot_raw"] == "줄거리"
    assert movie["score"] == 0.9


def test_build_structured_reply_uses_graph_query_results_as_candidates() -> None:
    deps = _deps()
    build_structured_reply(
        {
            "query": "추천",
            "intent_scope": "movie",
            "graph_query_results": [
                {
                    "cypher": "MATCH ...",
                    "rows": [{"movie_id": "m1", "title": "Movie 1", "plot_raw": "줄거리"}],
                }
            ],
        },
        deps,
    )
    messages = deps.llm.chat_json.call_args.kwargs.get("messages") or deps.llm.chat_json.call_args.args[0]
    system_text = "\n".join(m["content"] for m in messages if m["role"] == "system")
    assert '"movie_id": "m1"' in system_text
    assert '"plot": "줄거리"' in system_text
    assert "[영화 추천 후보 목록]" in system_text


def test_build_structured_reply_includes_plot_in_system_prompt() -> None:
    deps = _deps()
    build_structured_reply(
        {
            "query": "추천",
            "intent_scope": "movie",
            "retrieved_movies": [
                {
                    "movie_id": "m1",
                    "title": "Movie 1",
                    "plot_summary": "성장 드라마",
                    "producing_year": 2019,
                }
            ],
        },
        deps,
    )
    messages = deps.llm.chat_json.call_args.kwargs.get("messages") or deps.llm.chat_json.call_args.args[0]
    system_text = "\n".join(m["content"] for m in messages if m["role"] == "system")
    assert '"plot": "성장 드라마"' in system_text
    assert "[영화 추천 후보 목록]" in system_text
    assert "[Neo4j" not in system_text


def test_build_structured_reply_falls_back_when_llm_raises() -> None:
    deps = _deps()
    deps.llm.chat_json.side_effect = RuntimeError("boom")
    out = build_structured_reply(
        {
            "query": "추천",
            "intent_scope": "movie",
            "retrieved_movies": [{"movie_id": "m1", "title": "기생충"}],
        },
        deps,
    )
    assert "기생충" in out["reply"]
    assert out["reply_metadata"] == {"movie": [{"type": "movie", "id": "m1"}]}


def test_build_structured_reply_normalizes_multiple_movie_metadata() -> None:
    deps = _deps()
    deps.llm.chat_json.return_value = {
        "reply": "세 편 추천",
        "metadata": {
            "movie": [
                {"type": "movie", "id": "m1"},
                {"type": "movie", "id": "m2"},
                {"type": "movie", "id": "m3"},
            ]
        },
    }
    out = build_structured_reply(
        {
            "query": "추천",
            "intent_scope": "movie",
            "retrieved_movies": [
                {"movie_id": "m1"},
                {"movie_id": "m2"},
                {"movie_id": "m3"},
            ],
        },
        deps,
    )
    assert out["reply_metadata"] == {
        "movie": [
            {"type": "movie", "id": "m1"},
            {"type": "movie", "id": "m2"},
            {"type": "movie", "id": "m3"},
        ]
    }


def test_build_structured_reply_accepts_legacy_single_object_metadata() -> None:
    deps = _deps()
    deps.llm.chat_json.return_value = {
        "reply": "추천",
        "metadata": {"movie": {"type": "movie", "id": "m1"}},
    }
    out = build_structured_reply(
        {"query": "추천", "intent_scope": "movie", "retrieved_movies": [{"movie_id": "m1"}]},
        deps,
    )
    assert out["reply_metadata"] == {"movie": [{"type": "movie", "id": "m1"}]}


def test_build_structured_reply_none_scope_without_retrieval() -> None:
    deps = _deps()
    deps.llm.chat_json.return_value = {
        "reply": "안녕하세요!",
        "metadata": {},
    }
    out = build_structured_reply(
        {"query": "안녕", "intent_scope": "none", "direct_reply_hint": "인사"},
        deps,
    )
    assert out["reply"] == "안녕하세요!"


def test_persist_history_appends_when_session_id_present() -> None:
    deps = _deps()
    out = persist_history(
        {
            "session_id": "s1",
            "user_id": "u1",
            "reply": "ok",
            "intent_scope": "movie",
            "retrieved_movies": [{"movie_id": "m1"}],
            "themes": ["성장"],
            "moods": [],
            "feed_filters": {},
        },
        deps,
    )
    deps.history.append.assert_called_once()
    assert out["ontology_ref"]["movie_ids"] == ["m1"]


def test_build_chat_graph_runs_full_flow_with_agent_tool() -> None:
    deps = _deps(agent_with_tool=True)
    graph = build_chat_graph(deps)
    final = graph.invoke(
        {"user_id": "u1", "session_id": "s1", "query": "잔잔한 성장 영화 추천"},
        config={"recursion_limit": AGENT_RECURSION_LIMIT},
    )
    assert final["reply"]
    assert final["retrieved_movies"][0]["movie_id"] == "m1"
    deps.history.append.assert_called()


def test_build_chat_graph_skips_tool_for_none_scope() -> None:
    deps = _deps(agent_with_tool=False)
    deps.llm.chat_json.return_value = {
        "reply": "안녕하세요!",
        "metadata": {},
    }
    graph = build_chat_graph(deps)
    final = graph.invoke(
        {"user_id": "u1", "session_id": "s1", "query": "안녕하세요"},
        config={"recursion_limit": AGENT_RECURSION_LIMIT},
    )
    assert final["reply"] == "안녕하세요!"


def test_feedback_recorder_records_with_chat_policy() -> None:
    policy = MagicMock()
    recorder = FeedbackRecorder(policy)
    result = recorder.record(arm_id="vec_heavy", context_key="u1", action="click")
    assert result.reward == 1.0
    policy.record_reward.assert_called_once()
