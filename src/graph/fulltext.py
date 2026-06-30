"""Neo4j fulltext query helpers."""

from __future__ import annotations

import re

_LUCENE_SPECIAL = re.compile(r'([+\-!(){}[\]^"~*?:\\/|&])')


def escape_fulltext_query(query: str) -> str:
    """Lucene fulltext 쿼리용 특수문자 이스케이프."""
    text = query.strip()
    if not text:
        return text
    return _LUCENE_SPECIAL.sub(r"\\\1", text)


__all__ = ["escape_fulltext_query"]
