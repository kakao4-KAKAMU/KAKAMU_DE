from __future__ import annotations
from typing import Any, Final
from textwrap import dedent
from .pipeline import OntologyPromptSpec

ONTOLOGY_FEED_CACHE_SALT: Final[str] = "ontology:feed:v1"

_FEED_SCHEMA_BASE: Final[dict[str, Any]] = {
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
            "genres": {"type": "array", "items": {"type": "string"}},
            "themes": {"type": "array", "items": {"type": "string"}},
            "moods": {"type": "array", "items": {"type": "string"}},
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
            "categories",
            "sentiment",
            "sentiment_score",
            "emotions",
            "genres",
            "themes",
            "moods",
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
    - genres/themes/moods 는 본문에서 드러난 경우에만 폐쇄형 vocabulary 에서 선택.
      근거 없으면 빈 배열.
    - referenced_movie_ids 는 입력 메타의 known_movie_ids 에 포함된 ID 만 사용한다.
      메타에 없는 영화는 referenced_person_names 또는 keywords 로 처리.
    - contains_spoiler: 결말/반전을 직접 서술하면 true.
    - toxicity_score: 욕설/공격성/혐오표현 수위(0.1~1.0).
    """
).strip()

_SPEC = OntologyPromptSpec(
    name="feed",
    base_schema=_FEED_SCHEMA_BASE,
    guide=_FEED_GUIDE,
    cache_salt=ONTOLOGY_FEED_CACHE_SALT,
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
        - user_id        : {user_id}
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
