from __future__ import annotations
from typing import Any, Final
from textwrap import dedent
from .base import ONTOLOGY_SYSTEM_PROMPT

ONTOLOGY_FEED_CACHE_SALT: Final[str] = "ontology:feed:v1"

_FEED_SCHEMA_JSON: Final[dict[str, Any]] = {
    "name": "feed_knowledge_ontology",
    "strict": True,
    "schema": {
        "type": "object",
        "properties": {
            "schema_version": {"type": "string", "enum": ["1.0"]},
            "source_id": {"type": "string"},
            "language": {"type": "string"},
            "summary": {"type": "string"},
            "categories": {
                "type": "array",
                "items": {
                    "type": "string",
                    "enum": [
                        "review",
                        "recommendation",
                        "question",
                        "discussion",
                        "news",
                        "spoiler",
                        "theory",
                        "comparison",
                        "meta",
                        "off_topic",
                    ],
                },
            },
            "sentiment": {
                "type": "string",
                "enum": [
                    "very_negative",
                    "negative",
                    "neutral",
                    "positive",
                    "very_positive",
                ],
            },
            "sentiment_score": {"type": "number"},
            "emotions": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "tag": {
                            "type": "string",
                            "enum": [
                                "joy",
                                "sadness",
                                "anger",
                                "fear",
                                "disgust",
                                "surprise",
                                "nostalgia",
                                "empathy",
                                "excitement",
                                "boredom",
                                "confusion",
                                "admiration",
                            ],
                        },
                        "score": {"type": "number"},
                    },
                    "required": ["tag", "score"],
                    "additionalProperties": False,
                },
            },
            "keywords": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "term": {"type": "string"},
                        "normalized": {"type": "string"},
                        "weight": {"type": "number"},
                        "kind": {
                            "type": "string",
                            "enum": [
                                "entity",
                                "concept",
                                "theme",
                                "mood",
                                "trope",
                                "object",
                                "location",
                                "other",
                            ],
                        },
                    },
                    "required": ["term", "normalized", "weight", "kind"],
                    "additionalProperties": False,
                },
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
            "categories",
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
    [Feed 전용 가이드]
    - categories 는 다중 선택 가능. 명백히 1개라면 1개만 선택.
    - sentiment_score 와 sentiment 는 일관되어야 한다.
        very_negative ≈ -1.0 ~ -0.6
        negative      ≈ -0.6 ~ -0.2
        neutral       ≈ -0.2 ~ +0.2
        positive      ≈ +0.2 ~ +0.6
        very_positive ≈ +0.6 ~ +1.0
    - emotions 는 본문에서 명확히 드러난 감정 1~5개만 선택. 점수는 강도.
    - referenced_movie_ids 는 입력 메타의 known_movie_ids 에 포함된 ID 만 사용한다.
      메타에 없는 영화는 referenced_person_names 또는 keywords 로 처리.
    - contains_spoiler: 결말/반전을 직접 서술하면 true.
    - toxicity_score: 욕설/공격성/혐오표현 수위(0.1~1.0).
    """
).strip()


def build_feed_messages(
    *,
    feed_id: str,
    user_id: str,
    related_movie_id: str | None,
    known_movie_ids: list[str] | None,
    content: str,
) -> dict[str, Any]:
    """피드 본문 → FeedOntology 매핑용 messages.

    Args:
        feed_id: 피드 고유 ID.
        user_id: 작성자 user_id.
        related_movie_id: 피드가 명시적으로 연결한 영화 ID (있으면).
        known_movie_ids: 본문에서 참조 가능한 후보 movie_id 들(검색기로 사전 매칭한 결과).
        content: 정제 대상 피드 본문.
    """

    user_payload = dedent(
        f"""
        [피드 메타]
        - feed_id          : {feed_id}
        - user_id        : {user_id}
        - related_movie_id : {related_movie_id or "none"}
        - known_movie_ids  : {", ".join(known_movie_ids) if known_movie_ids else "none"}

        [원문 본문]
        \"\"\"
        {content.strip()}
        \"\"\"
        """
    ).strip()

    system_rules = dedent(
        f"""
        {_FEED_GUIDE}

        위 스키마에 정확히 맞춘 JSON 만 출력하라.
        """
    ).strip()

    return {
        "messages": [
            {"role": "system", "content": ONTOLOGY_SYSTEM_PROMPT},
            {"role": "system", "content": system_rules},
            {"role": "user", "content": user_payload},
        ],
        "response_format": {
            "type": "json_schema",
            "json_schema": _FEED_SCHEMA_JSON,
        },
        "cache_salt": ONTOLOGY_FEED_CACHE_SALT,
    }

__all__ = [
  "build_feed_messages",
]