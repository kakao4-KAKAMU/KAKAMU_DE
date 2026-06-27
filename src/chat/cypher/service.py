"""GraphCypherQAChain 기반 Cypher 생성·검증·실행.

SOLID
-----
- SRP : Cypher 생성(cypher_generation_chain), 보정(CypherQueryCorrector),
  검증(CyVer), 실행(Neo4jClient) 파이프라인만 담당.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Optional

from CyVer import PropertiesValidator, SchemaValidator, SyntaxValidator
from langchain_core.language_models import BaseLanguageModel
from langchain_neo4j import GraphCypherQAChain, Neo4jGraph
from src.api.security.limits import DEFAULT_MAX_CYPHER_QUESTION_LENGTH
from src.chat.cypher.sanitize import sanitize_and_extract_cypher
from src.chat.cypher.security import validate_cypher_security
from src.config.settings import Neo4jSettings
from src.graph.client import Neo4jClient

logger = logging.getLogger(__name__)

# Cypher 생성 프롬프트에 포함할 도메인 노드 (User/Persona 제외)
_DOMAIN_NODE_TYPES: list[str] = [
    "Movie",
    "Feed",
    "Comment",
    "Genre",
    "Theme",
    "Mood",
    "Keyword",
    "Category",
    "Emotion",
    "Person",
    "Country",
]

_EXCLUDED_NODE_TYPES: list[str] = ["User", "Persona"]

# GraphCypherQAChain CYPHER_GENERATION_PROMPT 의 {examples} 슬롯용 few-shot.
_DEFAULT_CYPHER_EXAMPLES: str = """\
# 잔잔한 무드의 영화 10편은?
MATCH (m:Movie)-[:HAS_MOOD]->(md:Mood)
WHERE md.name = '잔잔한'
RETURN m.movie_id AS movie_id, m.title AS title
LIMIT 10

# '기생충'과 같은 장르 영화는?
MATCH (seed:Movie {title: '기생충'})-[:HAS_GENRE]->(g:Genre)<-[:HAS_GENRE]-(m:Movie)
WHERE m.movie_id <> seed.movie_id
RETURN m.movie_id AS movie_id, m.title AS title
LIMIT 10

# '봉준호' 감독 영화 목록은?
MATCH (m:Movie)-[hp:HAS_PERSON]->(p:Person)
WHERE hp.job STARTS WITH '감독' AND p.name = '봉준호'
RETURN m.movie_id AS movie_id, m.title AS title
LIMIT 10

# '마동석' 배우 영화 목록은?
MATCH (m:Movie)-[hp:HAS_PERSON]->(p:Person)
WHERE hp.job STARTS WITH '배우' AND p.name = '마동석'
RETURN m.movie_id AS movie_id, m.title AS title
LIMIT 10

# '박지훈' 나온 영화 목록은?
MATCH (m:Movie)-[hp:HAS_PERSON]->(p:Person)
WHERE p.name = '박지훈'
RETURN m.movie_id AS movie_id, m.title AS title
LIMIT 10

# '기생충' 관련 감상 피드는?
MATCH (f:Feed)-[:ABOUT_MOVIE]->(m:Movie)
WHERE m.title = '기생충'
RETURN f.feed_id AS feed_id, f.summary AS summary
LIMIT 10

