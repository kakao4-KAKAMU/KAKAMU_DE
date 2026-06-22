"""추천 Persona 컨텍스트 유틸.

SOLID
-----
- SRP : Persona ID 해석과 Bandit context_key 생성만 담당.
- DRY : API 라우터와 LangGraph 노드가 동일 규칙을 공유한다.
"""

from __future__ import annotations

from typing import Any, Mapping, Optional


def resolve_persona_id(
    *,
    header: Optional[str] = None,
    body: Optional[str] = None,
) -> Optional[str]:
    """``X-Persona-Id`` 헤더와 body ``persona_id`` 를 병합한다.

    헤더가 우선이며, 없으면 body 값을 사용한다.
    """
    for value in (header, body):
        if value is not None:
            text = str(value).strip()
            if text:
                return text
    return None


def bandit_context_key(user_id: str, persona_id: Optional[str] = None) -> str:
    """Bandit posterior 스코프 키를 생성한다."""
    if persona_id:
        return f"{user_id}:{persona_id}"
    return user_id


def build_hybrid_recommend_params(
    *,
    user_id: str,
    persona_id: Optional[str],
    query_embedding: list[float],
    query_keywords: list[str],
    query_themes: list[str],
    query_moods: list[str],
    top_k: int,
    vec_top_k: int,
    max_toxicity: float,
    weights: Mapping[str, float],
) -> dict[str, Any]:
    """hybrid_recommend / hybrid_feed_recommend 공통 Cypher 파라미터."""
    return {
        "user_id": user_id,
        "persona_id": persona_id,
        "query_embedding": list(query_embedding),
        "query_keywords": list(query_keywords),
        "query_themes": list(query_themes),
        "query_moods": list(query_moods),
        "top_k": top_k,
        "vec_top_k": vec_top_k,
        "max_toxicity": max_toxicity,
        **dict(weights),
    }


def build_chat_movie_filter_params(
    *,
    user_id: str,
    persona_id: Optional[str],
    query_embedding: list[float],
    query_keywords: list[str],
    query_themes: list[str],
    query_moods: list[str],
    query_genres: list[str],
    query_person_names: list[str],
    query_person_jobs: list[str],
    filter_country: str,
    min_year: int,
    max_year: int,
    top_k: int,
    vec_top_k: int,
    max_toxicity: float,
    weights: Mapping[str, float],
) -> dict[str, Any]:
    """``chat_movie_filter`` 템플릿용 Cypher 파라미터."""
    return {
        **build_hybrid_recommend_params(
            user_id=user_id,
            persona_id=persona_id,
            query_embedding=query_embedding,
            query_keywords=query_keywords,
            query_themes=query_themes,
            query_moods=query_moods,
            top_k=top_k,
            vec_top_k=vec_top_k,
            max_toxicity=max_toxicity,
            weights=weights,
        ),
        "query_genres": list(query_genres),
        "query_person_names": list(query_person_names),
        "query_person_jobs": list(query_person_jobs),
        "filter_country": str(filter_country).lower(),
        "min_year": int(min_year),
        "max_year": int(max_year),
    }


def build_chat_feed_filter_params(
    *,
    user_id: str,
    persona_id: Optional[str],
    query_embedding: list[float],
    query_keywords: list[str],
    query_themes: list[str],
    query_moods: list[str],
    query_categories: list[str],
    query_emotions: list[str],
    filter_sentiment: str,
    include_spoiler: bool,
    related_movie_title: str,
    top_k: int,
    vec_top_k: int,
    max_toxicity: float,
    weights: Mapping[str, float],
) -> dict[str, Any]:
    """``chat_feed_filter`` 템플릿용 Cypher 파라미터."""
    return {
        **build_hybrid_recommend_params(
            user_id=user_id,
            persona_id=persona_id,
            query_embedding=query_embedding,
            query_keywords=query_keywords,
            query_themes=query_themes,
            query_moods=query_moods,
            top_k=top_k,
            vec_top_k=vec_top_k,
            max_toxicity=max_toxicity,
            weights=weights,
        ),
        "query_categories": list(query_categories),
        "query_emotions": list(query_emotions),
        "filter_sentiment": filter_sentiment,
        "include_spoiler": include_spoiler,
        "related_movie_title": related_movie_title,
    }


__all__ = [
    "bandit_context_key",
    "build_chat_feed_filter_params",
    "build_chat_movie_filter_params",
    "build_hybrid_recommend_params",
    "resolve_persona_id",
]
