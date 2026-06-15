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
from typing import Mapping, Optional, Sequence

from src.embedding.version_registry import EmbeddingVersionRegistry
from src.graph.client import Neo4jClient
from src.graph.cypher_statements import (
    JUDGE_MOVIE_WITH_PERSONA,
    JUDGE_PERSON_WITH_PERSONA,
    LIKE_COMMENT_WITH_PERSONA,
    LIKE_FEED_WITH_PERSONA,
    SOFT_DELETE_COMMENT,
    SOFT_DELETE_FEED,
    UNLIKE_COMMENT_WITH_PERSONA,
    UNLIKE_FEED_WITH_PERSONA,
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
        persons: Sequence[Mapping[str, str]] | None = None,
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
            "toxicity_score": ontology.toxicity_score,
            "keywords": [k.model_dump() for k in keywords],
            "persons": [
                {
                    "person_id": str(p["person_id"]),
                    "name": str(p["name"]),
                    "job": str(p["job"]),
                }
                for p in (persons or [])
            ],
        }
        self._neo4j.execute_write(self._movie_upsert_cypher(), params)
        logger.info(
            "Upserted movie %s (themes=%d, keywords=%d, persons=%d)",
            movie_id,
            len(ontology.themes),
            len(ontology.keywords),
            len(persons or []),
        )

    # ------------------------------------------------------------------
    # Feed
    # ------------------------------------------------------------------
    def upsert_feed(
        self,
        *,
        feed_id: str,
        user_id: str,
        related_movie_id: Optional[str],
        content_raw: str,
        ontology: FeedOntology,
        summary_embedding: Sequence[float],
        created_at: Optional[datetime] = None,
    ) -> None:
        params = {
            "feed_id": feed_id,
            "user_id": user_id,
            "related_movie_id": related_movie_id,
            "content_raw": content_raw,
            "summary": ontology.summary,
            "summary_embedding": list(summary_embedding),
            "sentiment": ontology.sentiment.value,
            "sentiment_score": ontology.sentiment_score,
            "contains_spoiler": ontology.contains_spoiler,
            "toxicity_score": ontology.toxicity_score,
            "categories": [ontology.category.value],
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
            1,
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
        user_id: str,
        content_raw: str,
        ontology: CommentOntology,
        summary_embedding: Sequence[float],
        parent_comment_id: Optional[str] = None,
        created_at: Optional[datetime] = None,
    ) -> None:
        params = {
            "comment_id": comment_id,
            "feed_id": feed_id,
            "user_id": user_id,
            "parent_comment_id": parent_comment_id,
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

    # ------------------------------------------------------------------
    # Feed Like
    # ------------------------------------------------------------------
    def like_feed(
        self,
        *,
        feed_id: str,
        user_id: str,
        persona_id: Optional[str] = None,
        is_like: bool = True,
        ts: Optional[datetime] = None,
    ) -> None:
        ts_val = ts or datetime.now(timezone.utc)
        if is_like:
            self._neo4j.execute_write(
                LIKE_FEED_WITH_PERSONA,
                {"feed_id": feed_id, "user_id": user_id, "persona_id": persona_id,
                 "weight": 1.0, "ts": ts_val},
            )
        else:
            self._neo4j.execute_write(
                UNLIKE_FEED_WITH_PERSONA,
                {"feed_id": feed_id, "user_id": user_id, "persona_id": persona_id},
            )
        logger.info("Feed like=%s feed=%s user=%s", is_like, feed_id, user_id)

    # ------------------------------------------------------------------
    # Comment Like
    # ------------------------------------------------------------------
    def like_comment(
        self,
        *,
        comment_id: str,
        user_id: str,
        persona_id: Optional[str] = None,
        is_like: bool = True,
        ts: Optional[datetime] = None,
    ) -> None:
        ts_val = ts or datetime.now(timezone.utc)
        if is_like:
            self._neo4j.execute_write(
                LIKE_COMMENT_WITH_PERSONA,
                {"comment_id": comment_id, "user_id": user_id, "persona_id": persona_id,
                 "weight": 1.0, "ts": ts_val},
            )
        else:
            self._neo4j.execute_write(
                UNLIKE_COMMENT_WITH_PERSONA,
                {"comment_id": comment_id, "user_id": user_id, "persona_id": persona_id},
            )
        logger.info("Comment like=%s comment=%s user=%s", is_like, comment_id, user_id)

    # ------------------------------------------------------------------
    # Movie Judge
    # ------------------------------------------------------------------
    def judge_movie(
        self,
        *,
        movie_id: str,
        user_id: str,
        judge_type: str,
        persona_id: Optional[str] = None,
        ts: Optional[datetime] = None,
    ) -> None:
        weight = 1.0 if judge_type == "like" else -1.0
        ts_val = ts or datetime.now(timezone.utc)
        self._neo4j.execute_write(
            JUDGE_MOVIE_WITH_PERSONA,
            {"movie_id": movie_id, "user_id": user_id, "persona_id": persona_id,
             "judge_type": judge_type, "weight": weight, "ts": ts_val},
        )
        logger.info(
            "Judge movie=%s user=%s persona=%s type=%s",
            movie_id, user_id, persona_id, judge_type,
        )

    # ------------------------------------------------------------------
    # Person Judge
    # ------------------------------------------------------------------
    def judge_person(
        self,
        *,
        person_id: str,
        user_id: str,
        judge_type: str,
        persona_id: Optional[str] = None,
        ts: Optional[datetime] = None,
    ) -> None:
        weight = 1.0 if judge_type == "like" else -1.0
        ts_val = ts or datetime.now(timezone.utc)
        self._neo4j.execute_write(
            JUDGE_PERSON_WITH_PERSONA,
            {"person_id": person_id, "user_id": user_id, "persona_id": persona_id,
             "judge_type": judge_type, "weight": weight, "ts": ts_val},
        )
        logger.info(
            "Judge person=%s user=%s persona=%s type=%s",
            person_id, user_id, persona_id, judge_type,
        )

    # ------------------------------------------------------------------
    # Feed Delete (soft)
    # ------------------------------------------------------------------
    def delete_feed(
        self,
        *,
        feed_id: str,
        deleted_at: Optional[datetime] = None,
    ) -> None:
        ts_val = deleted_at or datetime.now(timezone.utc)
        self._neo4j.execute_write(
            SOFT_DELETE_FEED,
            {"feed_id": feed_id, "deleted_at": ts_val},
        )
        logger.info("Soft-deleted feed %s", feed_id)

    # ------------------------------------------------------------------
    # Comment Delete (soft)
    # ------------------------------------------------------------------
    def delete_comment(
        self,
        *,
        comment_id: str,
        deleted_at: Optional[datetime] = None,
    ) -> None:
        ts_val = deleted_at or datetime.now(timezone.utc)
        self._neo4j.execute_write(
            SOFT_DELETE_COMMENT,
            {"comment_id": comment_id, "deleted_at": ts_val},
        )
        logger.info("Soft-deleted comment %s", comment_id)


__all__ = ["OntologyLoader"]
