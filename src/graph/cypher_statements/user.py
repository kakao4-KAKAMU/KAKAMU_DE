"""User upsert Cypher."""

from __future__ import annotations

from typing import Final

UPSERT_USER: Final[str] = """
MERGE (u:User {user_id: $user_id})
SET u.nickname = $nickname,
    u.updated_at = datetime()
FOREACH (_ IN CASE WHEN u.created_at IS NULL THEN [1] ELSE [] END |
  SET u.created_at = $created_at
)
"""


__all__ = ["UPSERT_USER"]
