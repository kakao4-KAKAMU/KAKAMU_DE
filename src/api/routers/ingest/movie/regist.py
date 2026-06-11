"""POST /ingest/movie/regist"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from src.api.dependencies import AppContainer
from src.api.routers.deps import get_app_container
from src.api.routers.ingest.utils import enqueue
from src.api.schemas import IngestMovieEnvelope, IngestResponse

router = APIRouter()


@router.post("/ingest/movie/regist", response_model=IngestResponse)
def ingest_movie(
    env: IngestMovieEnvelope,
    container: AppContainer = Depends(get_app_container),
) -> IngestResponse:
    return enqueue(container, aggregate_type="movie", env=env)
