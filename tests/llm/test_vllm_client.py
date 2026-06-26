"""vLLM response_format 정규화 회귀 테스트."""

from __future__ import annotations

from src.llm.vllm_client import normalize_response_format
from src.ontology.schema import MoviePlotOntology, build_llm_json_schema


def test_normalize_legacy_inner_json_schema_key() -> None:
    legacy_wrapper = {
        "name": "movie_knowledge_ontology",
        "strict": True,
        "json_schema": {"type": "object", "properties": {"title": {"type": "string"}}},
    }
    normalized = normalize_response_format(
        {"type": "json_schema", "json_schema": legacy_wrapper},
    )
    inner = normalized["json_schema"]
    assert inner["name"] == "movie_knowledge_ontology"
    assert inner["strict"] is True
    assert "json_schema" not in inner
    assert inner["schema"]["type"] == "object"


def test_normalize_flat_response_format() -> None:
    wrapper = build_llm_json_schema(MoviePlotOntology, name="movie_knowledge_ontology")
    normalized = normalize_response_format({"type": "json_schema", **wrapper})
    inner = normalized["json_schema"]
    assert inner["name"] == "movie_knowledge_ontology"
    assert "schema" in inner
    assert "json_schema" not in inner


def test_normalize_bare_wrapper() -> None:
    wrapper = build_llm_json_schema(MoviePlotOntology, name="movie_knowledge_ontology")
    normalized = normalize_response_format(wrapper)
    assert normalized["type"] == "json_schema"
    assert normalized["json_schema"]["schema"]["type"] == "object"
