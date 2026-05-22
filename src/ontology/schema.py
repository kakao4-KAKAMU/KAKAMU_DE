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

from datetime import datetime
from enum import Enum
from typing import List, Literal, Optional

from pydantic import BaseModel, Field, field_validator


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


class FeedCategory(str, Enum):
    """피드 카테고리(주제) 분류."""

    REVIEW = "review"                 # 감상평
    RECOMMENDATION = "recommendation" # 추천
    QUESTION = "question"             # 질문
    DISCUSSION = "discussion"         # 토론
    NEWS = "news"                     # 뉴스/정보
    SPOILER = "spoiler"               # 스포일러 포함
    THEORY = "theory"                 # 해석/이론
    COMPARISON = "comparison"         # 비교
    META = "meta"                     # 메타(촬영기법/감독/배우)
    OFF_TOPIC = "off_topic"


class CommentIntent(str, Enum):
    """댓글 의도 분류."""

    AGREE = "agree"
    DISAGREE = "disagree"
    QUESTION = "question"
    ANSWER = "answer"
    RECOMMEND = "recommend"
    CRITIQUE = "critique"
    APPRECIATION = "appreciation"
    JOKE = "joke"
    SPOILER_WARNING = "spoiler_warning"
    OFF_TOPIC = "off_topic"


class Keyword(BaseModel):
    """semantic / keyword 양쪽에서 anchor 가 되는 표준 키워드."""

    term: str = Field(..., description="원문에서 추출된 표면형(surface form)")
    normalized: str = Field(
        ..., description="정규화된 표제어. 동의어/표기 통일 후의 lemma."
    )
    weight: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="해당 문서 내 중요도(0~1). TF-IDF 또는 LLM 판단치.",
    )
    kind: Literal[
        "entity", "concept", "theme", "mood", "trope", "object", "location", "other"
    ] = Field(default="concept", description="키워드의 종류(상위 분류).")

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

    schema_version: Literal["1.0"] = "1.0"
    created_at: datetime = Field(default_factory=datetime.utcnow)
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
        description="영화의 주제(예: '복수', '성장', '구원'). 정규화된 표제어.",
    )
    moods: List[str] = Field(
        default_factory=list,
        description="영화의 분위기(예: '잔잔한', '긴장감', '몽환적'). 정규화 표제어.",
    )
    tropes: List[str] = Field(
        default_factory=list,
        description="장르 클리셰/트로프(예: 'time_loop', 'anti_hero').",
    )
    keywords: List[Keyword] = Field(
        default_factory=list, description="검색 anchor 가 되는 핵심 키워드."
    )
    characters: List[str] = Field(
        default_factory=list, description="주요 등장인물의 역할/이름."
    )
    locations: List[str] = Field(
        default_factory=list, description="주요 배경(시대/공간)."
    )
    target_audience: List[str] = Field(
        default_factory=list,
        description="추정 타겟 관객층 태그(예: 'family', 'cinephile', 'teen').",
    )


# ---------------------------------------------------------------------------
# Feed Ontology
# ---------------------------------------------------------------------------


class FeedOntology(OntologyResult):
    """피드 본문 정제 결과."""

    summary: str = Field(..., description="피드 본문의 1~2문장 요약.")
    categories: List[FeedCategory] = Field(
        default_factory=list, description="피드의 카테고리(다중 선택 가능)."
    )
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
    intents: List[CommentIntent] = Field(
        default_factory=list, description="댓글의 의도(다중 가능)."
    )
    sentiment: Sentiment = Field(..., description="전체 감정 극성.")
    sentiment_score: float = Field(..., ge=-1.0, le=1.0)
    emotions: List[EmotionScore] = Field(default_factory=list)
    keywords: List[Keyword] = Field(default_factory=list)
    targets_user_id: Optional[str] = Field(
        default=None,
        description="해당 댓글이 특정 사용자를 향한 경우 그 user_id.",
    )
    contains_spoiler: bool = Field(default=False)
    toxicity_score: float = Field(default=0.0, ge=0.0, le=1.0)


# ---------------------------------------------------------------------------
# Public Re-exports
# ---------------------------------------------------------------------------


__all__ = [
    "Sentiment",
    "EmotionTag",
    "FeedCategory",
    "CommentIntent",
    "Keyword",
    "EmotionScore",
    "OntologyResult",
    "MoviePlotOntology",
    "FeedOntology",
    "CommentOntology",
]
