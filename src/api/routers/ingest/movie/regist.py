"""POST /ingest/movie/regist"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from src.api.dependencies import AppContainer
from src.api.routers.deps import get_app_container
from src.api.routers.ingest.utils import enqueue
from src.api.schemas import IngestMovieEnvelope, IngestResponse

router = APIRouter()


@router.post(
    "/ingest/movie/regist",
    response_model=IngestResponse,
    tags=["ingest", "movie"],
    summary="영화 등록",
    description="영화 메타데이터와 줄거리를 ingest outbox에 적재합니다. 워커가 온톨로지 추출 후 지식 그래프에 반영합니다.",
)
def ingest_movie(
    env: IngestMovieEnvelope,
    container: AppContainer = Depends(get_app_container),
) -> IngestResponse:
    return enqueue(
        container, aggregate_type="movie", aggregate_id=env.payload.movie_id, env=env
    )
