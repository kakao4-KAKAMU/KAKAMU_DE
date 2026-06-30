"""MovieTitle search Cypher."""

from __future__ import annotations

from typing import Final

SEARCH_MOVIES_BY_TITLE_FT: Final[str] = """
CALL db.index.fulltext.queryNodes('movie_title_text_ft', $query)
YIELD node AS mt, score
WHERE $country IS NULL OR mt.country = $country
MATCH (m:Movie)-[:HAS_TITLE]->(mt)
WITH m, mt, score
ORDER BY score DESC
WITH m, collect({matched_title: mt.title, title_country: mt.country, score: score})[0] AS best
RETURN m.movie_id              AS movie_id,
       m.title                 AS title,
       best.matched_title      AS matched_title,
       best.title_country      AS title_country,
       best.score              AS score
ORDER BY best.score DESC
LIMIT $top_k
"""

MIGRATE_MOVIE_TITLES_FROM_MOVIE: Final[str] = """
MATCH (m:Movie)
WHERE coalesce(m.title, '') <> ''
MERGE (m)-[:HAS_TITLE]->(mt:MovieTitle {title: m.title, country: coalesce(m.country, '')})
ON CREATE SET mt.created_at = datetime()
RETURN count(mt) AS migrated
"""


__all__ = [
    "MIGRATE_MOVIE_TITLES_FROM_MOVIE",
    "SEARCH_MOVIES_BY_TITLE_FT",
]
