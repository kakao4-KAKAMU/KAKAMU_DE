"""Cypher sanitize 단위 테스트."""

from __future__ import annotations

from src.chat.cypher.sanitize import sanitize_and_extract_cypher

_BACKTICK = "`"

_PARK_JIHOON_SAMPLE = """<think>
Okay, let's tackle this query. The user wants the latest movies where Park Ji-hoon has acted.
</think>

MATCH (m:Movie)-[hp:HAS_PERSON]->(p:Person)
WHERE p.name = '박지훈'
RETURN m.movie_id AS movie_id, m.title AS title
ORDER BY m.updated_at DESC
LIMIT 10"""


def test_strips_qwen_think_block() -> None:
    raw = (
        f"{_BACKTICK * 3}think\n"
        "reasoning here\n"
        f"{_BACKTICK * 3}\n\n"
        "MATCH (m:Movie) RETURN m.movie_id AS movie_id LIMIT 5"
    )
    cypher = sanitize_and_extract_cypher(raw)
    assert cypher == "MATCH (m:Movie) RETURN m.movie_id AS movie_id LIMIT 5"


def test_strips_redacted_thinking_block() -> None:
    cypher = sanitize_and_extract_cypher(_PARK_JIHOON_SAMPLE)
    assert cypher.startswith("MATCH (m:Movie)")
    assert "redacted_thinking" not in cypher
    assert "박지훈" in cypher
    assert cypher.endswith("LIMIT 10")


def test_extracts_from_code_fence() -> None:
    raw = """```cypher
MATCH (m:Movie) RETURN m.title AS title LIMIT 3
```"""
    assert sanitize_and_extract_cypher(raw) == "MATCH (m:Movie) RETURN m.title AS title LIMIT 3"


def test_strips_mid_query_semicolon_before_return() -> None:
    raw = """CALL db.index.fulltext.queryNodes('movie_title_text_ft', '기생충')
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
RETURN f.feed_id AS feed_id, f.summary AS summary, similarityScore
ORDER BY similarityScore DESC;"""
    cypher = sanitize_and_extract_cypher(raw)
    assert "RETURN f.feed_id AS feed_id, f.summary AS summary, similarityScore" in cypher
    assert cypher == raw
