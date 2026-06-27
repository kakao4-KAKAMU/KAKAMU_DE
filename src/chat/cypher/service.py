"""GraphCypherQAChain 기반 Cypher 생성·검증·실행.

SOLID
-----
- SRP : Cypher 생성(cypher_generation_chain), 보정(CypherQueryCorrector),
  검증(CyVer), 실행(Neo4jClient) 파이프라인만 담당.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any, Optional

from CyVer import PropertiesValidator, SchemaValidator, SyntaxValidator
from langchain_core.language_models import BaseLanguageModel
from langchain_neo4j import GraphCypherQAChain, Neo4jGraph
from neo4j_graphrag.retrievers.text2cypher import extract_cypher

from src.config.settings import Neo4jSettings
from src.graph.client import Neo4jClient

logger = logging.getLogger(__name__)

_WRITE_KEYWORDS = re.compile(
    r"\b(CREATE|MERGE|DELETE|DETACH|SET|DROP|REMOVE|FOREACH|LOAD\s+CSV)\b",
    re.IGNORECASE,
)

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
    ) -> None:
        self._neo4j_client = neo4j_client
        self._settings = settings or neo4j_client._settings  # noqa: SLF001
        self._top_k = top_k
        self._database_name = self._settings.database

        use_include = include_types if include_types is not None else _DOMAIN_NODE_TYPES

        chain_kwargs: dict[str, Any] = {
            "cypher_llm": cypher_llm,
            "qa_llm": cypher_llm,
            "graph": neo4j_graph,
            "validate_cypher": True,
            "top_k": top_k,
            "allow_dangerous_requests": True,
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

    @property
    def graph_schema(self) -> str:
        return self._chain.graph_schema

    def query(self, question: str) -> CypherExecutionResult:
        """자연어 질문 → Cypher 생성·검증·실행."""
        try:
            raw = self._chain.cypher_generation_chain.invoke(
                {"question": question, "schema": self._chain.graph_schema}
            )
        except Exception as exc:
            logger.exception("Cypher generation failed")
            return CypherExecutionResult(valid=False, errors=[f"generation_failed: {exc}"])

        cypher = extract_cypher(str(raw)).strip()
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
        errors: list[str] = []

        if _WRITE_KEYWORDS.search(cypher):
            errors.append("security: write/mutation keywords are not allowed")

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
