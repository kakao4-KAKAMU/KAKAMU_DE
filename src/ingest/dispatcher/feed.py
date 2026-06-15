from src.api.schemas.feed import IngestFeedPayload
from src.extractor.feed_extractor import FeedExtractor
from src.graph.loader import OntologyLoader
from src.ingest.dispatcher.utils import Embedder, Handler


def build_feed_handler(
    *,
    extractor: FeedExtractor,
    embedder: Embedder,
    loader: OntologyLoader,
) -> Handler:

    def _handler(payload: IngestFeedPayload) -> None:
        payload = IngestFeedPayload.model_validate(payload)
        ontology = extractor.extract(
            feed_id=payload.feed_id,
            user_id=payload.user_id,
            related_movie_id=payload.related_movie_id,
            known_movie_ids=list(payload.known_movie_ids),
            content=payload.content,
        )
        embedding = embedder.embed(ontology.summary or payload.content)
        loader.upsert_feed(
            feed_id=payload.feed_id,
            user_id=payload.user_id,
            related_movie_id=payload.related_movie_id,
            content_raw=payload.content,
            ontology=ontology,
            summary_embedding=embedding,
            created_at=payload.created_at,
        )

    return _handler


__all__ = ["build_feed_handler"]
