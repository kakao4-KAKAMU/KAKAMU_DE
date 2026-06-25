"""analyze_query 노드: LLM 기반 질의 → 영화/피드 온톨로지 필터 분석."""

from __future__ import annotations

from src.chat.nodes.dependencies import ChatGraphDependencies
from src.chat.state import ChatState, MediaType
from src.ontology.schema import keyword_search_terms
from src.recommend.query_analyzer import QueryAnalysis


def _analysis_to_state(analysis: QueryAnalysis) -> ChatState:
    movie = analysis.movie
    media_type: MediaType | None
    if analysis.intent_scope == "both":
        media_type = None
    elif analysis.intent_scope in ("movie", "feed"):
        media_type = analysis.intent_scope
    else:
        media_type = None

    keyword_terms = keyword_search_terms(movie.keywords)
    feed_keyword_terms = keyword_search_terms(analysis.feed.keywords)
    return {
        "intent_scope": analysis.intent_scope,
        "media_type": media_type,
        "keywords": keyword_terms,
        "themes": list(movie.themes),
        "moods": list(movie.moods),
        "movie_filters": {
            "genres": list(movie.genres),
            "themes": list(movie.themes),
            "moods": list(movie.moods),
            "keywords": keyword_terms,
            "person_names": list(movie.person_names),
            "person_jobs": list(movie.person_jobs),
            "country": movie.country,
            "min_year": movie.min_year,
            "max_year": movie.max_year,
        },
        "feed_filters": {
            "categories": list(analysis.feed.categories),
            "emotions": list(analysis.feed.emotions),
            "keywords": feed_keyword_terms,
            "sentiment": analysis.feed.sentiment,
            "contains_spoiler": analysis.feed.contains_spoiler,
            "related_movie_title": analysis.feed.related_movie_title,
        },
        "direct_reply_hint": analysis.direct_reply_hint,
    }


def analyze_query(state: ChatState, deps: ChatGraphDependencies) -> ChatState:
    query = state.get("query", "")
    analysis = deps.query_analyzer.analyze(
        query, user_id=state.get("user_id")
    )
    return _analysis_to_state(analysis)


# 하위 호환 alias
plan_intent = analyze_query


__all__ = ["analyze_query", "plan_intent"]
