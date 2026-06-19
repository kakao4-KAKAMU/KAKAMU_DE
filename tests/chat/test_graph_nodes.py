"""LangGraph 노드 단위 테스트 (in-memory state, mock deps)."""

from __future__ import annotations

from unittest.mock import MagicMock

from src.chat.feedback import FeedbackRecorder
from src.chat.graph import build_chat_graph
from src.chat.nodes import (
    ChatGraphDependencies,
    classify_media,
    embed_query,
    generate_reply,
    persist_history,
    plan_intent,
    retrieve_feeds,
    retrieve_movies,
    route_media,
    select_weights,
)
from src.recommend.arms import BanditArm
from src.recommend.intent_resolver import ResolvedIntent


def _deps() -> ChatGraphDependencies:
    embedder = MagicMock()
    embedder.embed.return_value = [0.1, 0.2, 0.3]

    intent_resolver = MagicMock()
    intent_resolver.resolve.return_value = ResolvedIntent(
        keywords=["성장"], themes=["성장"], moods=["잔잔한"]
    )

    policy = MagicMock()
    policy.select_arm.return_value = BanditArm(
        "balanced",
        {"w_vec": 0.5, "w_kw": 0.15, "w_theme": 0.15, "w_mood": 0.1, "w_user": 0.1},
    )

    template_executor = MagicMock()
    template_executor.execute.return_value = [
        {"movie_id": "m1", "title": "Movie 1", "score": 0.9}
    ]

    llm = MagicMock()
    llm.chat_json.return_value = {"reply": "이런 영화를 추천드려요"}

    media_classifier = MagicMock()
    media_classifier.classify.return_value = "movie"

    history = MagicMock()

    return ChatGraphDependencies(
        embedder=embedder,
        intent_resolver=intent_resolver,
        policy=policy,
        template_executor=template_executor,
        llm=llm,
        history=history,
        media_classifier=media_classifier,
    )


def test_embed_query_writes_vector_to_state() -> None:
    deps = _deps()
    out = embed_query({"query": "잔잔한 영화"}, deps)
    assert out == {"query_embedding": [0.1, 0.2, 0.3]}


def test_plan_intent_resolves_themes_moods() -> None:
    deps = _deps()
    out = plan_intent({"query": "잔잔한 성장 드라마"}, deps)
    assert out["themes"] == ["성장"]
    assert out["moods"] == ["잔잔한"]


def test_select_weights_records_arm_id() -> None:
    deps = _deps()
    out = select_weights({"user_id": "u-1", "persona_id": "movie_buff"}, deps)
    assert out["arm_id"] == "balanced"
    assert out["weights"]["w_vec"] == 0.5
    deps.policy.select_arm.assert_called_once_with(context_key="u-1:movie_buff")


def test_retrieve_movies_calls_template_executor_with_weights() -> None:
    deps = _deps()
    state = {
        "user_id": "u-1",
        "query_embedding": [0.1],
        "keywords": ["성장"],
        "themes": ["성장"],
        "moods": [],
        "weights": {
            "w_vec": 0.5,
            "w_kw": 0.15,
            "w_theme": 0.15,
            "w_mood": 0.1,
            "w_user": 0.1,
        },
    }
    out = retrieve_movies(state, deps)
    deps.template_executor.execute.assert_called_once()
    params = deps.template_executor.execute.call_args.args[1]
    assert params["query_embedding"] == [0.1]
    assert params["w_vec"] == 0.5
    assert "max_toxicity" in params
    assert out["retrieved"][0]["movie_id"] == "m1"


def test_classify_media_delegates_to_classifier() -> None:
    deps = _deps()
    deps.media_classifier.classify.return_value = "feed"
    out = classify_media({"query": "잔잔한 영화 후기 추천"}, deps)
    assert out["media_type"] == "feed"
    deps.media_classifier.classify.assert_called_once_with("잔잔한 영화 후기 추천")


def test_classify_media_movie_decision() -> None:
    deps = _deps()
    deps.media_classifier.classify.return_value = "movie"
    out = classify_media({"query": "잔잔한 성장 영화 추천"}, deps)
    assert out["media_type"] == "movie"


