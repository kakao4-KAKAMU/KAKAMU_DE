"""댓글 본문 → CommentOntology Extractor."""

from __future__ import annotations

from src.extractor.base import LLMClient, OntologyChatPayload, OntologyExtractor
from src.ontology.prompts import build_comment_messages
from src.ontology.schema import CommentOntology


class CommentExtractor(OntologyExtractor[CommentOntology]):
    def __init__(self, llm: LLMClient) -> None:
        super().__init__(llm=llm, schema_cls=CommentOntology)

    def build_messages(
        self,
        *,
        comment_id: str,
        feed_id: str,
        user_id: str,
        mentioned_user_ids: list[str] | None,
        parent_feed_summary: str | None,
        parent_comment_summary: str | None = None,
        content: str,
    ) -> OntologyChatPayload:
        return build_comment_messages(
            comment_id=comment_id,
            feed_id=feed_id,
            user_id=user_id,
            mentioned_user_ids=mentioned_user_ids,
            parent_feed_summary=parent_feed_summary,
            parent_comment_summary=parent_comment_summary,
            content=content,
        )


__all__ = ["CommentExtractor"]
