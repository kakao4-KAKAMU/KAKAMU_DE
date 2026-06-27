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
        known_movie_plot_raws: str | None = None,
        content: str,
    ) -> OntologyChatPayload:
        return build_feed_messages(
            known_movie_plot_raws=known_movie_plot_raws,
            content=content,
        )


__all__ = ["FeedExtractor"]
