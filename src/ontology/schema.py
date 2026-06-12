"""온톨로지 스키마 정의.

본 모듈은 LLM(또는 SLM) 의 구조화 출력을 강제하기 위한 Pydantic 스키마를 정의한다.

- 영화 줄거리 → MoviePlotOntology
- 피드 본문   → FeedOntology
- 댓글 본문   → CommentOntology

설계 원칙
---------
- SRP: 각 클래스는 단일 데이터 타입에 대한 표상만 담당한다.
- OCP: 카테고리/감정/관계 분류 체계는 Enum/Literal 로 정의하고 확장 시 Enum 추가만으로 대응한다.
- LSP: 모든 Ontology* 는 OntologyResult 를 상속해 동일한 직렬화/검증 인터페이스를 보장한다.
- ISP: Movie/Feed/Comment 각각 필요한 필드만 노출한다.
- DIP: 추출기(extractor)는 본 스키마(추상) 에만 의존하고, LLM 구현(구체) 에는 의존하지 않는다.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import List, Literal, Optional, TypeVar

from pydantic import BaseModel, Field, field_validator

_E = TypeVar("_E", bound=Enum)

SCHEMA_VERSION: Literal["1.1"] = "1.1"
SCHEMA_VERSION_VALUES: list[str] = [SCHEMA_VERSION]


def enum_values(enum_cls: type[_E]) -> list[str]:
    """str Enum 의 value 목록을 정의 순서대로 반환한다."""
    return [member.value for member in enum_cls]


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# 공통 (Enum / Common Models)
# ---------------------------------------------------------------------------


class Sentiment(str, Enum):
    """감정 분류 (5단계 valence)."""

    VERY_NEGATIVE = "very_negative"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"
    POSITIVE = "positive"
    VERY_POSITIVE = "very_positive"


SENTIMENT_VALUES: list[str] = enum_values(Sentiment)


class EmotionTag(str, Enum):
    """세부 감정 태그 (Ekman 기반 + 영화 도메인 보강)."""

    JOY = "joy"
    SADNESS = "sadness"
    ANGER = "anger"
    FEAR = "fear"
    DISGUST = "disgust"
    SURPRISE = "surprise"
    NOSTALGIA = "nostalgia"
    EMPATHY = "empathy"
    EXCITEMENT = "excitement"
    BOREDOM = "boredom"
    CONFUSION = "confusion"
    ADMIRATION = "admiration"


EMOTION_TAG_VALUES: list[str] = enum_values(EmotionTag)


class FeedCategory(str, Enum):
    """피드 글 특성 분류."""

    REVIEW = "review"  # 감상평
    RECOMMENDATION = "recommendation"  # 추천
    QUESTION = "question"  # 질문
    DISCUSSION = "discussion"  # 토론
    NEWS = "news"  # 뉴스/정보
    SPOILER = "spoiler"  # 스포일러 포함
    THEORY = "theory"  # 해석/이론
    COMPARISON = "comparison"  # 비교
    META = "meta"  # 메타(촬영기법/감독/배우)
    OFF_TOPIC = "off_topic"


FEED_CATEGORY_VALUES: list[str] = enum_values(FeedCategory)


class CommentTarget(str, Enum):
    """댓글이 향하는 대상."""

    FEED = "feed"
    PARENT_COMMENT = "parent_comment"


COMMENT_TARGET_VALUES: list[str] = enum_values(CommentTarget)


class CommentReaction(str, Enum):
    """댓글의 반응 유형."""

    POSITIVE = "positive"
    NEGATIVE = "negative"
    EMPATHY = "empathy"
    SUPPLEMENT = "supplement"


COMMENT_REACTION_VALUES: list[str] = enum_values(CommentReaction)


class KeywordKind(str, Enum):
    """영화 지표 키워드 분류."""

    ERA = "era"
    ENVIRONMENT = "environment"
    KEY_OBJECT = "key_object"
    SOURCE_FORM = "source_form"
    CULTURE_CODE = "culture_code"
    ENTITY = "entity"
    OTHER = "other"


KEYWORD_KIND_VALUES: list[str] = enum_values(KeywordKind)


class Keyword(BaseModel):
    """영화 지표·검색 anchor 가 되는 표준 키워드."""

    term: str = Field(..., description="원문에서 추출된 표면형(surface form)")
    normalized: str = Field(
        ..., description="정규화된 표제어. 영어 snake_case 또는 고유명 표기."
    )
    weight: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="해당 문서 내 중요도(0~1).",
    )
    kind: KeywordKind = Field(default=KeywordKind.OTHER, description="키워드의 종류(상위 분류).")

    @field_validator("term", "normalized")
    @classmethod
    def _strip(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("term/normalized must not be empty")
        return v


class EmotionScore(BaseModel):
    """감정 태그별 점수(0~1)."""

    tag: EmotionTag
    score: float = Field(..., ge=0.0, le=1.0)


class OntologyResult(BaseModel):
    """모든 온톨로지 출력의 공통 베이스."""

    schema_version: Literal["1.1"] = SCHEMA_VERSION
    created_at: datetime = Field(default_factory=_utcnow)
    source_id: str = Field(..., description="원본 문서의 고유 ID (movie_id/feed_id/comment_id)")
    language: str = Field(default="ko", description="원문 언어 (ISO 639-1).")


# ---------------------------------------------------------------------------
# Movie Plot Ontology
# ---------------------------------------------------------------------------


class MoviePlotOntology(OntologyResult):
    """영화 줄거리 정제 결과."""

    summary: str = Field(
        ..., description="2~3문장으로 요약된 의미 보존 줄거리."
    )
    themes: List[str] = Field(
        default_factory=list,
        description="영화의 주제. 폐쇄형 vocabulary (snake_case).",
    )
    moods: List[str] = Field(
        default_factory=list,
        description="영화의 분위기. 폐쇄형 vocabulary (snake_case).",
    )
    keywords: List[Keyword] = Field(
        default_factory=list, description="영화 지표 키워드."
    )
    toxicity_score: float = Field(
        default=0.0, ge=0.0, le=1.0, description="유해/공격성 점수(0~1)."
    )


# ---------------------------------------------------------------------------
# Feed Ontology
# ---------------------------------------------------------------------------


class FeedOntology(OntologyResult):
    """피드 본문 정제 결과."""

    summary: str = Field(..., description="피드 본문의 1~2문장 요약.")
    category: FeedCategory = Field(..., description="피드 글 특성.")
    sentiment: Sentiment = Field(..., description="전체 감정 극성.")
    sentiment_score: float = Field(
        ..., ge=-1.0, le=1.0, description="감정 점수. -1(매우 부정) ~ +1(매우 긍정)."
    )
    emotions: List[EmotionScore] = Field(
        default_factory=list, description="세부 감정 태그와 점수."
    )
    keywords: List[Keyword] = Field(
        default_factory=list, description="피드 핵심 키워드."
    )
    referenced_movie_ids: List[str] = Field(
        default_factory=list,
        description="본문에서 참조된 영화 ID(없으면 빈 리스트).",
    )
    referenced_person_names: List[str] = Field(
        default_factory=list,
        description="본문에서 언급된 감독/배우 등 인물명.",
    )
    contains_spoiler: bool = Field(
        default=False, description="스포일러 포함 여부."
    )
    toxicity_score: float = Field(
        default=0.0, ge=0.0, le=1.0, description="유해/공격성 점수(0~1)."
    )


# ---------------------------------------------------------------------------
# Comment Ontology
# ---------------------------------------------------------------------------


class CommentOntology(OntologyResult):
    """댓글 본문 정제 결과."""

    summary: str = Field(..., description="댓글의 1문장 요약(짧으면 원문 그대로 가능).")
    target: CommentTarget = Field(..., description="댓글이 향하는 대상.")
    reaction: CommentReaction = Field(..., description="댓글의 반응 유형.")
    sentiment: Sentiment = Field(..., description="전체 감정 극성.")
    sentiment_score: float = Field(..., ge=-1.0, le=1.0)
    emotions: List[EmotionScore] = Field(default_factory=list)
    keywords: List[Keyword] = Field(default_factory=list)
    targets_user_id: Optional[str] = Field(
        default=None,
        description="해당 댓글이 특정 사용자를 향한 경우 그 user_id.",
    )
    contains_spoiler: bool = Field(
        default=False, description="스포일러 포함 여부."
    )
    toxicity_score: float = Field(
        default=0.0, ge=0.0, le=1.0, description="유해/공격성 점수(0~1)."
    )


# ---------------------------------------------------------------------------
# Public Re-exports
# ---------------------------------------------------------------------------


__all__ = [
    "SCHEMA_VERSION",
    "SCHEMA_VERSION_VALUES",
    "Sentiment",
    "SENTIMENT_VALUES",
    "EmotionTag",
    "EMOTION_TAG_VALUES",
    "FeedCategory",
    "FEED_CATEGORY_VALUES",
    "CommentTarget",
    "COMMENT_TARGET_VALUES",
    "CommentReaction",
    "COMMENT_REACTION_VALUES",
    "Keyword",
    "KeywordKind",
    "KEYWORD_KIND_VALUES",
    "EmotionScore",
    "OntologyResult",
    "MoviePlotOntology",
    "FeedOntology",
    "CommentOntology",
    "enum_values",
]
