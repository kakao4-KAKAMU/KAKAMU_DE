"""Comment upsert / embedding Cypher."""

from __future__ import annotations

from typing import Final, Sequence

from src.graph.cypher_statements.properties import BASE_SUMMARY_EMBEDDING, build_embedding_set_clause

_COMMENT_ONTOLOGY_RELATIONS_TAIL: Final[str] = """
// parent comment (대댓글, optional)
WITH c
CALL (c) {
  With c WHERE $parent_comment_id IS NOT NULL
  MERGE (pc:Comment {comment_id: $parent_comment_id})
  MERGE (c)-[:REPLY_TO]->(pc)
}

// emotions (optional)
WITH c
FOREACH (e IN coalesce($emotions, []) |
  MERGE (em:Emotion {tag: e.tag})
  MERGE (c)-[r:HAS_EMOTION]->(em)
    SET r.score = e.score
)

// keywords (optional)
WITH c
FOREACH (kw IN coalesce($keywords, []) |
  MERGE (k:Keyword {normalized: kw.normalized})
    ON CREATE SET k.kind = kw.kind, k.term = kw.term
  MERGE (c)-[r:MENTIONS]->(k)
    SET r.weight = kw.weight
)
"""

UPSERT_COMMENT_WITH_ONTOLOGY: Final[str] = f"""
MERGE (u:User {{user_id: $user_id}})
MERGE (parent:Feed {{feed_id: $feed_id}})
MERGE (c:Comment {{comment_id: $comment_id}})
SET c.content_raw       = $content_raw,
    c.summary           = $summary,
    {build_embedding_set_clause("c", BASE_SUMMARY_EMBEDDING, "summary_embedding")},
    c.sentiment         = $sentiment,
    c.sentiment_score   = $sentiment_score,
    c.contains_spoiler  = $contains_spoiler,
    c.toxicity_score    = $toxicity_score,
    c.created_at        = coalesce(c.created_at, $created_at),
    c.updated_at        = datetime()
MERGE (c)-[:ON_FEED]->(parent)
MERGE (c)-[:WRITTEN_BY]->(u)
""" + _COMMENT_ONTOLOGY_RELATIONS_TAIL


def build_upsert_comment_with_ontology(
    embedding_properties: Sequence[str] | None = None,
) -> str:
    """버전화된 summary_embedding 속성을 동시에 SET 하는 UPSERT Cypher."""
    embedding_clause = build_embedding_set_clause(
        "c",
        BASE_SUMMARY_EMBEDDING,
        "summary_embedding",
        embedding_properties,
    )
    return f"""
MERGE (u:User {{user_id: $user_id}})
MERGE (parent:Feed {{feed_id: $feed_id}})
MERGE (c:Comment {{comment_id: $comment_id}})
SET c.content_raw       = $content_raw,
    c.summary           = $summary,
    {embedding_clause},
    c.sentiment         = $sentiment,
    c.sentiment_score   = $sentiment_score,
    c.contains_spoiler  = $contains_spoiler,
    c.toxicity_score    = $toxicity_score,
    c.created_at        = coalesce(c.created_at, $created_at),
    c.updated_at        = datetime()
MERGE (c)-[:ON_FEED]->(parent)
MERGE (c)-[:WRITTEN_BY]->(u)
""" + _COMMENT_ONTOLOGY_RELATIONS_TAIL


def build_update_comment_summary_embedding(
    embedding_properties: Sequence[str] | None = None,
) -> str:
    """Comment summary embedding-only 갱신."""
    embedding_clause = build_embedding_set_clause(
        "c",
        BASE_SUMMARY_EMBEDDING,
        "summary_embedding",
        embedding_properties,
    )
    return f"""
MATCH (c:Comment {{comment_id: $comment_id}})
WHERE coalesce(c.summary, '') <> ''
SET {embedding_clause},
    c.updated_at = datetime()
RETURN c.comment_id AS comment_id
"""


UPDATE_COMMENT_SUMMARY_EMBEDDING: Final[str] = build_update_comment_summary_embedding()


__all__ = [
    "UPDATE_COMMENT_SUMMARY_EMBEDDING",
    "UPSERT_COMMENT_WITH_ONTOLOGY",
    "build_update_comment_summary_embedding",
    "build_upsert_comment_with_ontology",
]
