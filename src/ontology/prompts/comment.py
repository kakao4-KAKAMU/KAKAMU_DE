from __future__ import annotations
from typing import Any, Final
from textwrap import dedent
from .pipeline import OntologyPromptSpec

ONTOLOGY_COMMENT_CACHE_SALT: Final[str] = "ontology:comment:v1"

_COMMENT_SCHEMA_BASE: Final[dict[str, Any]] = {
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
            "genres": {"type": "array", "items": {"type": "string"}},
            "themes": {"type": "array", "items": {"type": "string"}},
            "moods": {"type": "array", "items": {"type": "string"}},
            "keywords": {
                "type": "array",
                "items": {"type": "object"},
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
            "genres",
            "themes",
            "moods",
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
    - genres/themes/moods 는 본문에서 드러난 경우에만 폐쇄형 vocabulary 에서 선택.
      근거 없으면 빈 배열.
    - 다른 사용자(@언급/대댓글) 를 향한 경우 targets_user_id 를 채운다.
      mentioned_user_ids 메타에 후보가 있는 경우 그 중에서만 선택.
    - keywords 는 5개를 넘기지 않는다(짧은 텍스트에 과추출 금지).
    - toxicity_score: 욕설/공격성/혐오표현 수위(0.1~1.0).
    """
).strip()

_SPEC = OntologyPromptSpec(
    name="comment",
    base_schema=_COMMENT_SCHEMA_BASE,
    guide=_COMMENT_GUIDE,
    cache_salt=ONTOLOGY_COMMENT_CACHE_SALT,
)


def get_comment_schema_json() -> dict[str, Any]:
    return _SPEC.schema_json()


def build_comment_messages(
    *,
    comment_id: str,
    feed_id: str,
    user_id: str,
    mentioned_user_ids: list[str] | None,
    parent_feed_summary: str | None,
    content: str,
) -> dict[str, Any]:
    """댓글 본문 → CommentOntology 매핑용 messages."""

    user_payload = dedent(
        f"""
        [댓글 메타]
        - comment_id        : {comment_id}
        - feed_id           : {feed_id}
        - user_id           : {user_id}
        - mentioned_user_ids: {", ".join(mentioned_user_ids) if mentioned_user_ids else "none"}

        [부모 피드 요약(맥락)]
        {parent_feed_summary or "(none)"}

        [원문 댓글]
        \"\"\"
        {content.strip()}
        \"\"\"
        """
    ).strip()

    return _SPEC.build_payload(user_payload=user_payload)


__all__ = [
    "ONTOLOGY_COMMENT_CACHE_SALT",
    "build_comment_messages",
    "get_comment_schema_json",
]
