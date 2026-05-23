"""기본 Cypher 템플릿 등록."""

from __future__ import annotations

from src.graph.cypher_statements import HYBRID_MOVIE_RECOMMEND_WEIGHTED
from src.graph.template_registry import CypherTemplate, TemplateRegistry

FEED_ABOUT_MOVIE = """
MATCH (f:Feed)-[:ABOUT_MOVIE]->(m:Movie {movie_id: $movie_id})
WHERE f.contains_spoiler = false
RETURN f.feed_id AS feed_id, f.summary AS summary, f.sentiment_score AS sentiment_score
ORDER BY f.created_at DESC
LIMIT $top_k
"""

SIMILAR_MOVIE_BY_THEME = """
MATCH (m:Movie {movie_id: $movie_id})-[:HAS_THEME]->(t:Theme)
MATCH (other:Movie)-[:HAS_THEME]->(t)
WHERE other.movie_id <> $movie_id
RETURN other.movie_id AS movie_id, other.title AS title, count(DISTINCT t) AS theme_overlap
ORDER BY theme_overlap DESC
LIMIT $top_k
"""

RECENT_FEEDS_POSITIVE = """
MATCH (f:Feed)
WHERE f.sentiment_score >= $min_sentiment AND f.contains_spoiler = false
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
            params_schema={
                "user_id": "string",
                "query_embedding": "list",
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
            },
            max_limit=100,
            description="Hybrid semantic+keyword+preference movie recommendation",
        )
    )
    registry.register(
        CypherTemplate(
            id="feed_about_movie",
            cypher=FEED_ABOUT_MOVIE,
            params_schema={"movie_id": "string", "top_k": "int"},
            max_limit=50,
        )
    )
    registry.register(
        CypherTemplate(
            id="similar_movie_by_theme",
            cypher=SIMILAR_MOVIE_BY_THEME,
            params_schema={"movie_id": "string", "top_k": "int"},
            max_limit=50,
        )
    )
    registry.register(
        CypherTemplate(
            id="recent_feeds_positive",
            cypher=RECENT_FEEDS_POSITIVE,
            params_schema={"min_sentiment": "float", "top_k": "int"},
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


__all__ = ["build_default_registry"]
