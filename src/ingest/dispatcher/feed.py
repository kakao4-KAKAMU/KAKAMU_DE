from src.api.schemas.feed import IngestFeedPayload
from src.extractor.feed_extractor import FeedExtractor
from src.graph.loader import OntologyLoader
from src.ingest.dispatcher.utils import Embedder, Handler, _parse_dt

def build_feed_handler(
    *,
    extractor: FeedExtractor,
    embedder: Embedder,
    loader: OntologyLoader,
) -> Handler:

    def _handler(payload: IngestFeedPayload) -> None:
        payload = IngestFeedPayload.model_validate(payload)
        feed_id = str(payload.feed_id)
        user_id = str(payload.user_id)
        content = str(payload.content or "")
        ontology = extractor.extract(
            feed_id=feed_id,
            user_id=user_id,
            related_movie_id=payload.related_movie_id,
            known_movie_ids=list(payload.known_movie_ids or []),
            content=content,
        )
        embedding = embedder.embed(ontology.summary or content)
        loader.upsert_feed(
            feed_id=feed_id,
            user_id=user_id,
            related_movie_id=payload.related_movie_id,
            content_raw=content,
            ontology=ontology,
            summary_embedding=embedding,
            created_at=_parse_dt(payload.created_at),
        )

    return _handler

__all__ = ["build_feed_handler"]