from __future__ import annotations
from typing import Any, Final
from textwrap import dedent
from .base import ONTOLOGY_SYSTEM_PROMPT

ONTOLOGY_COMMENT_CACHE_SALT: Final[str] = "ontology:comment:v1"

_COMMENT_SCHEMA_JSON: Final[dict[str, Any]] = {
    "name": "comment_knowledge_ontology",
    "strict": True,
    "schema": {
        "type": "object",
        "properties": {
            "schema_version": {"type": "string", "enum": ["1.0"]},
            "source_id": {"type": "string"},
            "language": {"type": "string"},
            "summary": {"type": "string"},
            "intents": {
                "type": "array",
                "items": {
                    "type": "string",
                    "enum": [
                        "agree",
                        "disagree",
                        "question",
                        "answer",
                        "recommend",
                        "critique",
                        "appreciation",
                        "joke",
                        "spoiler_warning",
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
                        "tag": {"type": "string"},
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
            "targets_user_id": {"type": ["string", "null"]},
            "contains_spoiler": {"type": "boolean"},
            "toxicity_score": {"type": "number"},
        },
        "required": [
            "schema_version",
            "source_id",
            "language",
            "summary",
            "intents",
            "sentiment",
            "sentiment_score",
            "emotions",
            "keywords",
            "targets_user_id",
            "contains_spoiler",
            "toxicity_score",
        ],
        "additionalProperties": False,
    },
}


_COMMENT_GUIDE: Final[str] = dedent(
    """
    [Comment 전용 가이드]
    - 댓글은 짧을 수 있으므로 summary 는 원문이 1문장이면 원문을 그대로 사용해도 된다.
    - intents 다중 선택 가능. 의문문이면 question, "동의/공감" 표현이면 agree.
    - 다른 사용자(@언급/대댓글) 를 향한 경우 targets_user_id 를 채운다.
      mentioned_user_ids 메타에 후보가 있는 경우 그 중에서만 선택.
    - keywords 는 5개를 넘기지 않는다(짧은 텍스트에 과추출 금지).
    - toxicity_score: 욕설/공격성/혐오표현 수위(0.1~1.0).
    """
).strip()


def build_comment_messages(
    *,
    comment_id: str,
    feed_id: str,
    author_id: str,
    mentioned_user_ids: list[str] | None,
    parent_feed_summary: str | None,
    content: str,
) -> dict[str, Any]:
    """댓글 본문 → CommentOntology 매핑용 messages.

    Args:
        comment_id: 댓글 ID.
        feed_id: 부모 피드 ID.
        author_id: 댓글 작성자.
        mentioned_user_ids: @멘션된 후보 user_id 목록.
        parent_feed_summary: 부모 피드의 정제 요약(맥락 보강용). 없으면 None.
        content: 댓글 원문.
    """

    user_payload = dedent(
        f"""
        [댓글 메타]
        - comment_id        : {comment_id}
        - feed_id           : {feed_id}
        - author_id         : {author_id}
        - mentioned_user_ids: {", ".join(mentioned_user_ids) if mentioned_user_ids else "none"}

        [부모 피드 요약(맥락)]
        {parent_feed_summary or "(none)"}

        [원문 댓글]
        \"\"\"
        {content.strip()}
        \"\"\"
        """
    ).strip()

    system_rules = dedent(
        f"""
        {_COMMENT_GUIDE}

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
            "json_schema": _COMMENT_SCHEMA_JSON,
        },
        "cache_salt": ONTOLOGY_COMMENT_CACHE_SALT,
    }

__all__ = [
  "build_comment_messages",
]