from src.api.schemas.comment import IngestCommentPayload
from src.extractor.comment_extractor import CommentExtractor
from src.graph.loader import OntologyLoader
from src.ingest.dispatcher.utils import Embedder, Handler, _parse_dt

def build_comment_handler(
    *,
    extractor: CommentExtractor,
    embedder: Embedder,
    loader: OntologyLoader,
) -> Handler:

    def _handler(payload: IngestCommentPayload) -> None:
        payload = IngestCommentPayload.model_validate(payload)
        comment_id = str(payload.comment_id)
        feed_id = str(payload.feed_id)
        author_id = str(payload.author_id)
        content = str(payload.content or "")
        ontology = extractor.extract(
            comment_id=comment_id,
            feed_id=feed_id,
            author_id=author_id,
            mentioned_user_ids=list(payload.mentioned_user_ids or []),
            parent_comment_id=payload.parent_comment_id,
            content=content,
        )
        embedding = embedder.embed(ontology.summary or content)
        loader.upsert_comment(
            comment_id=comment_id,
            feed_id=feed_id,
            author_id=author_id,
            content_raw=content,
            ontology=ontology,
            summary_embedding=embedding,
            created_at=_parse_dt(payload.created_at),
        )

    return _handler
