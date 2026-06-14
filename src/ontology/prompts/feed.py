from __future__ import annotations
from typing import Any, Final
from textwrap import dedent
from .pipeline import OntologyPromptSpec

from src.ontology.schema import (
    EMOTION_TAG_VALUES,
    FEED_CATEGORY_VALUES,
    SCHEMA_VERSION_VALUES,
    SENTIMENT_VALUES,
)

ONTOLOGY_FEED_CACHE_SALT: Final[str] = "ontology:feed:v3"

_FEED_SCHEMA_BASE: Final[dict[str, Any]] = {
    "name": "feed_knowledge_ontology",
    "strict": True,
    "schema": {
        "type": "object",
        "properties": {
            "schema_version": {"type": "string", "enum": SCHEMA_VERSION_VALUES},
            "source_id": {"type": "string"},
            "language": {"type": "string"},
            "summary": {"type": "string"},
            "category": {"type": "string", "enum": FEED_CATEGORY_VALUES},
            "sentiment": {"type": "string", "enum": SENTIMENT_VALUES},
            "sentiment_score": {"type": "number"},
            "emotions": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "tag": {
                            "type": "string",
                            "enum": EMOTION_TAG_VALUES,
                        },
                        "score": {"type": "number"},
                    },
                    "required": ["tag", "score"],
                    "additionalProperties": False,
                },
            },
            "keywords": {
                "type": "array",
                "items": {"type": "object"},
            },
            "referenced_movie_ids": {"type": "array", "items": {"type": "string"}},
            "referenced_person_names": {
                "type": "array",
                "items": {"type": "string"},
            },
            "contains_spoiler": {"type": "boolean"},
            "toxicity_score": {"type": "number"},
        },
        "required": [
            "schema_version",
            "source_id",
            "language",
            "summary",
            "category",
            "sentiment",
            "sentiment_score",
            "emotions",
            "keywords",
            "referenced_movie_ids",
            "referenced_person_names",
            "contains_spoiler",
            "toxicity_score",
        ],
        "additionalProperties": False,
    },
}


_FEED_GUIDE: Final[str] = dedent(
    """
    [Feed]
    - category: 글 특성 1개만 선택.
        - review: 감상평
        - recommendation: 추천
        - question: 질문
        - discussion: 토론
        - news: 뉴스/정보
        - spoiler: 스포일러 포함
        - theory: 해석/이론
        - comparison: 비교
        - meta: 메타(촬영기법/감독/배우)
        - off_topic: 관련 없음
    - sentiment/sentiment_score 일관 유지.
    - emotions: 본문에서 드러난 감정 1~5개.
    - keywords: 본문의 구체 표현(인물·작품·소재 등). 5~10개 권장.
    - referenced_movie_ids: known_movie_ids 에 있는 ID 만.
    - contains_spoiler: 결말/반전 직접 서술 시 true.
    - toxicity_score: 욕설/공격성/혐오 수위(0.0~1.0).
    """
).strip()

_SPEC = OntologyPromptSpec(
    name="feed",
    base_schema=_FEED_SCHEMA_BASE,
    guide=_FEED_GUIDE,
    cache_salt=ONTOLOGY_FEED_CACHE_SALT,
    include_vocab_guide=False,
)


def get_feed_schema_json() -> dict[str, Any]:
    return _SPEC.schema_json()


def build_feed_messages(
    *,
    feed_id: str,
    user_id: str,
    related_movie_id: str | None,
    known_movie_ids: list[str] | None,
    content: str,
) -> dict[str, Any]:
    """피드 본문 → FeedOntology 매핑용 messages."""

    user_payload = dedent(
        f"""
        [피드 메타]
        - feed_id          : {feed_id}
        - user_id          : {user_id}
        - related_movie_id : {related_movie_id or "none"}
        - known_movie_ids  : {", ".join(known_movie_ids) if known_movie_ids else "none"}

        [원문 본문]
        \"\"\"
        {content.strip()}
        \"\"\"
        """
    ).strip()

    return _SPEC.build_payload(user_payload=user_payload, frequency_penalty=0.5)


__all__ = [
    "ONTOLOGY_FEED_CACHE_SALT",
    "build_feed_messages",
    "get_feed_schema_json",
]
