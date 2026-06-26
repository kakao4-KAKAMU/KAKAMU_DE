from src.api.schemas.feed import IngestFeedPayload
from src.extractor.feed_extractor import FeedExtractor
from src.graph.context_reader import MoviePlotReader, NullMoviePlotReader
from src.graph.loader import OntologyLoader
from src.ingest.dispatcher.utils import Embedder, Handler


def build_feed_handler(
    *,
    extractor: FeedExtractor,
    embedder: Embedder,
    loader: OntologyLoader,
    movie_plot_reader: MoviePlotReader | None = None,
) -> Handler:
    reader = movie_plot_reader or NullMoviePlotReader()

    def _handler(payload: IngestFeedPayload) -> None:
        payload = IngestFeedPayload.model_validate(payload)
        related_movie_plot_raw = (
            reader.get_plot_raw(payload.related_movie_id)
            if payload.related_movie_id
            else None
        )
        ontology = extractor.extract(
            feed_id=payload.feed_id,
            user_id=payload.user_id,
            related_movie_id=payload.related_movie_id,
            known_movie_ids=list(payload.known_movie_ids),
            related_movie_plot_raw=related_movie_plot_raw,
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
