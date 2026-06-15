"""POST /recommend"""

from __future__ import annotations

from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Header

from src.api.dependencies import AppContainer
from src.api.routers.deps import get_app_container
from src.api.schemas import RecommendRequest, MovieRecommendResponse

router = APIRouter()


@router.post(
    "/recommend/movie",
    response_model=MovieRecommendResponse,
    tags=["recommend"],
    summary="영화 하이브리드 추천",
    description="hybrid 방식으로 영화를 추천합니다.",
)
def recommend_movie(
    req: RecommendRequest,
    container: AppContainer = Depends(get_app_container),
) -> MovieRecommendResponse:
    intent = container.intent_resolver.resolve(req.query)
    embedding = container.embedder.embed(req.query)
    arm = container.policy.select_arm(context_key=req.user_id)
    params = {
        "user_id": req.user_id,
        "query_embedding": list(embedding),
        "query_keywords": list(intent.keywords),
        "query_themes": list(intent.themes),
        "query_moods": list(intent.moods),
        "top_k": req.top_k,
        "vec_top_k": req.vec_top_k,
        "max_toxicity": req.max_toxicity,
        **dict(arm.weights),
    }
    movies = container.template_executor.execute("hybrid_recommend", params)
    return MovieRecommendResponse(
        arm_id=arm.arm_id,
        movies=list(movies),
        keywords=list(intent.keywords),
        themes=list(intent.themes),
        moods=list(intent.moods),
    )
