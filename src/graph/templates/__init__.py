"""기본 Cypher 템플릿 등록."""

from __future__ import annotations

from src.graph.cypher_statements import (
    HYBRID_FEED_RECOMMEND_WEIGHTED,
    HYBRID_MOVIE_RECOMMEND_WEIGHTED,
)
from src.graph.template_registry import CypherTemplate, TemplateRegistry

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
    return registry


__all__ = ["build_default_registry"]
