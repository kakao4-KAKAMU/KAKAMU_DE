"""온톨로지 결과 → Neo4j Upsert Loader.

설계 원칙
---------
- SRP : "Pydantic Ontology → Cypher params" 변환 및 적재만 담당.
- DIP : Neo4jClient 인터페이스에만 의존(드라이버 교체 가능).
- OCP : 임베딩 버전이 늘어나도 ``EmbeddingVersionRegistry`` 주입만으로 대응.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional, Sequence

from src.embedding.version_registry import EmbeddingVersionRegistry
from src.graph.client import Neo4jClient
from src.graph.cypher_statements import (
    UPSERT_COMMENT_WITH_ONTOLOGY,
    UPSERT_FEED_WITH_ONTOLOGY,
    UPSERT_MOVIE_WITH_ONTOLOGY,
    build_upsert_movie_with_ontology,
)
from src.ontology.schema import (
    CommentOntology,
    FeedOntology,
    MoviePlotOntology,
)
from src.vocab.pipeline import VocabPipeline

logger = logging.getLogger(__name__)


class OntologyLoader:
    """Ontology 객체를 Neo4j 로 멱등 적재한다.

    Args:
        neo4j: Neo4j 드라이버 래퍼.
        vocab_pipeline: 정규화/후보어휘 파이프라인 (선택).
        embedding_registry: 주입 시 active+shadow ``plot_embedding_vN`` 컬럼에도 동시 SET.
    """

    def __init__(
        self,
        neo4j: Neo4jClient,
        vocab_pipeline: VocabPipeline | None = None,
        *,
        embedding_registry: EmbeddingVersionRegistry | None = None,
    ) -> None:
        self._neo4j = neo4j
        self._vocab = vocab_pipeline
        self._embedding_registry = embedding_registry

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------
    def _movie_upsert_cypher(self) -> str:
        if self._embedding_registry is None:
            return UPSERT_MOVIE_WITH_ONTOLOGY
        targets = self._embedding_registry.write_targets()
        extra_props = [v.property_key for v in targets]
        if not extra_props:
            return UPSERT_MOVIE_WITH_ONTOLOGY
        return build_upsert_movie_with_ontology(embedding_properties=extra_props)

    # ------------------------------------------------------------------
    # Movie
    # ------------------------------------------------------------------
    def upsert_movie(
        self,
        *,
        movie_id: str,
        title: str,
        producing_year: int | None,
        country: str | None,
        genres: Sequence[str],
        plot_raw: str,
        ontology: MoviePlotOntology,
        plot_embedding: Sequence[float],
    ) -> None:
        themes = ontology.themes
        moods = ontology.moods
        keywords = ontology.keywords
        if self._vocab:
            themes = self._vocab.resolve_themes(themes)
            moods = self._vocab.resolve_moods(moods)
            keywords = self._vocab.resolve_keywords(keywords)

        params = {
            "movie_id": movie_id,
            "title": title,
            "producing_year": producing_year,
            "country": country,
            "plot_raw": plot_raw,
            "plot_summary": ontology.summary,
            "plot_embedding": list(plot_embedding),
            "genres": list(genres),
            "themes": themes,
            "moods": moods,
            "keywords": [k.model_dump() for k in keywords],
        }
        self._neo4j.execute_write(self._movie_upsert_cypher(), params)
        logger.info(
            "Upserted movie %s (themes=%d, keywords=%d)",
            movie_id,
            len(ontology.themes),
            len(ontology.keywords),
        )

    # ------------------------------------------------------------------
    # Feed
    # ------------------------------------------------------------------
    def upsert_feed(
        self,
        *,
        feed_id: str,
        author_id: str,
        related_movie_id: Optional[str],
        content_raw: str,
        ontology: FeedOntology,
        summary_embedding: Sequence[float],
        created_at: Optional[datetime] = None,
    ) -> None:
        params = {
            "feed_id": feed_id,
            "author_id": author_id,
            "related_movie_id": related_movie_id,
            "content_raw": content_raw,
            "summary": ontology.summary,
            "summary_embedding": list(summary_embedding),
            "sentiment": ontology.sentiment.value,
            "sentiment_score": ontology.sentiment_score,
            "contains_spoiler": ontology.contains_spoiler,
            "toxicity_score": ontology.toxicity_score,
            "categories": [c.value for c in ontology.categories],
            "emotions": [
                {"tag": e.tag.value, "score": e.score} for e in ontology.emotions
            ],
            "keywords": [k.model_dump() for k in ontology.keywords],
            "created_at": (created_at or datetime.now(timezone.utc)),
        }
        self._neo4j.execute_write(UPSERT_FEED_WITH_ONTOLOGY, params)
        logger.info(
            "Upserted feed %s (cats=%d, keywords=%d)",
            feed_id,
            len(ontology.categories),
            len(ontology.keywords),
        )

    # ------------------------------------------------------------------
    # Comment
    # ------------------------------------------------------------------
    def upsert_comment(
        self,
        *,
        comment_id: str,
        feed_id: str,
        author_id: str,
        content_raw: str,
        ontology: CommentOntology,
        summary_embedding: Sequence[float],
        created_at: Optional[datetime] = None,
    ) -> None:
        params = {
            "comment_id": comment_id,
            "feed_id": feed_id,
            "author_id": author_id,
            "content_raw": content_raw,
            "summary": ontology.summary,
            "summary_embedding": list(summary_embedding),
            "sentiment": ontology.sentiment.value,
            "sentiment_score": ontology.sentiment_score,
            "contains_spoiler": ontology.contains_spoiler,
            "toxicity_score": ontology.toxicity_score,
            "emotions": [
                {"tag": e.tag.value, "score": e.score} for e in ontology.emotions
            ],
            "keywords": [k.model_dump() for k in ontology.keywords],
            "created_at": (created_at or datetime.now(timezone.utc)),
        }
        self._neo4j.execute_write(UPSERT_COMMENT_WITH_ONTOLOGY, params)
        logger.info("Upserted comment %s on feed %s", comment_id, feed_id)


__all__ = ["OntologyLoader"]
