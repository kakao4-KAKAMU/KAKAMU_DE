"""Neo4j Cypher 서비스 단위 테스트."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from src.chat.cypher.service import Neo4jCypherService


def _service_with_mocks(
    *,
    generated: str = "MATCH (m:Movie) RETURN m",
    corrector_output: str | None = None,
    syntax_valid: bool = True,
    schema_score: float = 1.0,
    prop_score: float | None = 1.0,
    rows: list | None = None,
) -> tuple[Neo4jCypherService, MagicMock]:
    neo4j_graph = MagicMock()
    neo4j_client = MagicMock()
    neo4j_client._settings.database = "neo4j"
    neo4j_client.driver = MagicMock()
    neo4j_client.execute_read.return_value = rows or [{"movie_id": "m1"}]

    cypher_llm = MagicMock()
    chain = MagicMock()
    chain.cypher_generation_chain.invoke.return_value = generated
    chain.graph_schema = "Movie {title: STRING}"
    chain.cypher_query_corrector = MagicMock(
        side_effect=lambda q: corrector_output if corrector_output is not None else q
    )

    syntax_validator = MagicMock()
    syntax_validator.validate.return_value = (syntax_valid, "syntax-meta")
    schema_validator = MagicMock()
    schema_validator.validate.return_value = (schema_score, "schema-meta")
    properties_validator = MagicMock()
    properties_validator.validate.return_value = (prop_score, "prop-meta")

    with (
        patch(
            "src.chat.cypher.service.GraphCypherQAChain.from_llm",
            return_value=chain,
        ),
        patch("src.chat.cypher.service.SyntaxValidator", return_value=syntax_validator),
        patch("src.chat.cypher.service.SchemaValidator", return_value=schema_validator),
        patch(
            "src.chat.cypher.service.PropertiesValidator",
            return_value=properties_validator,
        ),
    ):
        service = Neo4jCypherService(
            neo4j_graph,
            neo4j_client,
            cypher_llm,
        )

    return service, neo4j_client


def test_query_strips_redacted_thinking_from_llm_output() -> None:
    service, neo4j_client = _service_with_mocks(
        generated=_PARK_JIHOON_LLM_OUTPUT,
        rows=[{"movie_id": "m1", "title": "영화1"}],
    )
    result = service.query("박지훈 최신 영화")
    assert result.valid is True
    assert result.cypher.startswith("MATCH (m:Movie)")
    assert "redacted_thinking" not in result.cypher
    neo4j_client.execute_read.assert_called_once()


_PARK_JIHOON_LLM_OUTPUT = """<think>
thinking content
</think>

MATCH (m:Movie)-[hp:HAS_PERSON]->(p:Person)
WHERE p.name = '박지훈'
RETURN m.movie_id AS movie_id, m.title AS title
ORDER BY m.updated_at DESC
LIMIT 10"""


def test_query_passes_examples_to_generation_chain() -> None:
    service, _ = _service_with_mocks()
    service.query("잔잔한 영화 추천")
    invoke_args = service._chain.cypher_generation_chain.invoke.call_args.args[0]
    assert "examples" in invoke_args
    assert invoke_args["examples"]
    assert "HAS_MOOD" in invoke_args["examples"]


def test_query_success_returns_rows() -> None:
    service, neo4j_client = _service_with_mocks(
        generated="```cypher\nMATCH (m:Movie) RETURN m.movie_id AS movie_id\n```",
        rows=[{"movie_id": "m1"}],
    )
    result = service.query("잔잔한 영화 추천")
    assert result.valid is True
    assert result.cypher == "MATCH (m:Movie) RETURN m.movie_id AS movie_id"
    assert result.rows == [{"movie_id": "m1"}]
    neo4j_client.execute_read.assert_called_once()


def test_query_blocks_write_keywords() -> None:
    service, neo4j_client = _service_with_mocks(
        generated="CREATE (m:Movie {title: 'x'}) RETURN m",
    )
    result = service.query("영화 추가")
    assert result.valid is False
    assert any("security" in err for err in result.errors)
    neo4j_client.execute_read.assert_not_called()


def test_query_fails_on_syntax_validation() -> None:
    service, neo4j_client = _service_with_mocks(
        generated="MATCH (m:Movie) RETURN m",
        syntax_valid=False,
    )
    result = service.query("영화")
    assert result.valid is False
    assert any("syntax" in err for err in result.errors)
    neo4j_client.execute_read.assert_not_called()


def test_query_fails_on_schema_validation() -> None:
    service, neo4j_client = _service_with_mocks(
        generated="MATCH (m:Movie) RETURN m",
        schema_score=0.5,
    )
    result = service.query("영화")
    assert result.valid is False
    assert any("schema" in err for err in result.errors)
    neo4j_client.execute_read.assert_not_called()


def test_query_applies_cypher_query_corrector() -> None:
    service, neo4j_client = _service_with_mocks(
        generated="MATCH (m:Movie)-[:HAS_GENRE]->(g:Genre) RETURN m",
        corrector_output="MATCH (g:Genre)<-[:HAS_GENRE]-(m:Movie) RETURN m",
    )
    result = service.query("장르 영화")
    assert result.valid is True
    neo4j_client.execute_read.assert_called_once_with(
        "MATCH (g:Genre)<-[:HAS_GENRE]-(m:Movie) RETURN m"
    )
    assert result.cypher == "MATCH (g:Genre)<-[:HAS_GENRE]-(m:Movie) RETURN m"
