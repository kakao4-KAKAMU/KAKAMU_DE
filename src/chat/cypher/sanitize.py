"""LLM Cypher 출력 정제 (thinking 블록·코드펜스 제거)."""

from __future__ import annotations

import re

from neo4j_graphrag.retrievers.text2cypher import extract_cypher

_BACKTICK = "`"
_QWEN_THINK_OPEN = f"{_BACKTICK * 3}think\n"
_QWEN_THINK_CLOSE = _BACKTICK * 3

_REASONING_BLOCK_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(
        re.escape(_QWEN_THINK_OPEN) + r".*?" + re.escape(_QWEN_THINK_CLOSE),
        re.IGNORECASE | re.DOTALL,
    ),
    re.compile(r"<think>.*?</think>", re.IGNORECASE | re.DOTALL),
    re.compile(r"<think(?:ing)?>.*?</think(?:ing)?>", re.IGNORECASE | re.DOTALL),
)

_CYPHER_STATEMENT_START = re.compile(
    r"(?im)^\s*(MATCH|OPTIONAL\s+MATCH|WITH|CALL\s+\{|CALL\s+db\.index\.fulltext\.queryNodes)\b",
)

# Neo4j는 ';'를 문장 종료로 해석한다. WHERE ... ;\nRETURN 형태는 MATCH만 실행되어 실패한다.
_MID_QUERY_SEMICOLON = re.compile(
    r";\s*(?=\n\s*(?:RETURN|WITH|MATCH|OPTIONAL|ORDER|LIMIT|UNION|CALL|WHERE)\b)",
    re.IGNORECASE,
)


def strip_reasoning_blocks(text: str) -> str:
    """thinking/redacted 블록을 제거하고 본문 텍스트만 반환한다."""
    cleaned = text
    for pattern in _REASONING_BLOCK_PATTERNS:
        cleaned = pattern.sub("", cleaned)
    return cleaned.strip()


def _extract_from_first_cypher_keyword(text: str) -> str:
    match = _CYPHER_STATEMENT_START.search(text)
    if match is None:
        return text.strip()
    return text[match.start() :].strip()


def sanitize_and_extract_cypher(raw: str) -> str:
    """thinking/설명 텍스트를 제거하고 실행 가능한 Cypher만 반환한다."""
    text = strip_reasoning_blocks(str(raw).strip())
    text = extract_cypher(text).strip()
    text = _MID_QUERY_SEMICOLON.sub("\n", text)
    if _CYPHER_STATEMENT_START.search(text):
        text = _extract_from_first_cypher_keyword(text)
    return text.strip()


__all__ = ["sanitize_and_extract_cypher", "strip_reasoning_blocks"]
