from src.api.schemas.comment import IngestCommentPayload
from src.extractor.comment_extractor import CommentExtractor
from src.graph.loader import OntologyLoader
from src.ingest.dispatcher.utils import Embedder, Handler


def build_comment_handler(
    *,
    extractor: CommentExtractor,
    embedder: Embedder,
    loader: OntologyLoader,
) -> Handler:

    def _handler(payload: IngestCommentPayload) -> None:
        payload = IngestCommentPayload.model_validate(payload)
        ontology = extractor.extract(
            comment_id=payload.comment_id,
            feed_id=payload.feed_id,
            user_id=payload.user_id,
            mentioned_user_ids=list(payload.mentioned_user_ids),
            parent_feed_summary=payload.parent_feed_summary,
            parent_comment_summary=payload.parent_comment_summary,
            content=payload.content,
        )
        embedding = embedder.embed(ontology.summary or payload.content)
        loader.upsert_comment(
            comment_id=payload.comment_id,
            feed_id=payload.feed_id,
            user_id=payload.user_id,
            parent_comment_id=payload.parent_comment_id,
            content_raw=payload.content,
            ontology=ontology,
            summary_embedding=embedding,
            created_at=payload.created_at,
        )

    return _handler


__all__ = ["build_comment_handler"]
