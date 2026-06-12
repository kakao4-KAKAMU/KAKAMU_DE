from __future__ import annotations
from typing import Any, Final
from textwrap import dedent

# ---------------------------------------------------------------------------
# 사용자 의도 → Cypher 매핑 프롬프트
# ---------------------------------------------------------------------------

_USER_INTENT_TO_CYPHER_SYSTEM_PROMPT: Final[str] = dedent(
    """
    너는 사용자의 자연어 추천 요청을, 미리 등록된 Cypher 템플릿 중 하나를 선택하고
  파라미터만 채우는 "Recommendation Template Planner" 다.
  raw Cypher 를 직접 작성하지 마라.

    [등록된 template_id]
    - hybrid_recommend: 영화 하이브리드 추천 (기본)
    - feed_about_movie: 특정 영화 관련 피드
    - similar_movie_by_theme: 테마 유사 영화
    - recent_feeds_positive: 긍정 피드 최신순
    - user_preference_summary: 사용자 선호 요약

    [출력 규칙]
    - 출력은 단일 JSON:
      {"template_id": "...", "params": {...}, "reasoning": "..."}
    - params 의 키는 템플릿이 요구하는 이름만 사용.
    - hybrid_recommend 기본 params 예:
      user_id, query_embedding (float[]), query_keywords, query_themes,
      query_moods, top_k, vec_top_k, w_vec, w_kw, w_theme, w_mood, w_user
    - 모르는 값은 빈 리스트/기본 가중치로 채운다.
    """
).strip()


def build_user_intent_messages(
    *,
    user_id: str,
    user_query: str,
    top_k: int = 20,
) -> list[dict[str, str]]:
    """사용자 자연어 추천 요청 → Cypher 변환 messages."""

    user_payload = dedent(
        f"""
        [요청]
        - user_id : {user_id}
        - top_k   : {top_k}
        - query   : "{user_query.strip()}"

        위 요청에 맞는 template_id 와 params 를 JSON 으로 반환하라.
        영화 추천이면 hybrid_recommend 를 우선 선택하라.
        """
    ).strip()

    return [
        {"role": "system", "content": _USER_INTENT_TO_CYPHER_SYSTEM_PROMPT},
        {"role": "user", "content": user_payload},
    ]

__all__ = [
  "build_user_intent_messages",
]
