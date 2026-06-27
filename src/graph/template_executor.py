"""템플릿 기반 Cypher 실행기."""

from __future__ import annotations

import logging
from typing import Any, Mapping

from src.graph.client import Neo4jClient
from src.graph.template_registry import TemplateRegistry, TemplateValidationError

logger = logging.getLogger(__name__)

DEFAULT_TEMPLATE_ID = "hybrid_recommend"


class TemplateExecutor:
    def __init__(self, registry: TemplateRegistry, neo4j: Neo4jClient) -> None:
        self._registry = registry
        self._neo4j = neo4j

    def execute(
        self,
        template_id: str,
        params: Mapping[str, Any],
        *,
        fallback: bool = True,
    ) -> list[dict[str, Any]]:
        try:
            tpl = self._registry.get(template_id)
            validated = self._registry.validate_params(template_id, params)
            return self._neo4j.execute_read(tpl.cypher.strip(), validated)
        except TemplateValidationError as exc:
            logger.warning("Template execution failed: %s", exc)
            if not fallback or template_id == DEFAULT_TEMPLATE_ID:
                raise
            logger.info("Falling back to %s", DEFAULT_TEMPLATE_ID)
            fallback_params = {
                "user_id": params.get("user_id", "anonymous"),
                "persona_id": params.get("persona_id"),
                "query_embedding": params.get("query_embedding", []),
                "query_keywords": params.get("query_keywords", []),
                "query_themes": params.get("query_themes", []),
                "query_moods": params.get("query_moods", []),
                "top_k": params.get("top_k", 20),
                "vec_top_k": params.get("vec_top_k", 50),
                "w_vec": 0.55,
                "w_kw": 0.15,
                "w_theme": 0.10,
                "w_mood": 0.05,
                "w_user": 0.15,
                "max_toxicity": params.get("max_toxicity", 0.7),
            }
            return self.execute(DEFAULT_TEMPLATE_ID, fallback_params, fallback=False)


__all__ = ["TemplateExecutor"]
