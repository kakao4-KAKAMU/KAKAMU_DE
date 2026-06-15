"""POST /recommend/feed

영화 추천(``/recommend/movie``)과 동일한 hybrid 방식(벡터 유사도 + 키워드/테마/무드
부스트 + 사용자 선호 가중치)을 사용하되, 피드(감상/후기) 노드를 대상으로 한다.
"""

from __future__ import annotations

from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Header

from src.api.dependencies import AppContainer
from src.api.routers.deps import get_app_container
from src.api.schemas import FeedRecommendResponse, RecommendRequest
from src.recommend.context import (
    bandit_context_key,
    build_hybrid_recommend_params,
    resolve_persona_id,
)

router = APIRouter()


@router.post(
    "/recommend/feed",
    response_model=FeedRecommendResponse,
    tags=["recommend"],
    summary="피드 하이브리드 추천",
    description="hybrid 방식으로 감상/후기 피드를 추천합니다.",
)
def recommend_feed(
    req: RecommendRequest,
    container: AppContainer = Depends(get_app_container),
) -> FeedRecommendResponse:
    resolved_persona_id = resolve_persona_id(header=req.persona_id, body=req.persona_id)
    intent = container.intent_resolver.resolve(req.query)
    embedding = container.embedder.embed(req.query)
    context_key = bandit_context_key(req.user_id, resolved_persona_id)
    arm = container.policy.select_arm(context_key=context_key)
    params = build_hybrid_recommend_params(
        user_id=req.user_id,
        persona_id=resolved_persona_id,
        query_embedding=list(embedding),
        query_keywords=list(intent.keywords),
        query_themes=list(intent.themes),
        query_moods=list(intent.moods),
        top_k=req.top_k,
        vec_top_k=req.vec_top_k,
        max_toxicity=req.max_toxicity,
        weights=dict(arm.weights),
    )
    feeds = container.template_executor.execute(
        "hybrid_feed_recommend", params, fallback=False
    )
    return FeedRecommendResponse(
        arm_id=arm.arm_id,
        feeds=list(feeds),
        keywords=list(intent.keywords),
        themes=list(intent.themes),
        moods=list(intent.moods),
    )
