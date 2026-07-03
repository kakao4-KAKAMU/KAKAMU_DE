"""Cypher read-only 보안 검증."""

from __future__ import annotations

import re

_WRITE_KEYWORDS = re.compile(
    r"\b(CREATE|MERGE|DELETE|DETACH|SET|DROP|REMOVE|FOREACH|LOAD\s+CSV)\b",
    re.IGNORECASE,
)

_FORBIDDEN_PROCEDURE = re.compile(
    r"\b(apoc\.|gds\.|dbms\.|tx\.)\b",
    re.IGNORECASE,
)

_ALLOWED_FULLTEXT_PROCEDURE = "db.index.fulltext.queryNodes"

_CALL_PROCEDURE = re.compile(
    rf"\bCALL\s+(?!\s*\{{)(?!{_ALLOWED_FULLTEXT_PROCEDURE.replace('.', r'\.')}\s*\()",
    re.IGNORECASE,
)

_USER_PERSONA_LABEL = re.compile(
    r":\s*(User|Persona)\b",
    re.IGNORECASE,
)


def validate_cypher_security(cypher: str) -> list[str]:
    """read-only Cypher 에 대한 보안 규칙 위반 목록."""
    errors: list[str] = []

    if _WRITE_KEYWORDS.search(cypher):
        errors.append("security: write/mutation keywords are not allowed")

    if _CALL_PROCEDURE.search(cypher):
        errors.append("security: procedure CALL is not allowed")

    if _FORBIDDEN_PROCEDURE.search(cypher):
        errors.append("security: forbidden procedure namespace")

    if _USER_PERSONA_LABEL.search(cypher):
        errors.append("security: User/Persona node access is not allowed")

    return errors


__all__ = ["validate_cypher_security"]
