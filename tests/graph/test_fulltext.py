from __future__ import annotations

from src.graph.fulltext import escape_fulltext_query


def test_escape_fulltext_query_escapes_special_chars() -> None:
    assert escape_fulltext_query("a+b") == r"a\+b"
    assert escape_fulltext_query("  hello world  ") == "hello world"


def test_escape_fulltext_query_empty() -> None:
    assert escape_fulltext_query("") == ""
    assert escape_fulltext_query("   ") == ""
