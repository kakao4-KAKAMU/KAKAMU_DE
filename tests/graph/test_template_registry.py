from __future__ import annotations

import pytest

from src.graph.template_registry import (
    CypherTemplate,
    TemplateRegistry,
    TemplateValidationError,
)
from src.graph.templates import build_default_registry


def test_default_registry_has_six_templates() -> None:
    reg = build_default_registry()
    assert len(reg.list_ids()) == 6
    assert "hybrid_recommend" in reg.list_ids()
    assert "hybrid_feed_recommend" in reg.list_ids()


def test_rejects_write_operations() -> None:
    reg = TemplateRegistry()
    with pytest.raises(TemplateValidationError):
        reg.register(
            CypherTemplate(
                id="bad",
                cypher="CREATE (n:Node) RETURN n",
                read_only=True,
            )
        )


def test_validate_params_missing() -> None:
    reg = build_default_registry()
    with pytest.raises(TemplateValidationError):
        reg.validate_params("hybrid_recommend", {"user_id": "u1"})


def test_validate_params_ok() -> None:
    reg = build_default_registry()
    params = reg.validate_params(
        "hybrid_recommend",
        {
            "user_id": "u1",
            "persona_id": None,
            "query_embedding": [0.1, 0.2],
            "query_keywords": [],
            "query_themes": [],
            "query_moods": [],
            "top_k": 10,
            "vec_top_k": 20,
            "w_vec": 0.55,
            "w_kw": 0.15,
            "w_theme": 0.1,
            "w_mood": 0.05,
            "w_user": 0.15,
            "max_toxicity": 0.7,
        },
    )
    assert params["top_k"] == 10
    assert params["query_embedding"] == [0.1, 0.2]
    assert params["max_toxicity"] == 0.7


def test_validate_params_optional_string_null() -> None:
    reg = build_default_registry()
    params = reg.validate_params(
        "hybrid_recommend",
        {
            "user_id": "u1",
            "persona_id": None,
            "query_embedding": [0.1],
            "query_keywords": [],
            "query_themes": [],
            "query_moods": [],
            "top_k": 10,
            "vec_top_k": 20,
            "w_vec": 0.55,
            "w_kw": 0.15,
            "w_theme": 0.1,
            "w_mood": 0.05,
            "w_user": 0.15,
            "max_toxicity": 0.7,
        },
    )
    assert params["persona_id"] is None
