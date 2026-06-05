from src.api.schemas.movie import IngestMoviePayload
from src.graph.loader import OntologyLoader
from src.extractor.movie_extractor import MoviePlotExtractor
from src.ingest.dispatcher.utils import Embedder, Handler

def build_movie_handler(
    *,
    extractor: MoviePlotExtractor,
    embedder: Embedder,
    loader: OntologyLoader,
) -> Handler:

    def _handler(payload: IngestMoviePayload) -> None:
        payload = IngestMoviePayload.model_validate(payload)
        movie_id = str(payload.movie_id)
        title = str(payload.title)
        plot = str(payload.plot or "")
        ontology = extractor.extract(
            movie_id=movie_id,
            title=title,
            producing_year=payload.producing_year,
            country=payload.country,
            genres=list(payload.genres or []),
            plot=plot,
        )
        embedding = embedder.embed(ontology.summary or plot)
        loader.upsert_movie(
            movie_id=movie_id,
            title=title,
            producing_year=payload.producing_year,
            country=payload.country,
            genres=list(payload.genres or []),
            plot_raw=plot,
            ontology=ontology,
            plot_embedding=embedding,
        )

    return _handler
