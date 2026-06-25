"""LangGraph 노드 단위 테스트 (in-memory state, mock deps)."""

from __future__ import annotations

from unittest.mock import MagicMock

from src.chat.feedback import FeedbackRecorder
from src.chat.graph import build_chat_graph
from src.chat.nodes import (
    ChatGraphDependencies,
    analyze_query,
    embed_query,
    filter_feeds,
    filter_movies,
    generate_reply,
    persist_history,
    route_after_analysis,
)
from src.recommend.arms import BanditArm
from src.recommend.query_analyzer import (
    FeedQueryFilters,
    MovieQueryFilters,
    QueryAnalysis,
)


def _deps() -> ChatGraphDependencies:
    embedder = MagicMock()
    embedder.embed.return_value = [0.1, 0.2, 0.3]

    intent_resolver = MagicMock()
    intent_resolver.resolve.return_value = MagicMock(
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
    llm.chat_json.return_value = {
        "reply": "이런 영화를 추천드려요",
        "metadata": {"movie": [{"type": "movie", "id": "m1"}]},
    }

    query_analyzer = MagicMock()
    query_analyzer.analyze.return_value = QueryAnalysis(
        intent_scope="movie",
        movie=MovieQueryFilters(
            genres=[],
            themes=["성장"],
            moods=["잔잔한"],
            keywords=["성장"],
        ),
        feed=FeedQueryFilters(),
    )

    history = MagicMock()

    return ChatGraphDependencies(
        embedder=embedder,
        intent_resolver=intent_resolver,
        policy=policy,
        template_executor=template_executor,
        llm=llm,
        history=history,
        query_analyzer=query_analyzer,
    )


def test_embed_query_writes_vector_to_state() -> None:
    deps = _deps()
    out = embed_query({"query": "잔잔한 영화"}, deps)
    assert out == {"query_embedding": [0.1, 0.2, 0.3]}


def test_analyze_query_resolves_ontology_filters() -> None:
    deps = _deps()
    out = analyze_query({"query": "잔잔한 성장 드라마"}, deps)
    assert out["intent_scope"] == "movie"
    assert out["themes"] == ["성장"]
    assert out["moods"] == ["잔잔한"]
    assert out["movie_filters"]["themes"] == ["성장"]


def test_filter_movies_calls_template_executor_with_weights() -> None:
    deps = _deps()
    state = {
        "user_id": "u-1",
        "query_embedding": [0.1],
        "intent_scope": "movie",
        "movie_filters": {
            "keywords": ["성장"],
            "themes": ["성장"],
            "moods": [],
            "genres": [],
            "person_names": [],
            "person_jobs": [],
            "country": "",
            "min_year": 0,
            "max_year": 0,
        },
    }
    out = filter_movies(state, deps)
    deps.template_executor.execute.assert_called_once()
    params = deps.template_executor.execute.call_args.args[1]
    assert params["query_embedding"] == [0.1]
    assert params["w_vec"] == 0.5
    assert "max_toxicity" in params
    assert out["retrieved_movies"][0]["movie_id"] == "m1"


def test_route_after_analysis_returns_branch_key() -> None:
    assert route_after_analysis({"intent_scope": "feed"}) == "feed"
    assert route_after_analysis({"intent_scope": "movie"}) == "movie"
    assert route_after_analysis({"intent_scope": "both"}) == "both"
    assert route_after_analysis({"intent_scope": "none"}) == "none"
    assert route_after_analysis({}) == "none"


def test_filter_feeds_uses_feed_template_without_fallback() -> None:
    deps = _deps()
    deps.template_executor.execute.return_value = [
        {"feed_id": "f1", "summary": "감동적인 후기", "score": 0.8}
    ]
    state = {
        "user_id": "u-1",
        "query_embedding": [0.1],
        "intent_scope": "feed",
        "feed_filters": {
            "categories": ["review"],
            "emotions": [],
            "keywords": ["성장"],
            "sentiment": "positive",
            "contains_spoiler": False,
            "related_movie_title": "",
        },
    }
    out = filter_feeds(state, deps)
    deps.template_executor.execute.assert_called_once()
    template_id = deps.template_executor.execute.call_args.args[0]
    assert template_id == "chat_feed_filter"
    assert deps.template_executor.execute.call_args.kwargs["fallback"] is False
    assert out["retrieved_feeds"][0]["feed_id"] == "f1"


def test_filter_movies_passes_ontology_params_to_template() -> None:
    deps = _deps()
    state = {
        "user_id": "u-1",
        "query_embedding": [0.1],
        "intent_scope": "movie",
        "movie_filters": {
            "keywords": ["성장"],
            "themes": ["성장"],
            "moods": [],
            "genres": ["드라마"],
            "person_names": ["봉준호"],
            "person_jobs": ["director"],
            "country": "KR",
            "min_year": 2010,
            "max_year": 2024,
        },
    }
    filter_movies(state, deps)
    params = deps.template_executor.execute.call_args.args[1]
    assert params["query_genres"] == ["드라마"]
    assert params["query_person_names"] == ["봉준호"]
    assert params["filter_country"] == "kr"
    assert deps.template_executor.execute.call_args.args[0] == "chat_movie_filter"


def test_filter_feeds_passes_ontology_params_to_template() -> None:
    deps = _deps()
    deps.template_executor.execute.return_value = [
        {"feed_id": "f1", "summary": "후기", "score": 0.8}
    ]
    state = {
        "user_id": "u-1",
        "query_embedding": [0.1],
        "intent_scope": "feed",
        "feed_filters": {
            "categories": ["review"],
            "emotions": ["joy"],
            "keywords": ["감동"],
            "sentiment": "positive",
            "contains_spoiler": False,
            "related_movie_title": "기생충",
        },
    }
    filter_feeds(state, deps)
    params = deps.template_executor.execute.call_args.args[1]
    assert params["query_categories"] == ["review"]
    assert params["query_emotions"] == ["joy"]
    assert params["filter_sentiment"] == "positive"
    assert params["related_movie_title"] == "기생충"
    assert deps.template_executor.execute.call_args.args[0] == "chat_feed_filter"


def test_build_chat_graph_routes_feed_query() -> None:
    deps = _deps()
    deps.query_analyzer.analyze.return_value = QueryAnalysis(
        intent_scope="feed",
        movie=MovieQueryFilters(),
        feed=FeedQueryFilters(keywords=["후기"], categories=["review"]),
    )
    deps.template_executor.execute.return_value = [
        {"feed_id": "f1", "summary": "후기", "score": 0.9}
    ]
    deps.llm.chat_json.return_value = {
        "reply": "이런 피드를 추천드려요",
        "metadata": {"feed": [{"type": "feed", "id": "f1"}]},
    }
    graph = build_chat_graph(deps)
    final = graph.invoke(
        {"user_id": "u1", "session_id": "s1", "query": "영화 감상 후기 피드 추천"}
    )
    assert final["intent_scope"] == "feed"
    assert final["retrieved_feeds"][0]["feed_id"] == "f1"
    template_id = deps.template_executor.execute.call_args.args[0]
    assert template_id == "chat_feed_filter"
    assert final["ontology_ref"]["feed_ids"] == ["f1"]


def test_generate_reply_uses_llm_json() -> None:
    deps = _deps()
    out = generate_reply(
        {
            "query": "추천",
            "intent_scope": "movie",
            "retrieved_movies": [{"movie_id": "m1", "title": "Foo"}],
        },
        deps,
    )
    assert out["reply"] == "이런 영화를 추천드려요"
    assert out["reply_metadata"] == {"movie": [{"type": "movie", "id": "m1"}]}


def test_generate_reply_falls_back_when_llm_raises() -> None:
    deps = _deps()
    deps.llm.chat_json.side_effect = RuntimeError("boom")
    out = generate_reply(
        {
            "query": "추천",
            "intent_scope": "movie",
            "retrieved_movies": [{"movie_id": "m1", "title": "기생충"}],
        },
        deps,
    )
    assert "기생충" in out["reply"]
    assert out["reply_metadata"] == {"movie": [{"type": "movie", "id": "m1"}]}


def test_generate_reply_normalizes_multiple_movie_metadata() -> None:
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
    out = generate_reply(
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


def test_generate_reply_accepts_legacy_single_object_metadata() -> None:
    deps = _deps()
    deps.llm.chat_json.return_value = {
        "reply": "추천",
        "metadata": {"movie": {"type": "movie", "id": "m1"}},
    }
    out = generate_reply(
        {"query": "추천", "intent_scope": "movie", "retrieved_movies": [{"movie_id": "m1"}]},
        deps,
    )
    assert out["reply_metadata"] == {"movie": [{"type": "movie", "id": "m1"}]}


def test_generate_reply_none_scope_without_retrieval() -> None:
    deps = _deps()
    deps.llm.chat_json.return_value = {
        "reply": "안녕하세요!",
        "metadata": {},
    }
    out = generate_reply(
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
            "movie_filters": {"themes": ["성장"]},
            "feed_filters": {},
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
    assert final["retrieved_movies"][0]["movie_id"] == "m1"
    deps.history.append.assert_called()


def test_build_chat_graph_skips_filter_for_none_scope() -> None:
    deps = _deps()
    deps.query_analyzer.analyze.return_value = QueryAnalysis(
        intent_scope="none",
        movie=MovieQueryFilters(),
        feed=FeedQueryFilters(),
        direct_reply_hint="인사",
    )
    deps.llm.chat_json.return_value = {
        "reply": "안녕하세요!",
        "metadata": {},
    }
    graph = build_chat_graph(deps)
    final = graph.invoke(
        {"user_id": "u1", "session_id": "s1", "query": "안녕하세요"}
    )
    assert final["intent_scope"] == "none"
    deps.template_executor.execute.assert_not_called()
    assert final["reply"] == "안녕하세요!"


def test_feedback_recorder_records_with_chat_policy() -> None:
    policy = MagicMock()
    recorder = FeedbackRecorder(policy)
    result = recorder.record(arm_id="vec_heavy", context_key="u1", action="click")
    assert result.reward == 1.0
    policy.record_reward.assert_called_once()
