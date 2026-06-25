from __future__ import annotations
from typing import Any, Final
from textwrap import dedent
from .pipeline import OntologyPromptSpec

from src.ontology.schema import CommentOntology, build_llm_json_schema

ONTOLOGY_COMMENT_CACHE_SALT: Final[str] = "ontology:comment:v3"

_COMMENT_SCHEMA_BASE: Final[dict[str, Any]] = build_llm_json_schema(
    CommentOntology,
    name="comment_knowledge_ontology",
)


_COMMENT_GUIDE: Final[str] = dedent(
    """
    [Comment]
    - target: feed=피드에 대한 댓글, parent_comment=부모 댓글에 대한 대댓글.
    - reaction: positive/negative/empathy=판단·공감, supplement=보충 설명.
    - summary: 1문장. 짧으면 원문 그대로 가능.
    - sentiment/sentiment_score 일관 유지.
    - keywords: 5개 이하. 구체 표현만.
    - targets_user_id: @언급/대댓글 시 mentioned_user_ids 중에서만 선택.
    - toxicity_score: 욕설/공격성/혐오 수위(0.0~1.0).
    """
).strip()

_SPEC = OntologyPromptSpec(
    name="comment",
    base_schema=_COMMENT_SCHEMA_BASE,
    guide=_COMMENT_GUIDE,
    cache_salt=ONTOLOGY_COMMENT_CACHE_SALT,
    include_vocab_guide=False,
    genre_fields=(),
    theme_fields=(),
    mood_fields=(),
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
    parent_comment_summary: str | None = None,
    content: str,
) -> dict[str, Any]:
    """댓글 본문 → CommentOntology 매핑용 messages."""

    parent_comment_section = (
        dedent(
            f"""
            [부모 댓글 요약(맥락)]
            {parent_comment_summary.strip()}
            """
        ).strip()
        if parent_comment_summary
        else ""
    )

    user_payload = dedent(
        f"""
        [댓글 메타]
        - comment_id        : {comment_id}
        - feed_id           : {feed_id}
        - user_id           : {user_id}
        - mentioned_user_ids: {", ".join(mentioned_user_ids) if mentioned_user_ids else "none"}

        [부모 피드 요약(맥락)]
        {parent_feed_summary or "(none)"}
        {parent_comment_section}

        [원문 댓글]
        \"\"\"
        {content.strip()}
        \"\"\"
        """
    ).strip()

    return _SPEC.build_payload(user_payload=user_payload, frequency_penalty=0.5)


__all__ = [
    "ONTOLOGY_COMMENT_CACHE_SALT",
    "build_comment_messages",
    "get_comment_schema_json",
]
