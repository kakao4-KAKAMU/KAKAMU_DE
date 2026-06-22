"""filter 노드: 분석된 온톨로지 필터로 매체별 기본 하이브리드 검색.

``chat_movie_filter`` / ``chat_feed_filter`` 템플릿에 질의 분석 온톨로지 필터를
전달해 Cypher 단계에서 기본 필터링을 수행한다.

SOLID
-----
- SRP : 파라미터 구성과 템플릿 실행만 담당.
- DRY : 파라미터 조립을 ``build_chat_*_filter_params`` 로 위임.
"""

from __future__ import annotations

from typing import Any

from src.chat.nodes.dependencies import DEFAULT_WEIGHTS, ChatGraphDependencies
from src.chat.state import ChatState
from src.recommend.context import (
    bandit_context_key,
    build_chat_feed_filter_params,
    build_chat_movie_filter_params,
)


def _select_weights(state: ChatState, deps: ChatGraphDependencies) -> tuple[str, dict[str, float]]:
    if state.get("weights"):
        return str(state.get("arm_id") or "preset"), dict(state["weights"])
    user_id = state.get("user_id", "anonymous")
    context_key = bandit_context_key(user_id, state.get("persona_id"))
    arm = deps.policy.select_arm(context_key=context_key)
    return arm.arm_id, dict(arm.weights)


def _movie_search_tokens(state: ChatState) -> tuple[list[str], list[str], list[str]]:
    filters = state.get("movie_filters") or {}
    keywords = list(filters.get("keywords") or state.get("keywords") or [])
    themes = list(filters.get("themes") or state.get("themes") or [])
    moods = list(filters.get("moods") or state.get("moods") or [])
    genres = list(filters.get("genres") or [])
    persons = list(filters.get("person_names") or [])
    merged_keywords = list(dict.fromkeys(keywords + genres + persons))
    return merged_keywords, themes, moods


def _feed_search_tokens(state: ChatState) -> tuple[list[str], list[str], list[str]]:
    filters = state.get("feed_filters") or {}
    keywords = list(filters.get("keywords") or [])
    categories = list(filters.get("categories") or [])
    emotions = list(filters.get("emotions") or [])
    merged_keywords = list(dict.fromkeys(keywords + categories + emotions))
    return merged_keywords, [], emotions


def _build_movie_filter_params(
    state: ChatState,
    deps: ChatGraphDependencies,
) -> tuple[dict[str, Any], str, dict[str, float]]:
    filters = state.get("movie_filters") or {}
    keywords, themes, moods = _movie_search_tokens(state)
    arm_id, arm_weights = _select_weights(state, deps)
    params = build_chat_movie_filter_params(
        user_id=state.get("user_id", "anonymous"),
        persona_id=state.get("persona_id"),
        query_embedding=state.get("query_embedding") or [],
        query_keywords=keywords,
        query_themes=themes,
        query_moods=moods,
        query_genres=list(filters.get("genres") or []),
        query_person_names=list(filters.get("person_names") or []),
        query_person_jobs=list(filters.get("person_jobs") or []),
        filter_country=str(filters.get("country") or ""),
        min_year=int(filters.get("min_year") or 0),
        max_year=int(filters.get("max_year") or 0),
        top_k=int(state.get("top_k") or deps.default_top_k),
        vec_top_k=int(state.get("vec_top_k") or deps.default_vec_top_k),
        max_toxicity=float(state.get("max_toxicity") or deps.default_max_toxicity),
        weights=arm_weights,
    )
    return params, arm_id, arm_weights


def _build_feed_filter_params(
    state: ChatState,
    deps: ChatGraphDependencies,
) -> tuple[dict[str, Any], str, dict[str, float]]:
    filters = state.get("feed_filters") or {}
    keywords, themes, moods = _feed_search_tokens(state)
    arm_id, arm_weights = _select_weights(state, deps)
    sentiment = str(filters.get("sentiment") or "").strip()
    filter_sentiment = "" if sentiment in ("", "neutral") else sentiment
    params = build_chat_feed_filter_params(
        user_id=state.get("user_id", "anonymous"),
        persona_id=state.get("persona_id"),
        query_embedding=state.get("query_embedding") or [],
        query_keywords=keywords,
        query_themes=themes,
        query_moods=moods,
        query_categories=list(filters.get("categories") or []),
        query_emotions=list(filters.get("emotions") or []),
        filter_sentiment=filter_sentiment,
        include_spoiler=bool(filters.get("contains_spoiler")),
        related_movie_title=str(filters.get("related_movie_title") or ""),
        top_k=int(state.get("top_k") or deps.default_top_k),
        vec_top_k=int(state.get("vec_top_k") or deps.default_vec_top_k),
        max_toxicity=float(state.get("max_toxicity") or deps.default_max_toxicity),
        weights=arm_weights,
    )
    return params, arm_id, arm_weights


def filter_movies(state: ChatState, deps: ChatGraphDependencies) -> ChatState:
    params, arm_id, arm_weights = _build_movie_filter_params(state, deps)
    rows = deps.template_executor.execute(
        deps.movie_template_id, params, fallback=True
    )
    retrieved = list(rows)
    return {
        "retrieved": retrieved,
        "retrieved_movies": retrieved,
        "arm_id": arm_id,
        "weights": arm_weights or DEFAULT_WEIGHTS,
    }


def filter_feeds(state: ChatState, deps: ChatGraphDependencies) -> ChatState:
    params, arm_id, arm_weights = _build_feed_filter_params(state, deps)
    rows = deps.template_executor.execute(
        deps.feed_template_id, params, fallback=False
    )
    retrieved = list(rows)
    return {
        "retrieved": retrieved,
        "retrieved_feeds": retrieved,
        "arm_id": arm_id,
        "weights": arm_weights or DEFAULT_WEIGHTS,
    }


def filter_both(state: ChatState, deps: ChatGraphDependencies) -> ChatState:
    movie_out = filter_movies(state, deps)
    feed_out = filter_feeds(state, deps)
    return {
        "retrieved_movies": movie_out.get("retrieved_movies") or [],
        "retrieved_feeds": feed_out.get("retrieved_feeds") or [],
        "retrieved": (movie_out.get("retrieved_movies") or [])
        + (feed_out.get("retrieved_feeds") or []),
        "arm_id": movie_out.get("arm_id"),
        "weights": movie_out.get("weights") or feed_out.get("weights") or DEFAULT_WEIGHTS,
    }


# 하위 호환 alias
retrieve_movies = filter_movies
retrieve_feeds = filter_feeds


__all__ = [
    "filter_both",
    "filter_feeds",
    "filter_movies",
    "retrieve_feeds",
    "retrieve_movies",
]