# '최신' 영화는?
MATCH (m:Movie)
RETURN m.movie_id AS movie_id, m.title AS title
ORDER BY m.producing_year DESC
LIMIT 10
"""


@dataclass(frozen=True)
class CypherExecutionResult:
    """Cypher 파이프라인 실행 결과."""

    valid: bool
    cypher: str = ""
    rows: list[dict[str, Any]] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


class Neo4jCypherService:
    """Cypher 생성·검증·read-only 실행 서비스."""

    def __init__(
        self,
        neo4j_graph: Neo4jGraph,
        neo4j_client: Neo4jClient,
        cypher_llm: BaseLanguageModel,
        *,
        settings: Optional[Neo4jSettings] = None,
        top_k: int = 20,
        include_types: Optional[list[str]] = None,
        exclude_types: Optional[list[str]] = None,
        cypher_examples: Optional[str] = None,
    ) -> None:
        self._neo4j_client = neo4j_client
        self._settings = settings or neo4j_client._settings  # noqa: SLF001
        self._top_k = top_k
        self._database_name = self._settings.database
        self._cypher_examples = (
            cypher_examples if cypher_examples is not None else _DEFAULT_CYPHER_EXAMPLES
        )

        use_include = include_types if include_types is not None else _DOMAIN_NODE_TYPES

        chain_kwargs: dict[str, Any] = {
            "cypher_llm": cypher_llm,
            "qa_llm": cypher_llm,
            "graph": neo4j_graph,
            "validate_cypher": True,
            "top_k": top_k,
            "allow_dangerous_requests": False,
        }
        if use_include:
            chain_kwargs["include_types"] = use_include
        elif exclude_types is not None:
            chain_kwargs["exclude_types"] = exclude_types
        else:
            chain_kwargs["exclude_types"] = _EXCLUDED_NODE_TYPES

        self._chain = GraphCypherQAChain.from_llm(**chain_kwargs)

        driver = neo4j_client.driver
        self._syntax_validator = SyntaxValidator(driver)
        self._schema_validator = SchemaValidator(driver)
        self._properties_validator = PropertiesValidator(driver)

    def query(self, question: str) -> CypherExecutionResult:
        """자연어 질문 → Cypher 생성·검증·실행."""
        if len(question) > DEFAULT_MAX_CYPHER_QUESTION_LENGTH:
            return CypherExecutionResult(
                valid=False,
                errors=[
                    f"security: question exceeds max length ({DEFAULT_MAX_CYPHER_QUESTION_LENGTH})"
                ],
            )

        try:
            raw = self._chain.cypher_generation_chain.invoke(
                {
                    "question": question,
                    "schema": self._chain.graph_schema,
                    "examples": self._cypher_examples,
                }
            )
        except Exception as exc:
            logger.exception("Cypher generation failed")
            return CypherExecutionResult(valid=False, errors=[f"generation_failed: {exc}"])

        cypher = sanitize_and_extract_cypher(str(raw))
        if not cypher:
            return CypherExecutionResult(
                valid=False,
                errors=["generation_failed: empty cypher"],
            )

        if self._chain.cypher_query_corrector is not None:
            cypher = self._chain.cypher_query_corrector(cypher)

        validation_errors = self._validate_cypher(cypher)
        if validation_errors:
            return CypherExecutionResult(
                valid=False,
                cypher=cypher,
                errors=validation_errors,
            )

        try:
            rows = self._neo4j_client.execute_read(cypher)[: self._top_k]
        except Exception as exc:
            logger.warning("Cypher execution failed: %s", exc)
            return CypherExecutionResult(
                valid=False,
                cypher=cypher,
                errors=[f"execution_failed: {exc}"],
            )

        return CypherExecutionResult(valid=True, cypher=cypher, rows=rows)

    def _validate_cypher(self, cypher: str) -> list[str]:
        errors: list[str] = list(validate_cypher_security(cypher))

        is_valid, syntax_meta = self._syntax_validator.validate(
            cypher, database_name=self._database_name
        )
        if not is_valid:
            errors.append(f"syntax: {syntax_meta}")

        schema_score, schema_meta = self._schema_validator.validate(
            cypher, database_name=self._database_name
        )
        if schema_score != 1:
            errors.append(f"schema (score={schema_score}): {schema_meta}")

        prop_score, prop_meta = self._properties_validator.validate(
            cypher, database_name=self._database_name
        )
        if prop_score is not None and prop_score != 1:
            errors.append(f"properties (score={prop_score}): {prop_meta}")

        return errors


__all__ = ["CypherExecutionResult", "Neo4jCypherService"]
