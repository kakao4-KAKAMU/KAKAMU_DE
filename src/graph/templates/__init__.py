"""기본 Cypher 템플릿 등록."""

from __future__ import annotations

from src.graph.cypher_statements import (
    CHAT_FEED_FILTER,
    CHAT_MOVIE_FILTER,
    HYBRID_FEED_RECOMMEND_WEIGHTED,
    HYBRID_MOVIE_RECOMMEND_WEIGHTED,
)
from src.graph.template_registry import CypherTemplate, TemplateRegistry

CHAT_MOVIE_FILTER_TEMPLATE_ID = "chat_movie_filter"
CHAT_FEED_FILTER_TEMPLATE_ID = "chat_feed_filter"

_HYBRID_BASE_PARAMS_SCHEMA: dict[str, str] = {
    "user_id": "string",
    "persona_id": "optional_string",
    "query_embedding": "float_list",
    "query_keywords": "string_list",
    "query_themes": "string_list",
    "query_moods": "string_list",
    "top_k": "int",
    "vec_top_k": "int",
    "w_vec": "float",
    "w_kw": "float",
    "w_theme": "float",
    "w_mood": "float",
    "w_user": "float",
    "max_toxicity": "float",
}

_CHAT_MOVIE_FILTER_PARAMS_SCHEMA: dict[str, str] = {
    **_HYBRID_BASE_PARAMS_SCHEMA,
    "query_genres": "string_list",
    "query_person_names": "string_list",
    # "query_person_jobs": "string_list",
    "filter_country": "string",
    "min_year": "int",
    "max_year": "int",
}

_CHAT_FEED_FILTER_PARAMS_SCHEMA: dict[str, str] = {
    **_HYBRID_BASE_PARAMS_SCHEMA,
    "query_categories": "string_list",
    "query_emotions": "string_list",
    "filter_sentiment": "string",
    "include_spoiler": "bool",
    "related_movie_title": "string",
}

FEED_ABOUT_MOVIE = """
MATCH (f:Feed)-[:ABOUT_MOVIE]->(m:Movie {movie_id: $movie_id})
WHERE ($include_spoiler = true OR f.contains_spoiler = false)
  AND coalesce(f.toxicity_score, 0.0) <= $max_toxicity
RETURN f.feed_id AS feed_id, f.summary AS summary, f.sentiment_score AS sentiment_score
ORDER BY f.created_at DESC
LIMIT $top_k
"""

SIMILAR_MOVIE_BY_THEME = """
MATCH (m:Movie {movie_id: $movie_id})-[:HAS_THEME]->(t:Theme)
MATCH (other:Movie)-[:HAS_THEME]->(t)
WHERE other.movie_id <> $movie_id
  AND coalesce(other.toxicity_score, 0.0) <= $max_toxicity
RETURN other.movie_id AS movie_id, other.title AS title, count(DISTINCT t) AS theme_overlap
ORDER BY theme_overlap DESC
LIMIT $top_k
"""

RECENT_FEEDS_POSITIVE = """
MATCH (f:Feed)
WHERE f.sentiment_score >= $min_sentiment
  AND ($include_spoiler = true OR f.contains_spoiler = false)
  AND coalesce(f.toxicity_score, 0.0) <= $max_toxicity
RETURN f.feed_id AS feed_id, f.summary AS summary, f.sentiment_score AS sentiment_score
ORDER BY f.created_at DESC
LIMIT $top_k
"""

USER_PREFERENCE_SUMMARY = """
MATCH (u:User {user_id: $user_id})-[p:PREFERS]->(x)
RETURN labels(x)[0] AS label, coalesce(x.name, x.normalized, x.tag) AS name, p.weight AS weight
ORDER BY p.weight DESC
LIMIT $top_k
"""


def build_default_registry() -> TemplateRegistry:
    registry = TemplateRegistry()

    registry.register(
        CypherTemplate(
            id="hybrid_recommend",
            cypher=HYBRID_MOVIE_RECOMMEND_WEIGHTED,
            params_schema=dict(_HYBRID_BASE_PARAMS_SCHEMA),
            max_limit=100,
            description="Hybrid semantic+keyword+preference movie recommendation",
        )
    )
    registry.register(
        CypherTemplate(
            id="hybrid_feed_recommend",
            cypher=HYBRID_FEED_RECOMMEND_WEIGHTED,
            params_schema=dict(_HYBRID_BASE_PARAMS_SCHEMA),
            max_limit=100,
            description="Hybrid semantic+keyword+preference feed recommendation",
        )
    )
    registry.register(
        CypherTemplate(
            id=CHAT_MOVIE_FILTER_TEMPLATE_ID,
            cypher=CHAT_MOVIE_FILTER,
            params_schema=dict(_CHAT_MOVIE_FILTER_PARAMS_SCHEMA),
            max_limit=100,
            description=(
                "Chat query ontology filter + hybrid movie recommendation "
                "(genre/person/country/year + semantic boost)"
            ),
        )
    )
    registry.register(
        CypherTemplate(
            id=CHAT_FEED_FILTER_TEMPLATE_ID,
            cypher=CHAT_FEED_FILTER,
            params_schema=dict(_CHAT_FEED_FILTER_PARAMS_SCHEMA),
            max_limit=100,
            description=(
                "Chat query ontology filter + hybrid feed recommendation "
                "(category/emotion/sentiment/spoiler/movie + semantic boost)"
            ),
        )
    )
    registry.register(
        CypherTemplate(
            id="feed_about_movie",
            cypher=FEED_ABOUT_MOVIE,
            params_schema={
                "movie_id": "string",
                "top_k": "int",
                "include_spoiler": "bool",
                "max_toxicity": "float",
            },
            max_limit=50,
        )
    )
    registry.register(
        CypherTemplate(
            id="similar_movie_by_theme",
            cypher=SIMILAR_MOVIE_BY_THEME,
            params_schema={
                "movie_id": "string",
                "top_k": "int",
                "max_toxicity": "float",
            },
            max_limit=50,
        )
    )
    registry.register(
        CypherTemplate(
            id="recent_feeds_positive",
            cypher=RECENT_FEEDS_POSITIVE,
            params_schema={
                "min_sentiment": "float",
                "top_k": "int",
                "include_spoiler": "bool",
                "max_toxicity": "float",
            },
            max_limit=50,
        )
    )
    registry.register(
        CypherTemplate(
            id="user_preference_summary",
            cypher=USER_PREFERENCE_SUMMARY,
            params_schema={"user_id": "string", "top_k": "int"},
            max_limit=50,
        )
    )
    return registry


__all__ = [
    "CHAT_FEED_FILTER_TEMPLATE_ID",
    "CHAT_MOVIE_FILTER_TEMPLATE_ID",
    "build_default_registry",
]
