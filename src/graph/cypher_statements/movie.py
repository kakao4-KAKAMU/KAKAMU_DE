"""Movie upsert / embedding Cypher."""

from __future__ import annotations

from typing import Final, Sequence

from src.graph.cypher_statements.properties import BASE_PLOT_EMBEDDING, build_embedding_set_clause

_MOVIE_TITLE_RELATIONS: Final[str] = """
// MovieTitle (optional, 1:N per movie)
WITH m
UNWIND coalesce($titles, []) AS t
MERGE (m)-[:HAS_TITLE]->(mt:MovieTitle {title: t.title, country: t.country})
ON CREATE SET mt.created_at = datetime()
SET mt.updated_at = datetime()
"""

_MOVIE_TAXONOMY_RELATIONS: Final[str] = """
// Genre (optional)
WITH m
FOREACH (gname IN coalesce($genres, []) |
  MERGE (g:Genre {name: gname})
  MERGE (m)-[:HAS_GENRE]->(g)
)

// Theme (optional)
WITH m
FOREACH (tname IN coalesce($themes, []) |
  MERGE (t:Theme {name: tname})
  MERGE (m)-[:HAS_THEME]->(t)
)

// Mood (optional)
WITH m
FOREACH (mdname IN coalesce($moods, []) |
  MERGE (md:Mood {name: mdname})
  MERGE (m)-[:HAS_MOOD]->(md)
)

// Keywords (optional)
WITH m
FOREACH (kw IN coalesce($keywords, []) |
  MERGE (k:Keyword {normalized: kw.normalized})
    ON CREATE SET k.kind = kw.kind, k.term = kw.term
  MERGE (m)-[r:MENTIONS]->(k)
    SET r.weight = kw.weight
)
"""

_MOVIE_ONTOLOGY_RELATIONS_TAIL: Final[str] = """
// Person (director, actor, etc., optional)
WITH m
FOREACH (pr IN coalesce($persons, []) |
  MERGE (p:Person {person_id: pr.person_id})
    SET p.name = pr.name
  MERGE (m)-[hp:HAS_PERSON]->(p)
    SET hp.job = pr.job
)

// Country node (optional)
WITH m
CALL (m) {
  WITH m WHERE $country IS NOT NULL AND trim(toString($country)) <> ''
  MERGE (c:Country {code: $country})
    ON CREATE SET c.name = $country
  MERGE (m)-[:PRODUCED_IN]->(c)
}

RETURN count(*) AS _
"""

UPSERT_MOVIE_WITH_ONTOLOGY: Final[str] = f"""
MERGE (m:Movie {{movie_id: $movie_id}})
SET m.title          = $title,
    m.producing_year = $producing_year,
    m.country        = $country,
    m.plot_raw       = $plot_raw,
    m.plot_summary   = $plot_summary,
    {build_embedding_set_clause("m", BASE_PLOT_EMBEDDING, "plot_embedding")},
    m.toxicity_score = $toxicity_score,
    m.updated_at     = datetime()
""" + _MOVIE_TITLE_RELATIONS + _MOVIE_TAXONOMY_RELATIONS + _MOVIE_ONTOLOGY_RELATIONS_TAIL


def build_upsert_movie_with_ontology(
    embedding_properties: Sequence[str] | None = None,
) -> str:
    """버전화된 plot_embedding 속성을 동시에 SET 하는 UPSERT Cypher 를 생성한다."""
    embedding_clause = build_embedding_set_clause(
        "m",
        BASE_PLOT_EMBEDDING,
        "plot_embedding",
        embedding_properties,
    )
    return f"""
MERGE (m:Movie {{movie_id: $movie_id}})
SET m.title          = $title,
    m.producing_year = $producing_year,
    m.country        = $country,
    m.plot_raw       = $plot_raw,
    m.plot_summary   = $plot_summary,
    {embedding_clause},
    m.toxicity_score = $toxicity_score,
    m.updated_at     = datetime()
""" + _MOVIE_TITLE_RELATIONS + _MOVIE_TAXONOMY_RELATIONS + _MOVIE_ONTOLOGY_RELATIONS_TAIL


def build_update_movie_plot_embedding(
    embedding_properties: Sequence[str] | None = None,
) -> str:
    """Movie summary(plot) embedding-only 갱신."""
    embedding_clause = build_embedding_set_clause(
        "m",
        BASE_PLOT_EMBEDDING,
        "plot_embedding",
        embedding_properties,
    )
    return f"""
MATCH (m:Movie {{movie_id: $movie_id}})
WHERE coalesce(m.plot_summary, '') <> ''
SET {embedding_clause},
    m.updated_at = datetime()
RETURN m.movie_id AS movie_id
"""


__all__ = [
    "UPSERT_MOVIE_WITH_ONTOLOGY",
    "build_update_movie_plot_embedding",
    "build_upsert_movie_with_ontology",
]
