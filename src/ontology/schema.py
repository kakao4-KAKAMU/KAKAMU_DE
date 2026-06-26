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

from copy import deepcopy
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Iterable, List, Literal, Mapping, Optional, TypeVar, Final

from pydantic import BaseModel, Field, field_validator, ConfigDict

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


GENRE_VALUES: Final[list[str]] = [
    "SF",
    "가족",
    "갱스터",
    "계몽",
    "공포",
    "공포(호러)",
    "과학",
    "교육",
    "군사",
    "기독교 애니메이션",
    "기록",
    "기업ㆍ기관ㆍ단체",
    "느와르",
    "다부작",
    "동성애",
    "드라마",
    "로드무비",
    "멜로/로맨스",
    "멜로드라마",
    "모험",
    "무협",
    "문예",
    "문화",
    "뮤지컬",
    "뮤직",
    "미스터리",
    "반공/분단",
    "범죄",
    "사회",
    "사회물(경향)",
    "서부",
    "스릴러",
    "스포츠",
    "시대극/사극",
    "신파",
    "실험",
    "아동",
    "애니메이션",
    "액션",
    "어드벤처",
    "에로",
    "역사",
    "연쇄극",
    "예술",
    "옴니버스",
    "인권",
    "인물",
    "자연ㆍ환경",
    "재난",
    "전기",
    "전쟁",
    "종교",
    "지역",
    "첩보",
    "청춘영화",
    "코메디",
    "판타지",
    "하이틴(고교)",
    "합작(번안물)",
    "해양액션",
    "활극",
]

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
    model_config = ConfigDict(use_enum_values=True)

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


def keyword_search_terms(
    keywords: Iterable[Keyword | str | Mapping[str, Any]] | None,
) -> list[str]:
    """Keyword/Pydantic/dict/str → Cypher ``query_keywords`` 용 normalized term 리스트."""
    terms: list[str] = []
    seen: set[str] = set()
    for item in keywords or []:
        token = ""
        if isinstance(item, Keyword):
            token = item.normalized.strip() or item.term.strip()
        elif isinstance(item, str):
            token = item.strip()
        elif isinstance(item, Mapping):
            normalized = str(item.get("normalized") or "").strip()
            term = str(item.get("term") or "").strip()
            token = normalized or term
        if token and token not in seen:
            seen.add(token)
            terms.append(token)
    return terms


class EmotionScore(BaseModel):
    """감정 태그별 점수(0~1)."""
    model_config = ConfigDict(use_enum_values=True)

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
    model_config = ConfigDict(use_enum_values=True)

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
    model_config = ConfigDict(use_enum_values=True)

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
    model_config = ConfigDict(use_enum_values=True)

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
# Query Ontology Analysis (chat filter)
# ---------------------------------------------------------------------------


class PersonJob(str, Enum):
    """질의 분석 시 인물 역할 필터."""

    DIRECTOR = "director"
    ACTOR = "actor"


PERSON_JOB_VALUES: list[str] = enum_values(PersonJob)


class MovieQueryFilterOntology(BaseModel):
    """사용자 질의에서 추출한 영화 온톨로지 필터."""

    model_config = ConfigDict(use_enum_values=True)

    genres: List[str] = Field(default_factory=list)
    themes: List[str] = Field(default_factory=list)
    moods: List[str] = Field(default_factory=list)
    keywords: List[Keyword] = Field(default_factory=list)
    person_names: List[str] = Field(default_factory=list)
    person_jobs: List[PersonJob] = Field(default_factory=list)
    country: str = ""
    min_year: int = Field(default=0)
    max_year: int = Field(default=0)


class FeedQueryFilterOntology(BaseModel):
    """사용자 질의에서 추출한 피드 온톨로지 필터."""

    model_config = ConfigDict(use_enum_values=True)

    categories: List[FeedCategory] = Field(default_factory=list)
    emotions: List[EmotionTag] = Field(default_factory=list)
    keywords: List[Keyword] = Field(default_factory=list)
    sentiment: Sentiment = Sentiment.NEUTRAL
    contains_spoiler: bool = False
    related_movie_title: str = ""


class QueryOntologyAnalysis(BaseModel):
    """사용자 자연어 질의 → 영화/피드 온톨로지 필터 분석 결과."""

    model_config = ConfigDict(use_enum_values=True)

    intent_scope: Literal["movie", "feed", "both", "none"]
    movie: MovieQueryFilterOntology
    feed: FeedQueryFilterOntology
    direct_reply_hint: str = ""


# ---------------------------------------------------------------------------
# Chat Reply (generate_reply structured output)
# ---------------------------------------------------------------------------


class ReplyRefMovie(BaseModel):
    """답변 metadata 에 포함되는 영화 참조."""

    type: Literal["movie"] = "movie"
    id: str


class ReplyRefFeed(BaseModel):
    """답변 metadata 에 포함되는 피드 참조."""

    type: Literal["feed"] = "feed"
    id: str


class ReplyMetadataMovie(BaseModel):
    movie: List[ReplyRefMovie] = Field(default_factory=list)


class ReplyMetadataFeed(BaseModel):
    feed: List[ReplyRefFeed] = Field(default_factory=list)


class ReplyMetadataBoth(BaseModel):
    movie: List[ReplyRefMovie] = Field(default_factory=list)
    feed: List[ReplyRefFeed] = Field(default_factory=list)


class ReplyMetadataEmpty(BaseModel):
    """intent_scope=none 일 때 빈 metadata 객체."""


