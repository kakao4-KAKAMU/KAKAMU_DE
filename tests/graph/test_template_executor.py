from __future__ import annotations

from unittest.mock import MagicMock

from src.graph.template_executor import TemplateExecutor
from src.graph.template_registry import TemplateValidationError
from src.graph.templates import build_default_registry


def test_execute_with_fallback() -> None:
    neo4j = MagicMock()
    neo4j.execute_read.return_value = [{"movie_id": "m1"}]
    executor = TemplateExecutor(build_default_registry(), neo4j)

    result = executor.execute(
        "unknown_template",
        {
            "user_id": "u1",
            "query_embedding": [0.1],
            "query_keywords": [],
            "query_themes": [],
            "query_moods": [],
            "top_k": 5,
            "vec_top_k": 10,
        },
        fallback=True,
    )
    assert result == [{"movie_id": "m1"}]
    assert neo4j.execute_read.call_count == 1


def test_execute_intent() -> None:
    neo4j = MagicMock()
    neo4j.execute_read.return_value = []
    executor = TemplateExecutor(build_default_registry(), neo4j)
    executor.execute_intent(
        {
            "template_id": "feed_about_movie",
            "params": {
                "movie_id": "m1",
                "top_k": 3,
                "include_spoiler": False,
                "max_toxicity": 0.7,
            },
        }
    )
    neo4j.execute_read.assert_called_once()
