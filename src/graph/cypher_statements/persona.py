"""Persona upsert / delete Cypher."""

from __future__ import annotations

from typing import Final

UPSERT_PERSONA: Final[str] = """
MERGE (u:User {user_id: $user_id})
MERGE (p:Persona {persona_id: $persona_id})
SET p.user_id = $user_id,
    p.label = $label,
    p.updated_at = datetime()
FOREACH (_ IN CASE WHEN p.created_at IS NULL THEN [1] ELSE [] END |
  SET p.created_at = $created_at
)
MERGE (u)-[:HAS_PERSONA]->(p)

WITH p
OPTIONAL MATCH (p)-[rg:PREFERS]->(:Genre)
DELETE rg

WITH p
OPTIONAL MATCH (p)-[im:INTERACTED]->(:Movie)
WHERE im.action = 'interest'
DELETE im

WITH p
OPTIONAL MATCH (p)-[ip:INTERACTED]->(:Person)
WHERE ip.action = 'favorite'
DELETE ip

WITH p
FOREACH (genre_name IN coalesce($genres, []) |
  MERGE (g:Genre {name: genre_name})
  MERGE (p)-[r:PREFERS]->(g)
  SET r.weight = 1.0, r.updated_at = datetime()
)

WITH p
FOREACH (movie_id IN coalesce($movies, []) |
  MERGE (m:Movie {movie_id: movie_id})
  MERGE (p)-[r:INTERACTED]->(m)
  SET r.action = 'interest', r.weight = 1.0, r.ts = $ts
)

WITH p
FOREACH (person_id IN coalesce($persons, []) |
  MERGE (per:Person {person_id: person_id})
  MERGE (p)-[r:INTERACTED]->(per)
  SET r.action = 'favorite', r.weight = 1.0, r.ts = $ts
)
"""

DELETE_PERSONA: Final[str] = """
MATCH (p:Persona {persona_id: $persona_id})
DETACH DELETE p
"""


__all__ = ["UPSERT_PERSONA", "DELETE_PERSONA"]
