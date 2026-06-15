"""retrieve 노드: 매체별 하이브리드 추천 실행.

영화/피드 모두 동일한 hybrid 방식(벡터 유사도 + 키워드/테마/무드 부스트 +
사용자 선호 가중치)을 사용하며, 실행 템플릿만 매체에 따라 달라진다.

SOLID
-----
- SRP : 파라미터 구성과 템플릿 실행만 담당.
- DRY : 공통 파라미터 구성을 ``build_hybrid_recommend_params`` 로 위임.
"""

from __future__ import annotations

from src.chat.nodes.dependencies import DEFAULT_WEIGHTS, ChatGraphDependencies
from src.chat.state import ChatState
from src.recommend.context import build_hybrid_recommend_params


def _build_hybrid_params(state: ChatState, deps: ChatGraphDependencies) -> dict:
    weights = state.get("weights") or DEFAULT_WEIGHTS
    return build_hybrid_recommend_params(
        user_id=state.get("user_id", "anonymous"),
        persona_id=state.get("persona_id"),
        query_embedding=state.get("query_embedding") or [],
        query_keywords=state.get("keywords") or [],
        query_themes=state.get("themes") or [],
        query_moods=state.get("moods") or [],
        top_k=int(state.get("top_k") or deps.default_top_k),
        vec_top_k=int(state.get("vec_top_k") or deps.default_vec_top_k),
        max_toxicity=float(state.get("max_toxicity") or deps.default_max_toxicity),
        weights=weights,
    )


def retrieve_movies(state: ChatState, deps: ChatGraphDependencies) -> ChatState:
    params = _build_hybrid_params(state, deps)
    rows = deps.template_executor.execute(
        deps.movie_template_id, params, fallback=True
    )
    return {"retrieved": list(rows)}


def retrieve_feeds(state: ChatState, deps: ChatGraphDependencies) -> ChatState:
    params = _build_hybrid_params(state, deps)
    # 피드 추천은 영화(hybrid_recommend)로 fallback 하지 않는다.
    rows = deps.template_executor.execute(
        deps.feed_template_id, params, fallback=False
    )
    return {"retrieved": list(rows)}


__all__ = ["retrieve_movies", "retrieve_feeds"]
