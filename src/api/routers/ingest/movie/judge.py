"""POST /ingest/movie/judge"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from src.api.dependencies import AppContainer
from src.api.routers.deps import get_app_container
from src.api.routers.ingest.utils import enqueue
from src.api.schemas import IngestMovieJudgeEnvelope, IngestResponse

router = APIRouter()


@router.post(
    "/ingest/movie/judge",
    response_model=IngestResponse,
    tags=["movie"],
    summary="영화 선호 판정",
    description="사용자의 영화 like/dislike 판정을 ingest outbox에 적재합니다.",
)
def ingest_movie_judge(
    env: IngestMovieJudgeEnvelope,
    container: AppContainer = Depends(get_app_container),
) -> IngestResponse:
    return enqueue(
        container,
        aggregate_type="movie_judge",
        aggregate_id=f"{env.payload.movie_id}_{env.payload.user_id}",
        env=env,
    )