class ChatReplyMovie(BaseModel):
    """영화 추천 답변 structured output."""

    reply: str
    metadata: ReplyMetadataMovie


class ChatReplyFeed(BaseModel):
    """피드 추천 답변 structured output."""

    reply: str
    metadata: ReplyMetadataFeed


class ChatReplyBoth(BaseModel):
    """영화·피드 동시 추천 답변 structured output."""

    reply: str
    metadata: ReplyMetadataBoth


class ChatReplyNone(BaseModel):
    """일반 대화 답변 structured output."""

    reply: str
    metadata: ReplyMetadataEmpty


# ---------------------------------------------------------------------------
# LLM strict JSON Schema (from Pydantic models)
# ---------------------------------------------------------------------------

_LLM_SCHEMA_EXCLUDE: Final[frozenset[str]] = frozenset({"created_at"})


def _inline_schema_refs(schema: dict[str, Any]) -> dict[str, Any]:
    """``$defs`` 참조를 인라인해 단일 스키마 트리로 만든다."""
    defs = schema.get("$defs", {})
    node = deepcopy(schema)

    def resolve(current: dict[str, Any]) -> dict[str, Any]:
        if "$ref" in current:
            ref = current["$ref"]
            if not ref.startswith("#/$defs/"):
                return current
            name = ref.rsplit("/", 1)[-1]
            merged = deepcopy(defs[name])
            for key, value in current.items():
                if key != "$ref":
                    merged[key] = value
            return resolve(merged)

        current.pop("$defs", None)
        current.pop("title", None)

        if "properties" in current:
            current["properties"] = {
                key: resolve(value)
                for key, value in current["properties"].items()
            }
        if "items" in current:
            current["items"] = resolve(current["items"])
        if "anyOf" in current:
            current["anyOf"] = [resolve(item) for item in current["anyOf"]]

        return current

    return resolve(node)


def _normalize_nullable(node: dict[str, Any]) -> dict[str, Any]:
    """OpenAI strict 호환을 위해 ``anyOf[string,null]`` 를 단일 type 배열로 정규화."""
    any_of = node.get("anyOf")
    if not isinstance(any_of, list):
        return node

    types: list[str] = []
    for item in any_of:
        item_type = item.get("type")
        if isinstance(item_type, str):
            types.append(item_type)

    if types == ["string", "null"]:
        normalized = {key: value for key, value in node.items() if key != "anyOf"}
        normalized["type"] = ["string", "null"]
        return normalized

    return node


def _make_strict_schema(node: dict[str, Any]) -> dict[str, Any]:
    """strict json_schema 용: 모든 object 에 required·additionalProperties 를 강제."""
    current = deepcopy(node)
    current = _normalize_nullable(current)
    current.pop("default", None)

    if current.get("type") == "object" and "properties" in current:
        properties = current["properties"]
        current["properties"] = {
            key: _make_strict_schema(value) for key, value in properties.items()
        }
        current["required"] = list(current["properties"].keys())
        current["additionalProperties"] = False
        return current

    if current.get("type") == "array" and "items" in current:
        current["items"] = _make_strict_schema(current["items"])
        return current

    if "anyOf" in current:
        current["anyOf"] = [_make_strict_schema(item) for item in current["anyOf"]]
        return current

    if "const" in current and "enum" not in current:
        current["enum"] = [current.pop("const")]

    return current


def build_strict_object_schema(
    model: type[BaseModel],
    *,
    exclude: frozenset[str] = _LLM_SCHEMA_EXCLUDE,
) -> dict[str, Any]:
    """Pydantic 모델 → strict object JSON Schema (wrapper 없음)."""
    raw = model.model_json_schema()
    inlined = _inline_schema_refs(raw)
    properties = inlined.get("properties", {})
    for field in exclude:
        properties.pop(field, None)
    inlined["properties"] = properties
    if "required" in inlined:
        inlined["required"] = [
            key for key in inlined["required"] if key not in exclude
        ]
    return _make_strict_schema(inlined)


def build_llm_json_schema(
    model: type[BaseModel],
    *,
    name: str,
    exclude: frozenset[str] = _LLM_SCHEMA_EXCLUDE,
) -> dict[str, Any]:
    """Pydantic 모델 → OpenAI/vLLM ``json_schema`` response_format wrapper."""
    return {
        "name": name,
        "strict": True,
        "schema": build_strict_object_schema(model, exclude=exclude),
    }


KEYWORD_ITEM_SCHEMA: dict[str, Any] = build_strict_object_schema(Keyword)


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
    "GENRE_VALUES",
    "Keyword",
    "KeywordKind",
    "KEYWORD_ITEM_SCHEMA",
    "KEYWORD_KIND_VALUES",
    "EmotionScore",
    "OntologyResult",
    "MoviePlotOntology",
    "FeedOntology",
    "CommentOntology",
    "PersonJob",
    "PERSON_JOB_VALUES",
    "MovieQueryFilterOntology",
    "FeedQueryFilterOntology",
    "QueryOntologyAnalysis",
    "ReplyRefMovie",
    "ReplyRefFeed",
    "ReplyMetadataMovie",
    "ReplyMetadataFeed",
    "ReplyMetadataBoth",
    "ReplyMetadataEmpty",
    "ChatReplyMovie",
    "ChatReplyFeed",
    "ChatReplyBoth",
    "ChatReplyNone",
    "build_llm_json_schema",
    "build_strict_object_schema",
    "enum_values",
    "keyword_search_terms",
]
