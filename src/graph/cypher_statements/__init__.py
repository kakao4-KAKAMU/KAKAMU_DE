"""Neo4j Cypher statement modules (re-export hub)."""

from .comment import (
    UPDATE_COMMENT_SUMMARY_EMBEDDING,
    UPSERT_COMMENT_WITH_ONTOLOGY,
    build_update_comment_summary_embedding,
    build_upsert_comment_with_ontology,
)
from .context import GET_COMMENT_SUMMARY, GET_FEED_SUMMARY
from .feed import (
    UPDATE_FEED_SUMMARY_EMBEDDING,
    UPSERT_FEED_WITH_ONTOLOGY,
    build_update_feed_summary_embedding,
    build_upsert_feed_with_ontology,
)
from .interaction import (
    JUDGE_MOVIE_WITH_PERSONA,
    JUDGE_PERSON_WITH_PERSONA,
    LIKE_COMMENT_WITH_PERSONA,
    LIKE_FEED_WITH_PERSONA,
    SOFT_DELETE_COMMENT,
    SOFT_DELETE_FEED,
    UNLIKE_COMMENT_WITH_PERSONA,
    UNLIKE_FEED_WITH_PERSONA,
)
from .movie import (
    UPSERT_MOVIE_WITH_ONTOLOGY,
    build_update_movie_plot_embedding,
    build_upsert_movie_with_ontology,
)
from .properties import (
    BASE_PLOT_EMBEDDING,
    BASE_SUMMARY_EMBEDDING,
    build_embedding_set_clause,
    normalize_version,
    plot_embedding_property,
    summary_embedding_property,
    versioned_embedding_property,
)
from .retrieval import (
    HYBRID_FEED_RECOMMEND_WEIGHTED,
    HYBRID_MOVIE_RECOMMEND_WEIGHTED,
    build_hybrid_feed_recommend_weighted,
    build_hybrid_movie_recommend_weighted,
)
from .schema import (
    FULLTEXT_INDEXES,
    NODE_CONSTRAINTS,
    NODE_PROPERTY_INDEXES,
    SEED_CATEGORIES,
    SEED_EMOTIONS,
    SEED_MERGE_CATEGORY,
    SEED_MERGE_EMOTION,
    vector_index_statements,
    vector_index_statements_for_version,
)

__all__ = [
    "BASE_PLOT_EMBEDDING",
    "BASE_SUMMARY_EMBEDDING",
    "FULLTEXT_INDEXES",
    "GET_COMMENT_SUMMARY",
    "GET_FEED_SUMMARY",
    "HYBRID_FEED_RECOMMEND_WEIGHTED",
    "HYBRID_MOVIE_RECOMMEND_WEIGHTED",
    "JUDGE_MOVIE_WITH_PERSONA",
    "JUDGE_PERSON_WITH_PERSONA",
    "LIKE_COMMENT_WITH_PERSONA",
    "LIKE_FEED_WITH_PERSONA",
    "NODE_CONSTRAINTS",
    "NODE_PROPERTY_INDEXES",
    "SEED_CATEGORIES",
    "SEED_EMOTIONS",
    "SEED_MERGE_CATEGORY",
    "SEED_MERGE_EMOTION",
    "SOFT_DELETE_COMMENT",
    "SOFT_DELETE_FEED",
    "UNLIKE_COMMENT_WITH_PERSONA",
    "UNLIKE_FEED_WITH_PERSONA",
    "UPDATE_COMMENT_SUMMARY_EMBEDDING",
    "UPDATE_FEED_SUMMARY_EMBEDDING",
    "UPSERT_COMMENT_WITH_ONTOLOGY",
    "UPSERT_FEED_WITH_ONTOLOGY",
    "UPSERT_MOVIE_WITH_ONTOLOGY",
    "build_embedding_set_clause",
    "build_hybrid_feed_recommend_weighted",
    "build_hybrid_movie_recommend_weighted",
    "build_update_comment_summary_embedding",
    "build_update_feed_summary_embedding",
    "build_update_movie_plot_embedding",
    "build_upsert_comment_with_ontology",
    "build_upsert_feed_with_ontology",
    "build_upsert_movie_with_ontology",
    "normalize_version",
    "plot_embedding_property",
    "summary_embedding_property",
    "vector_index_statements",
    "vector_index_statements_for_version",
    "versioned_embedding_property",
]
