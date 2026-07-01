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
from datetime import datetime
from CyVer import PropertiesValidator, SchemaValidator, SyntaxValidator
from langchain_core.language_models import BaseLanguageModel
from langchain_neo4j import GraphCypherQAChain, Neo4jGraph
from src.config.limits import DEFAULT_MAX_CYPHER_QUESTION_LENGTH
from src.chat.cypher.sanitize import sanitize_and_extract_cypher
from src.chat.cypher.security import validate_cypher_security
from src.config.settings import Neo4jSettings
from src.graph.client import Neo4jClient
from src.graph.cypher_statements.properties import (
    BASE_PLOT_EMBEDDING,
    BASE_SUMMARY_EMBEDDING,
)
from src.graph.cypher_statements.schema import FULLTEXT_INDEXES, NODE_PROPERTY_INDEXES
from src.ontology.prompts.schema_vocab import build_cypher_analysis_knowledge

logger = logging.getLogger(__name__)

# Cypher 생성 프롬프트에 포함할 도메인 노드 (User/Persona 제외)
_DOMAIN_NODE_TYPES: list[str] = [
    "Movie",
    "MovieTitle",
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

# 영화 목록 조회 시 공통 RETURN 컬럼
_MOVIE_RETURN = (
    "m.movie_id AS movie_id, m.producing_year AS producing_year, "
    "m.country AS country, m.title AS title"
)

_FULLTEXT_INDEX_RE = re.compile(
    r"CREATE FULLTEXT INDEX (\S+).*?FOR \(\w+:(\w+)\) ON EACH \[([^\]]+)\]",
    re.DOTALL | re.IGNORECASE,
)
_PROPERTY_INDEX_RE = re.compile(
    r"CREATE INDEX (\S+).*?FOR \(\w+:(\w+)\)\s+ON \(([^)]+)\)",
    re.IGNORECASE,
)


def _build_cypher_index_knowledge() -> str:
    """schema.py 기반 Neo4j index catalog — graph_schema 슬롯용."""
    lines = [
        "## Neo4j Index Catalog",
        "",
        "### Full-text (CALL db.index.fulltext.queryNodes('<index>', '<query>') YIELD node, score)",
        "",
    ]
    for stmt in FULLTEXT_INDEXES:
        match = _FULLTEXT_INDEX_RE.search(stmt)
        if match:
            name, label, props = match.groups()
            prop_list = ", ".join(p.strip() for p in props.split(","))
            lines.append(f"- `{name}` → `:{label}` [{prop_list}] (CJK analyzer)")

    lines.extend(
        [
            "",
            "### Range property indexes",
            "",
        ]
    )
    for stmt in NODE_PROPERTY_INDEXES:
        match = _PROPERTY_INDEX_RE.search(stmt)
        if match:
            name, label, props = match.groups()
            prop_list = ", ".join(p.strip() for p in props.split(","))
            lines.append(f"- `{name}` → `:{label}` ({prop_list})")

    lines.extend(
        [
            "",
            "### Vector (MATCH … SEARCH … VECTOR INDEX … FOR … LIMIT … [SCORE AS …])",
            "",
            f"- `movie_plot_vec` → `:Movie` (`{BASE_PLOT_EMBEDDING}`, cosine) — 줄거리 의미 유사도",
            f"- `feed_summary_vec` → `:Feed` (`{BASE_SUMMARY_EMBEDDING}`, cosine) — 피드 요약 의미 유사도",
            f"- `comment_summary_vec` → `:Comment` (`{BASE_SUMMARY_EMBEDDING}`, cosine) — 댓글 요약 의미 유사도",
            "- 버전별 index/property: `movie_plot_vec_v*`, `plot_embedding_v*` / `feed_summary_vec_v*`, `summary_embedding_v*`",
            "",
            "### Search rules",
            "",
            "- `CALL db.index.fulltext.queryNodes` 사용 가능.",
            "- Person 검색: `(m:Movie)-[hp:HAS_PERSON]->(p:Person)` 에 반드시",
            "  `p.kmdb_person_id IS NOT NULL` 과 `hp.job STARTS WITH '감독'` 또는 `hp.job STARTS WITH '출연'` 포함.",
            "- 영화 제목 검색은 `MovieTitle` full-text index `movie_title_text_ft` 우선.",
            f"- 줄거리/피드 의미 검색: vector index + `SEARCH` 절. query vector 는 seed node 의 `{BASE_PLOT_EMBEDDING}` / `{BASE_SUMMARY_EMBEDDING}` 또는 literal/parameter.",
            "- vector score 는 full-text score 와 직접 비교하지 말 것.",
        ]
    )
    return "\n".join(lines)


# GraphCypherQAChain CYPHER_GENERATION_PROMPT 의 {examples} 슬롯용 few-shot.
_DEFAULT_CYPHER_EXAMPLES: str = """\
{analysis_knowledge}

# Cypher 작성 규칙
- read-only: MATCH / RETURN / WITH / CALL {{ … }} / CALL db.index.fulltext.queryNodes / SEARCH 만 사용.
- 영화 목록 RETURN: movie_id, producing_year, country, title. 기본 LIMIT 10.
- Person: `p.kmdb_person_id IS NOT NULL` + `hp.job STARTS WITH '감독'|'출연'` (역할에 맞게 하나).
- 제목·인명·키워드는 아래 full-text index 이름을 그대로 사용.

# Cypher 예시

## 무드 — '긴장감 넘치는' 영화
MATCH (m:Movie)-[:HAS_MOOD]->(md:Mood {{name: 'suspenseful'}})
RETURN {_movie_return}
ORDER BY m.producing_year DESC LIMIT 10;

## 테마 — '복수' 영화
MATCH (m:Movie)-[:HAS_THEME]->(t:Theme {{name: 'revenge'}})
RETURN {_movie_return}
ORDER BY m.producing_year DESC LIMIT 10;

## 장르 — '액션' 영화
MATCH (m:Movie)-[:HAS_GENRE]->(g:Genre {{name: '액션'}})
RETURN {_movie_return}
ORDER BY m.producing_year DESC LIMIT 10;

## 제목 full-text — '기생충' 영화
CALL db.index.fulltext.queryNodes('movie_title_text_ft', '기생충')
YIELD node AS mt, score
MATCH (m:Movie)-[:HAS_TITLE]->(mt)
RETURN {_movie_return}
ORDER BY score DESC LIMIT 10;

## 같은 장르 — '기생충'과 유사
CALL db.index.fulltext.queryNodes('movie_title_text_ft', '기생충')
YIELD node AS mt, score
MATCH (seed:Movie)-[:HAS_TITLE]->(mt)
WITH seed ORDER BY score DESC LIMIT 1
MATCH (seed)-[:HAS_GENRE]->(g:Genre)<-[:HAS_GENRE]-(m:Movie)
WHERE m.movie_id <> seed.movie_id
RETURN {_movie_return}
ORDER BY m.producing_year DESC LIMIT 10;

## 감독 — '봉준호' filmography
CALL db.index.fulltext.queryNodes('person_name_ft', '봉준호')
YIELD node AS p, score
MATCH (m:Movie)-[hp:HAS_PERSON]->(p)
WHERE p.kmdb_person_id IS NOT NULL AND hp.job STARTS WITH '감독'
RETURN {_movie_return}
ORDER BY score DESC LIMIT 10;

## 출연 — '박지훈' filmography
CALL db.index.fulltext.queryNodes('person_name_ft', '박지훈')
YIELD node AS p, score
MATCH (m:Movie)-[hp:HAS_PERSON]->(p)
WHERE p.kmdb_person_id IS NOT NULL AND hp.job STARTS WITH '출연'
RETURN {_movie_return}
ORDER BY score DESC LIMIT 10;

## 최신 — 최근 1년 영화
MATCH (m:Movie)
WHERE m.producing_year >= toInteger(format(date() - Duration({{years: 1}}), 'yyyy'))
RETURN {_movie_return}
ORDER BY m.producing_year DESC LIMIT 10;

## 피드 — '기생충' 관련 감상
CALL db.index.fulltext.queryNodes('movie_title_text_ft', '기생충')
YIELD node AS mt, score
MATCH (m:Movie)-[:HAS_TITLE]->(mt)
WITH m ORDER BY score DESC LIMIT 1
MATCH (f:Feed)-[:ABOUT_MOVIE]->(m)
RETURN f.feed_id AS feed_id, f.summary AS summary
ORDER BY f.created_at DESC LIMIT 10;

## 키워드 — '왕' 언급 영화
CALL db.index.fulltext.queryNodes('keyword_text_ft', '왕')
YIELD node AS k, score
MATCH (m:Movie)-[:MENTIONS]->(k)
RETURN {_movie_return}
ORDER BY score DESC LIMIT 10;

## vector — '기생충'과 줄거리 유사 영화
CALL db.index.fulltext.queryNodes('movie_title_text_ft', '기생충')
YIELD node AS mt, score
MATCH (seed:Movie)-[:HAS_TITLE]->(mt)
WITH seed ORDER BY score DESC LIMIT 1
MATCH (m:Movie)
  SEARCH m IN (
    VECTOR INDEX movie_plot_vec
    FOR seed.plot_embedding
    LIMIT 10
  ) SCORE AS similarityScore
WHERE m.movie_id <> seed.movie_id AND seed.plot_embedding IS NOT NULL
RETURN {_movie_return}
ORDER BY similarityScore DESC;

## vector — seed 영화 피드와 요약 유사 피드
CALL db.index.fulltext.queryNodes('movie_title_text_ft', '기생충')
YIELD node AS mt, score
MATCH (m:Movie)-[:HAS_TITLE]->(mt)
WITH m ORDER BY score DESC LIMIT 1
MATCH (seedFeed:Feed)-[:ABOUT_MOVIE]->(m)
WITH seedFeed ORDER BY seedFeed.created_at DESC LIMIT 1
MATCH (f:Feed)
  SEARCH f IN (
    VECTOR INDEX feed_summary_vec
    FOR seedFeed.summary_embedding
    LIMIT 10
  ) SCORE AS similarityScore
WHERE f.feed_id <> seedFeed.feed_id AND seedFeed.summary_embedding IS NOT NULL
RETURN f.feed_id AS feed_id, f.summary AS summary
ORDER BY similarityScore DESC;

"""


def _build_default_cypher_examples() -> str:
    """Cypher few-shot 프롬프트에 ontology 분석 지식을 주입한다."""
    return _DEFAULT_CYPHER_EXAMPLES.format(
        analysis_knowledge=build_cypher_analysis_knowledge(),
        _movie_return=_MOVIE_RETURN,
    )


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
            cypher_examples if cypher_examples is not None else _build_default_cypher_examples()
        )

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
        self._chain.graph_schema += "\n" + _build_cypher_index_knowledge()

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
            now = datetime.now()
            raw = self._chain.cypher_generation_chain.invoke(
                {
                    "question": (
                        question
                        + f"\nCurrent Date: {now.year}-{now.month:02d}-{now.day:02d}"
                        f"\n오늘 날짜는 {now.year}년 {now.month}월 {now.day}일"
                    ),
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

        # ----- when add CALL db.index.fulltext.queryNodes, the cypher is not corrected by the corrector
        # if self._chain.cypher_query_corrector is not None:
        #     cypher = self._chain.cypher_query_corrector(cypher)

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
