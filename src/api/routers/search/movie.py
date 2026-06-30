"""POST /search/movie/title"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from src.api.dependencies import AppContainer
from src.api.routers.deps import get_app_container
from src.api.schemas.search import (
    MovieTitleSearchItem,
    MovieTitleSearchRequest,
    MovieTitleSearchResponse,
)
from src.graph.fulltext import escape_fulltext_query

router = APIRouter()


@router.post(
    "/search/movie/title",
    response_model=MovieTitleSearchResponse,
    tags=["search"],
    summary="영화 제목 fulltext 검색",
    description="MovieTitle 노드의 title 필드를 fulltext 인덱스로 검색합니다.",
)
def search_movie_by_title(
    req: MovieTitleSearchRequest,
    container: AppContainer = Depends(get_app_container),
) -> MovieTitleSearchResponse:
    rows = container.template_executor.execute(
        "movie_title_search",
        {
            "query": escape_fulltext_query(req.query),
            "country": req.country,
            "top_k": req.top_k,
        },
    )
    movies = [
        MovieTitleSearchItem(
            movie_id=str(row["movie_id"]),
            title=str(row["title"]),
            matched_title=str(row["matched_title"]),
            title_country=str(row["title_country"]),
            score=float(row["score"]),
        )
        for row in rows
    ]
    return MovieTitleSearchResponse(movies=movies)


__all__ = ["router"]
