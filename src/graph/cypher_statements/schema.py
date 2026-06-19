"""Neo4j schema DDL (constraints, indexes, seeds, vector indexes)."""

from __future__ import annotations

from typing import Final, List

from src.graph.cypher_statements.properties import (
    BASE_PLOT_EMBEDDING,
    BASE_SUMMARY_EMBEDDING,
    normalize_version,
    versioned_embedding_property,
)
from src.ontology.schema import EMOTION_TAG_VALUES, FEED_CATEGORY_VALUES

NODE_CONSTRAINTS: Final[List[str]] = [
    "CREATE CONSTRAINT movie_id_unique IF NOT EXISTS FOR (m:Movie)    REQUIRE m.movie_id   IS UNIQUE",
    "CREATE CONSTRAINT person_id_unique IF NOT EXISTS FOR (p:Person)  REQUIRE p.person_id  IS UNIQUE",
    "CREATE CONSTRAINT user_id_unique IF NOT EXISTS FOR (u:User)      REQUIRE u.user_id    IS UNIQUE",
    "CREATE CONSTRAINT feed_id_unique IF NOT EXISTS FOR (f:Feed)      REQUIRE f.feed_id    IS UNIQUE",
    "CREATE CONSTRAINT comment_id_unique IF NOT EXISTS FOR (c:Comment) REQUIRE c.comment_id IS UNIQUE",
    "CREATE CONSTRAINT genre_name_unique IF NOT EXISTS FOR (g:Genre)  REQUIRE g.name       IS UNIQUE",
    "CREATE CONSTRAINT theme_name_unique IF NOT EXISTS FOR (t:Theme)  REQUIRE t.name       IS UNIQUE",
    "CREATE CONSTRAINT mood_name_unique  IF NOT EXISTS FOR (m:Mood)   REQUIRE m.name       IS UNIQUE",
    "CREATE CONSTRAINT keyword_norm_unique IF NOT EXISTS FOR (k:Keyword) REQUIRE k.normalized IS UNIQUE",
    "CREATE CONSTRAINT category_name_unique IF NOT EXISTS FOR (c:Category) REQUIRE c.name IS UNIQUE",
    "CREATE CONSTRAINT emotion_tag_unique IF NOT EXISTS FOR (e:Emotion) REQUIRE e.tag      IS UNIQUE",
    "CREATE CONSTRAINT country_code_unique IF NOT EXISTS FOR (c:Country) REQUIRE c.code    IS UNIQUE",
    "CREATE CONSTRAINT embedding_version_unique IF NOT EXISTS FOR (e:EmbeddingVersionMeta) REQUIRE e.version IS UNIQUE",
    "CREATE CONSTRAINT embedding_version_property_unique IF NOT EXISTS FOR (e:EmbeddingVersionMeta) REQUIRE e.property_key IS UNIQUE",
]

NODE_PROPERTY_INDEXES: Final[List[str]] = [
    "CREATE INDEX movie_year_idx   IF NOT EXISTS FOR (m:Movie)   ON (m.producing_year)",
    "CREATE INDEX movie_country_idx IF NOT EXISTS FOR (m:Movie)  ON (m.country)",
    "CREATE INDEX feed_created_idx IF NOT EXISTS FOR (f:Feed)    ON (f.created_at)",
    "CREATE INDEX comment_created_idx IF NOT EXISTS FOR (c:Comment) ON (c.created_at)",
    "CREATE INDEX user_created_idx IF NOT EXISTS FOR (u:User)    ON (u.created_at)",
    "CREATE INDEX feed_sentiment_idx IF NOT EXISTS FOR (f:Feed)  ON (f.sentiment_score)",
    "CREATE INDEX embedding_version_role_idx IF NOT EXISTS FOR (e:EmbeddingVersionMeta) ON (e.role)",
    "CREATE INDEX embedding_version_dimension_idx IF NOT EXISTS FOR (e:EmbeddingVersionMeta) ON (e.dimension)",
    "CREATE INDEX embedding_version_model_idx IF NOT EXISTS FOR (e:EmbeddingVersionMeta) ON (e.model_name)",
    "CREATE INDEX embedding_version_created_idx IF NOT EXISTS FOR (e:EmbeddingVersionMeta) ON (e.created_at)",
]

