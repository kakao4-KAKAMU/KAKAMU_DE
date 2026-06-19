"""Feed upsert / embedding Cypher."""

from __future__ import annotations

from typing import Final, Sequence

from src.graph.cypher_statements.properties import BASE_SUMMARY_EMBEDDING, build_embedding_set_clause

_FEED_ONTOLOGY_RELATIONS_TAIL: Final[str] = """
// related movie (optional)
WITH f
CALL (f) {
  With f WHERE $related_movie_id IS NOT NULL
  MATCH (m:Movie {movie_id: $related_movie_id})
  MERGE (f)-[:ABOUT_MOVIE]->(m)
}

// categories
WITH f
UNWIND $categories AS cname
  MERGE (c:Category {name: cname})
  MERGE (f)-[:HAS_CATEGORY]->(c)

// emotions
WITH f
UNWIND $emotions AS e
  MERGE (em:Emotion {tag: e.tag})
  MERGE (f)-[r:HAS_EMOTION]->(em)
    SET r.score = e.score

// keywords
With f
UNWIND $keywords AS kw
  MERGE (k:Keyword {normalized: kw.normalized})
    ON CREATE SET k.kind = kw.kind, k.term = kw.term
  MERGE (f)-[r:MENTIONS]->(k)
    SET r.weight = kw.weight
"""

UPSERT_FEED_WITH_ONTOLOGY: Final[str] = f"""
MERGE (u:User {{user_id: $user_id}})
MERGE (f:Feed {{feed_id: $feed_id}})
SET f.content_raw       = $content_raw,
    f.summary           = $summary,
    {build_embedding_set_clause("f", BASE_SUMMARY_EMBEDDING, "summary_embedding")},
    f.sentiment         = $sentiment,
    f.sentiment_score   = $sentiment_score,
    f.contains_spoiler  = $contains_spoiler,
    f.toxicity_score    = $toxicity_score,
    f.created_at        = coalesce(f.created_at, $created_at),
    f.updated_at        = datetime()
MERGE (f)-[:WRITTEN_BY]->(u)
""" + _FEED_ONTOLOGY_RELATIONS_TAIL


def build_upsert_feed_with_ontology(
    embedding_properties: Sequence[str] | None = None,
) -> str:
    """버전화된 summary_embedding 속성을 동시에 SET 하는 UPSERT Cypher."""
    embedding_clause = build_embedding_set_clause(
        "f",
        BASE_SUMMARY_EMBEDDING,
        "summary_embedding",
        embedding_properties,
    )
    return f"""
MERGE (u:User {{user_id: $user_id}})
MERGE (f:Feed {{feed_id: $feed_id}})
SET f.content_raw       = $content_raw,
    f.summary           = $summary,
    {embedding_clause},
    f.sentiment         = $sentiment,
    f.sentiment_score   = $sentiment_score,
    f.contains_spoiler  = $contains_spoiler,
    f.toxicity_score    = $toxicity_score,
    f.created_at        = coalesce(f.created_at, $created_at),
    f.updated_at        = datetime()
MERGE (f)-[:WRITTEN_BY]->(u)
""" + _FEED_ONTOLOGY_RELATIONS_TAIL


def build_update_feed_summary_embedding(
    embedding_properties: Sequence[str] | None = None,
) -> str:
    """Feed summary embedding-only 갱신."""
    embedding_clause = build_embedding_set_clause(
        "f",
        BASE_SUMMARY_EMBEDDING,
        "summary_embedding",
        embedding_properties,
    )
    return f"""
MATCH (f:Feed {{feed_id: $feed_id}})
WHERE coalesce(f.summary, '') <> ''
SET {embedding_clause},
    f.updated_at = datetime()
RETURN f.feed_id AS feed_id
"""


UPDATE_FEED_SUMMARY_EMBEDDING: Final[str] = build_update_feed_summary_embedding()


__all__ = [
    "UPDATE_FEED_SUMMARY_EMBEDDING",
    "UPSERT_FEED_WITH_ONTOLOGY",
    "build_update_feed_summary_embedding",
    "build_upsert_feed_with_ontology",
]
