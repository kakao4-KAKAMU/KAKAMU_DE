"""Neo4j 지식그래프 Cypher 조회 tool."""

from __future__ import annotations

import json
from typing import Any

from langchain_core.tools import BaseTool, StructuredTool

from src.chat.cypher.service import Neo4jCypherService


def _format_tool_response(result: Any) -> str:
    if result.valid:
        payload = {
            "status": "ok",
            "cypher": result.cypher,
            "rows": result.rows,
        }
    else:
        payload = {
            "status": "validation_failed",
            "cypher": result.cypher,
            "errors": result.errors,
        }
    return json.dumps(payload, ensure_ascii=False, default=str)


def build_neo4j_tools(cypher_service: Neo4jCypherService) -> list[BaseTool]:
    """Neo4j Cypher 조회 tool 목록을 생성한다."""

    def query_neo4j_graph(question: str) -> str:
        """Neo4j 지식그래프에서 영화/피드/인물/장르 등을 조회할 때 사용한다.

        검증 실패(status=validation_failed) 시 errors 필드를 읽고
        질문 또는 Cypher 조건을 수정한 뒤 재호출한다.
        """
        return _format_tool_response(cypher_service.query(question))

    return [
        StructuredTool.from_function(
            func=query_neo4j_graph,
            name="query_neo4j_graph",
            description=(
                "Neo4j knowledge graph에서 영화, 피드, 인물, 장르, 테마, "
                "무드 등을 조회할 때 사용한다. READ-ONLY MATCH/RETURN 쿼리만 실행된다."
            ),
        )
    ]


__all__ = ["build_neo4j_tools"]