FULLTEXT_INDEXES: Final[List[str]] = [
    """
    CREATE FULLTEXT INDEX movie_text_ft IF NOT EXISTS
    FOR (m:Movie) ON EACH [m.title, m.plot_summary]
    OPTIONS { indexConfig: { `fulltext.analyzer`: 'cjk' } }
    """,
    """
    CREATE FULLTEXT INDEX feed_text_ft IF NOT EXISTS
    FOR (f:Feed) ON EACH [f.summary]
    OPTIONS { indexConfig: { `fulltext.analyzer`: 'cjk' } }
    """,
    """
    CREATE FULLTEXT INDEX comment_text_ft IF NOT EXISTS
    FOR (c:Comment) ON EACH [c.summary]
    OPTIONS { indexConfig: { `fulltext.analyzer`: 'cjk' } }
    """,
    """
    CREATE FULLTEXT INDEX keyword_text_ft IF NOT EXISTS
    FOR (k:Keyword) ON EACH [k.term, k.normalized]
    OPTIONS { indexConfig: { `fulltext.analyzer`: 'cjk' } }
    """,
]

SEED_CATEGORIES: Final[List[str]] = FEED_CATEGORY_VALUES
SEED_EMOTIONS: Final[List[str]] = EMOTION_TAG_VALUES

SEED_MERGE_CATEGORY: Final[str] = """
UNWIND $categories AS name
MERGE (c:Category {name: name})
ON CREATE SET c.created_at = datetime()
"""

SEED_MERGE_EMOTION: Final[str] = """
UNWIND $emotions AS tag
MERGE (e:Emotion {tag: tag})
ON CREATE SET e.created_at = datetime()
"""


def vector_index_statements_for_version(
    version: str,
    embedding_dim: int,
    *,
    label: str = "Movie",
    base_property: str = BASE_PLOT_EMBEDDING,
    index_prefix: str | None = None,
) -> List[str]:
    """버전별 vector index (예: summary_embedding_v2, plot_embedding_v1)."""
    prop = versioned_embedding_property(base_property, version)
    if index_prefix is None:
        if label == "Movie" and base_property == BASE_PLOT_EMBEDDING:
            prefix = "movie_plot_vec"
        elif label == "Feed" and base_property == BASE_SUMMARY_EMBEDDING:
            prefix = "feed_summary_vec"
        elif label == "Comment" and base_property == BASE_SUMMARY_EMBEDDING:
            prefix = "comment_summary_vec"
        else:
            prefix = f"{label.lower()}_{base_property}"
    else:
        prefix = index_prefix
    index_name = f"{prefix}_{normalize_version(version)}"
    return [
        f"""
        CREATE VECTOR INDEX {index_name} IF NOT EXISTS
        FOR (n:{label}) ON (n.{prop})
        OPTIONS {{
            indexConfig: {{
                `vector.dimensions`: {embedding_dim},
                `vector.similarity_function`: 'cosine'
            }}
        }}
        """
    ]


def vector_index_statements(embedding_dim: int) -> List[str]:
    """legacy/base embedding 속성용 native vector index."""
    return [
        f"""
        CREATE VECTOR INDEX movie_plot_vec IF NOT EXISTS
        FOR (m:Movie) ON (m.{BASE_PLOT_EMBEDDING})
        OPTIONS {{
            indexConfig: {{
                `vector.dimensions`: {embedding_dim},
                `vector.similarity_function`: 'cosine'
            }}
        }}
        """,
        f"""
        CREATE VECTOR INDEX feed_summary_vec IF NOT EXISTS
        FOR (f:Feed) ON (f.{BASE_SUMMARY_EMBEDDING})
        OPTIONS {{
            indexConfig: {{
                `vector.dimensions`: {embedding_dim},
                `vector.similarity_function`: 'cosine'
            }}
        }}
        """,
        f"""
        CREATE VECTOR INDEX comment_summary_vec IF NOT EXISTS
        FOR (c:Comment) ON (c.{BASE_SUMMARY_EMBEDDING})
        OPTIONS {{
            indexConfig: {{
                `vector.dimensions`: {embedding_dim},
                `vector.similarity_function`: 'cosine'
            }}
        }}
        """,
    ]


__all__ = [
    "FULLTEXT_INDEXES",
    "NODE_CONSTRAINTS",
    "NODE_PROPERTY_INDEXES",
    "SEED_CATEGORIES",
    "SEED_EMOTIONS",
    "SEED_MERGE_CATEGORY",
    "SEED_MERGE_EMOTION",
    "vector_index_statements",
    "vector_index_statements_for_version",
]
