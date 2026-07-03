"""Cypher 보안 검증 단위 테스트."""

from __future__ import annotations

from src.chat.cypher.security import validate_cypher_security


def test_blocks_write_keywords() -> None:
    errors = validate_cypher_security("CREATE (m:Movie) RETURN m")
    assert any("write/mutation" in err for err in errors)


def test_blocks_procedure_call() -> None:
    errors = validate_cypher_security("CALL apoc.load.json('file:///etc/passwd') YIELD value RETURN value")
    assert any("procedure CALL" in err or "forbidden procedure" in err for err in errors)


def test_blocks_user_persona_labels() -> None:
    errors = validate_cypher_security("MATCH (u:User {user_id: 'x'}) RETURN u")
    assert any("User/Persona" in err for err in errors)


def test_allows_call_subquery() -> None:
    cypher = """
    CALL {
      MATCH (m:Movie) RETURN m LIMIT 1
    }
    RETURN m
    """
    errors = validate_cypher_security(cypher)
    assert not any("procedure CALL" in err for err in errors)


def test_allows_fulltext_query_nodes_procedure() -> None:
    cypher = """
    call db.index.fulltext.queryNodes('movie_title_text_ft', '기생충')
    YIELD node AS mt, score
    MATCH (m:Movie)-[:HAS_TITLE]->(mt)
    RETURN m.movie_id AS movie_id
    LIMIT 10
    """
    errors = validate_cypher_security(cypher)
    assert errors == []


def test_blocks_non_fulltext_procedure_call() -> None:
    errors = validate_cypher_security("CALL db.labels() YIELD label RETURN label")
    assert any("procedure CALL" in err for err in errors)