def test_classify_media_respects_existing_media_type() -> None:
    deps = _deps()
    out = classify_media({"query": "영화 추천", "media_type": "feed"}, deps)
    assert out["media_type"] == "feed"
    deps.media_classifier.classify.assert_not_called()


def test_route_media_returns_branch_key() -> None:
    assert route_media({"media_type": "feed"}) == "feed"
    assert route_media({"media_type": "movie"}) == "movie"
    assert route_media({}) == "movie"


def test_retrieve_feeds_uses_feed_template_without_fallback() -> None:
    deps = _deps()
    deps.template_executor.execute.return_value = [
        {"feed_id": "f1", "summary": "감동적인 후기", "score": 0.8}
    ]
    state = {
        "user_id": "u-1",
        "query_embedding": [0.1],
        "keywords": ["성장"],
        "themes": [],
        "moods": [],
        "weights": {
            "w_vec": 0.5,
            "w_kw": 0.15,
            "w_theme": 0.15,
            "w_mood": 0.1,
            "w_user": 0.1,
        },
    }
    out = retrieve_feeds(state, deps)
    deps.template_executor.execute.assert_called_once()
    template_id = deps.template_executor.execute.call_args.args[0]
    assert template_id == "hybrid_feed_recommend"
    assert deps.template_executor.execute.call_args.kwargs["fallback"] is False
    assert out["retrieved"][0]["feed_id"] == "f1"


def test_build_chat_graph_routes_feed_query() -> None:
    deps = _deps()
    deps.media_classifier.classify.return_value = "feed"
    deps.template_executor.execute.return_value = [
        {"feed_id": "f1", "summary": "후기", "score": 0.9}
    ]
    deps.llm.chat_json.return_value = {
        "reply": "이런 피드를 추천드려요",
        "metadata": {"type": "feed", "id": "f1"},
    }
    graph = build_chat_graph(deps)
    final = graph.invoke(
        {"user_id": "u1", "session_id": "s1", "query": "영화 감상 후기 피드 추천"}
    )
    assert final["media_type"] == "feed"
    assert final["retrieved"][0]["feed_id"] == "f1"
    template_id = deps.template_executor.execute.call_args.args[0]
    assert template_id == "hybrid_feed_recommend"
    assert final["ontology_ref"]["feed_ids"] == ["f1"]


def test_generate_reply_uses_llm_json() -> None:
    deps = _deps()
    out = generate_reply(
        {"query": "추천", "retrieved": [{"movie_id": "m1", "title": "Foo"}]},
        deps,
    )
    assert out["reply"] == "이런 영화를 추천드려요"


def test_generate_reply_falls_back_when_llm_raises() -> None:
    deps = _deps()
    deps.llm.chat_json.side_effect = RuntimeError("boom")
    out = generate_reply(
        {"query": "추천", "retrieved": [{"movie_id": "m1", "title": "기생충"}]},
        deps,
    )
    assert "기생충" in out["reply"]


def test_persist_history_appends_when_session_id_present() -> None:
    deps = _deps()
    out = persist_history(
        {
            "session_id": "s1",
            "user_id": "u1",
            "reply": "ok",
            "arm_id": "balanced",
            "retrieved": [{"movie_id": "m1"}],
            "themes": ["성장"],
            "moods": [],
        },
        deps,
    )
    deps.history.append.assert_called_once()
    assert out["ontology_ref"]["movie_ids"] == ["m1"]


def test_build_chat_graph_runs_full_flow() -> None:
    deps = _deps()
    graph = build_chat_graph(deps)
    final = graph.invoke(
        {"user_id": "u1", "session_id": "s1", "query": "잔잔한 성장 영화 추천"}
    )
    assert final["reply"]
    assert final["arm_id"] == "balanced"
    assert final["retrieved"][0]["movie_id"] == "m1"
    deps.history.append.assert_called()


def test_feedback_recorder_records_with_chat_policy() -> None:
    policy = MagicMock()
    recorder = FeedbackRecorder(policy)
    result = recorder.record(arm_id="vec_heavy", context_key="u1", action="click")
    assert result.reward == 1.0
    policy.record_reward.assert_called_once()
