"""피드 본문 → FeedOntology Extractor."""

from __future__ import annotations

from src.extractor.base import LLMClient, OntologyChatPayload, OntologyExtractor
from src.ontology.prompts import build_feed_messages
from src.ontology.schema import FeedOntology


class FeedExtractor(OntologyExtractor[FeedOntology]):
    def __init__(self, llm: LLMClient) -> None:
        super().__init__(llm=llm, schema_cls=FeedOntology)

    def build_messages(
        self,
        *,
        feed_id: str,
        user_id: str,
        related_movie_id: str | None,
        known_movie_ids: list[str] | None,
        content: str,
    ) -> OntologyChatPayload:
        return build_feed_messages(
            feed_id=feed_id,
            user_id=user_id,
            related_movie_id=related_movie_id,
            known_movie_ids=known_movie_ids,
            content=content,
        )


__all__ = ["FeedExtractor"]
