"""사용자 질의 → 영화/피드 온톨로지 필터 분석용 프롬프트·JSON schema.

그래프 온톨로지 관계 (Cypher upsert 기준)
---------------------------------------
Movie
  - HAS_GENRE → Genre
  - HAS_THEME → Theme
  - HAS_MOOD → Mood
  - MENTIONS → Keyword (kind: era/environment/key_object/source_form/culture_code/entity/other)
  - HAS_PERSON → Person (job: director/actor/…)
  - PRODUCED_IN → Country
  - 속성: title, producing_year, country, plot_summary, toxicity_score

Feed
  - WRITTEN_BY → User
  - ABOUT_MOVIE → Movie
  - HAS_CATEGORY → Category (review/recommendation/question/…)
  - HAS_EMOTION → Emotion (tag, score)
  - MENTIONS → Keyword
  - 속성: summary, sentiment, sentiment_score, contains_spoiler, toxicity_score
"""

from __future__ import annotations

from textwrap import dedent
from typing import Any, Final

from src.ontology.prompts.pipeline import OntologyPromptSpec
from src.ontology.schema import (
    EMOTION_TAG_VALUES,
    FEED_CATEGORY_VALUES,
    KEYWORD_KIND_VALUES,
    SENTIMENT_VALUES,
)

QUERY_ANALYSIS_CACHE_SALT: Final[str] = "query_analysis:v1"

_KEYWORD_ITEM_SCHEMA: Final[dict[str, Any]] = {
    "type": "object",
    "properties": {
        "term": {"type": "string"},
        "normalized": {"type": "string"},
        "kind": {"type": "string", "enum": KEYWORD_KIND_VALUES},
    },
    "required": ["term", "normalized", "kind"],
    "additionalProperties": False,
}

_QUERY_ANALYSIS_SCHEMA_BASE: Final[dict[str, Any]] = {
    "name": "query_ontology_analysis",
    "strict": True,
    "schema": {
        "type": "object",
        "properties": {
            "intent_scope": {
                "type": "string",
                "enum": ["movie", "feed", "both", "none"],
            },
            "movie": {
                "type": "object",
                "properties": {
                    "genres": {"type": "array", "items": {"type": "string"}},
                    "themes": {"type": "array", "items": {"type": "string"}},
                    "moods": {"type": "array", "items": {"type": "string"}},
                    "keywords": {"type": "array", "items": _KEYWORD_ITEM_SCHEMA},
                    "person_names": {"type": "array", "items": {"type": "string"}},
                    # "person_jobs": {"type": "array", "items": {"type": "string"}},
                    "country": {"type": "string"},
                    "min_year": {"type": "integer"},
                    "max_year": {"type": "integer"},
                },
                "required": [
                    "genres",
                    "themes",
                    "moods",
                    "keywords",
                    "person_names",
                    # "person_jobs",
                    "country",
                    "min_year",
                    "max_year",
                ],
                "additionalProperties": False,
            },
            "feed": {
                "type": "object",
                "properties": {
                    "categories": {
                        "type": "array",
                        "items": {"type": "string", "enum": FEED_CATEGORY_VALUES},
                    },
                    "emotions": {
                        "type": "array",
                        "items": {"type": "string", "enum": EMOTION_TAG_VALUES},
                    },
                    "keywords": {"type": "array", "items": _KEYWORD_ITEM_SCHEMA},
                    "sentiment": {"type": "string", "enum": SENTIMENT_VALUES},
                    "contains_spoiler": {"type": "boolean"},
                    "related_movie_title": {"type": "string"},
                },
                "required": [
                    "categories",
                    "emotions",
                    "keywords",
                    "sentiment",
                    "contains_spoiler",
                    "related_movie_title",
                ],
                "additionalProperties": False,
            },
            "direct_reply_hint": {"type": "string"},
        },
        "required": ["intent_scope", "movie", "feed", "direct_reply_hint"],
        "additionalProperties": False,
    },
}

_QUERY_ANALYSIS_GUIDE: Final[str] = dedent(
    """
    [질의 분석 — Query Ontology Analysis]
    사용자 자연어 질의를 영화/피드 온톨로지 필터로 변환한다.

    [intent_scope 판단]
    - movie : 영화 작품 추천·정보·비교 등 영화 자체에 대한 질문
    - feed  : 감상평·후기·리뷰·게시글(피드) 추천·검색에 대한 질문
    - both  : 영화와 피드를 동시에 요구 (예: "이 영화 추천하고 후기도 보여줘")
    - none  : 영화/피드와 무관한 일반 대화·인사·시스템 질문

    [movie 필터 — Movie 온톨로지]
    - genres/themes/moods: 질의에서 드러난 장르·주제·무드. 근거 없으면 [].
    - keywords: 영화 지표(era/environment/key_object/source_form/culture_code/entity/other).
      themes/moods 와 중복 금지. normalized 는 snake_case.
    - person_names: 감독·배우 등 인물 언급 시 채운다.
    - country: 제작국 언급 시. 없으면 빈 문자열.
    - min_year/max_year: 연도 범위. 없으면 0.

    [feed 필터 — Feed 온톨로지]
    - categories: 글 특성(review/recommendation/question/discussion/news/spoiler/theory/comparison/meta/off_topic).
    - emotions: 본문에서 기대되는 감정 태그.
    - keywords: 구체 표현(인물·작품·소재). normalized 는 snake_case.
    - sentiment: 기대 감정 극성. 모호하면 "neutral".
    - contains_spoiler: 스포일러 피드를 원하면 true, 회피하면 false, 무관하면 false.
    - related_movie_title: 특정 영화 관련 피드 요청 시 제목. 없으면 빈 문자열.

    [none 일 때]
    - direct_reply_hint: 바로 응답할 때 참고할 한국어 힌트(1문장). 빈 문자열 가능.
    - movie/feed 필터는 모두 빈 값으로 둔다.
    """
).strip()

_SPEC = OntologyPromptSpec(
    name="query_analysis",
    base_schema=_QUERY_ANALYSIS_SCHEMA_BASE,
    guide=_QUERY_ANALYSIS_GUIDE,
    cache_salt=QUERY_ANALYSIS_CACHE_SALT,
    include_vocab_guide=True,
)


def get_query_analysis_schema_json() -> dict[str, Any]:
    return _SPEC.schema_json()


def build_query_analysis_messages(*, user_query: str) -> dict[str, Any]:
    """사용자 질의 → 온톨로지 필터 분석용 messages + response_format."""
    user_payload = dedent(
        f"""
        [사용자 질의]
        \"\"\"
        {user_query.strip()}
        \"\"\"
        """
    ).strip()
    return _SPEC.build_payload(user_payload=user_payload)


__all__ = [
    "QUERY_ANALYSIS_CACHE_SALT",
    "build_query_analysis_messages",
    "get_query_analysis_schema_json",
]
