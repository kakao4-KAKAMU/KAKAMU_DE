from src.api.schemas.movie import IngestMoviePayload
from src.extractor.movie_extractor import MoviePlotExtractor
from src.graph.loader import OntologyLoader
from src.ingest.dispatcher.utils import Embedder, Handler


def build_movie_handler(
    *,
    extractor: MoviePlotExtractor,
    embedder: Embedder,
    loader: OntologyLoader,
) -> Handler:

    def _handler(payload: IngestMoviePayload) -> None:
        payload = IngestMoviePayload.model_validate(payload)
        plot = payload.plot or ""
        persons = [p.model_dump() for p in payload.persons]
        reviews = [r for r in payload.reviews if r.strip()]
        ontology = extractor.extract(
            movie_id=payload.movie_id,
            title=payload.title,
            producing_year=payload.producing_year,
            country=payload.country,
            genres=list(payload.genres),
            plot=plot,
            persons=persons,
            reviews=reviews,
        )
        embedding = embedder.embed(ontology.summary or plot)
        loader.upsert_movie(
            movie_id=payload.movie_id,
            title=payload.title,
            producing_year=payload.producing_year,
            country=payload.country,
            genres=list(payload.genres),
            plot_raw=plot,
            ontology=ontology,
            plot_embedding=embedding,
            persons=persons,
        )

    return _handler


__all__ = ["build_movie_handler"]
