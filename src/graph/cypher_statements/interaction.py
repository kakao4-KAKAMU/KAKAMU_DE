"""Like / judge / soft-delete Cypher."""

from __future__ import annotations

from typing import Final

LIKE_FEED_WITH_PERSONA: Final[str] = """
MERGE (f:Feed {feed_id: $feed_id})
WITH f
CALL (f) {
  WITH f WHERE $persona_id IS NOT NULL
  MERGE (u:User {user_id: $user_id})
  MERGE (pe:Persona {persona_id: $persona_id})
  MERGE (u)-[:HAS_PERSONA]->(pe)
  MERGE (pe)-[r:INTERACTED]->(f)
    SET r.action = 'like', r.weight = $weight, r.ts = $ts
}
WITH f
CALL (f) {
  WITH f WHERE $persona_id IS NULL
  MERGE (u:User {user_id: $user_id})
  MERGE (u)-[r:INTERACTED]->(f)
    SET r.action = 'like', r.weight = $weight, r.ts = $ts
}
"""

UNLIKE_FEED_WITH_PERSONA: Final[str] = """
MATCH (f:Feed {feed_id: $feed_id})
WITH f
CALL (f) {
  WITH f WHERE $persona_id IS NOT NULL
  OPTIONAL MATCH (:Persona {persona_id: $persona_id})-[r:INTERACTED]->(f)
  DELETE r
}
WITH f
CALL (f) {
  WITH f WHERE $persona_id IS NULL
  OPTIONAL MATCH (:User {user_id: $user_id})-[r:INTERACTED]->(f)
  DELETE r
}
"""

LIKE_COMMENT_WITH_PERSONA: Final[str] = """
MERGE (c:Comment {comment_id: $comment_id})
WITH c
CALL (c) {
  WITH c WHERE $persona_id IS NOT NULL
  MERGE (u:User {user_id: $user_id})
  MERGE (pe:Persona {persona_id: $persona_id})
  MERGE (u)-[:HAS_PERSONA]->(pe)
  MERGE (pe)-[r:INTERACTED]->(c)
    SET r.action = 'like', r.weight = $weight, r.ts = $ts
}
WITH c
CALL (c) {
  WITH c WHERE $persona_id IS NULL
  MERGE (u:User {user_id: $user_id})
  MERGE (u)-[r:INTERACTED]->(c)
    SET r.action = 'like', r.weight = $weight, r.ts = $ts
}
"""

UNLIKE_COMMENT_WITH_PERSONA: Final[str] = """
MATCH (c:Comment {comment_id: $comment_id})
WITH c
CALL (c) {
  WITH c WHERE $persona_id IS NOT NULL
  OPTIONAL MATCH (:Persona {persona_id: $persona_id})-[r:INTERACTED]->(c)
  DELETE r
}
WITH c
CALL (c) {
  WITH c WHERE $persona_id IS NULL
  OPTIONAL MATCH (:User {user_id: $user_id})-[r:INTERACTED]->(c)
  DELETE r
}
"""

JUDGE_MOVIE_WITH_PERSONA: Final[str] = """
MERGE (m:Movie {movie_id: $movie_id})
WITH m
CALL (m) {
  WITH m WHERE $persona_id IS NOT NULL
  MERGE (u:User {user_id: $user_id})
  MERGE (pe:Persona {persona_id: $persona_id})
  MERGE (u)-[:HAS_PERSONA]->(pe)
  MERGE (pe)-[r:INTERACTED]->(m)
    SET r.action = $judge_type, r.weight = $weight, r.ts = $ts
}
WITH m
CALL (m) {
  WITH m WHERE $persona_id IS NULL
  MERGE (u:User {user_id: $user_id})
  MERGE (u)-[r:INTERACTED]->(m)
    SET r.action = $judge_type, r.weight = $weight, r.ts = $ts
}
"""

JUDGE_PERSON_WITH_PERSONA: Final[str] = """
MERGE (p:Person {person_id: $person_id})
WITH p
CALL (p) {
  WITH p WHERE $persona_id IS NOT NULL
  MERGE (u:User {user_id: $user_id})
  MERGE (pe:Persona {persona_id: $persona_id})
  MERGE (u)-[:HAS_PERSONA]->(pe)
  MERGE (pe)-[r:INTERACTED]->(p)
    SET r.action = $judge_type, r.weight = $weight, r.ts = $ts
}
WITH p
CALL (p) {
  WITH p WHERE $persona_id IS NULL
  MERGE (u:User {user_id: $user_id})
  MERGE (u)-[r:INTERACTED]->(p)
    SET r.action = $judge_type, r.weight = $weight, r.ts = $ts
}
"""

SOFT_DELETE_FEED: Final[str] = """
MATCH (f:Feed {feed_id: $feed_id})
SET f.deleted = true,
    f.deleted_at = $deleted_at,
    f.updated_at = datetime()
"""

SOFT_DELETE_COMMENT: Final[str] = """
MATCH (c:Comment {comment_id: $comment_id})
SET c.deleted = true,
    c.deleted_at = $deleted_at,
    c.updated_at = datetime()
"""


__all__ = [
    "JUDGE_MOVIE_WITH_PERSONA",
    "JUDGE_PERSON_WITH_PERSONA",
    "LIKE_COMMENT_WITH_PERSONA",
    "LIKE_FEED_WITH_PERSONA",
    "SOFT_DELETE_COMMENT",
    "SOFT_DELETE_FEED",
    "UNLIKE_COMMENT_WITH_PERSONA",
    "UNLIKE_FEED_WITH_PERSONA",
]
