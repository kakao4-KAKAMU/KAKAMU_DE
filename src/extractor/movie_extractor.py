"""영화 줄거리 → MoviePlotOntology Extractor."""

from __future__ import annotations

from src.extractor.base import LLMClient, OntologyExtractor
from src.ontology.prompts import build_movie_plot_messages
from src.ontology.schema import MoviePlotOntology


class MoviePlotExtractor(OntologyExtractor[MoviePlotOntology]):
    """짧은 줄거리에서 semantic / keyword 데이터를 추출한다."""

    def __init__(self, llm: LLMClient) -> None:
        super().__init__(llm=llm, schema_cls=MoviePlotOntology)

    def build_messages(
        self,
        *,
        movie_id: str,
        title: str,
        producing_year: int | None,
        country: str | None,
        genres: list[str] | None,
        plot: str,
    ) -> list[dict[str, str]]:
        return build_movie_plot_messages(
            movie_id=movie_id,
            title=title,
            producing_year=producing_year,
            country=country,
            genres=genres,
            plot=plot,
        )


__all__ = ["MoviePlotExtractor"]
