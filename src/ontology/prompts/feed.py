from __future__ import annotations
from typing import Any, Final
from textwrap import dedent
from .pipeline import OntologyPromptSpec

from src.ontology.schema import FeedOntology, build_llm_json_schema

ONTOLOGY_FEED_CACHE_SALT: Final[str] = "ontology:feed:v4"

_FEED_SCHEMA_BASE: Final[dict[str, Any]] = build_llm_json_schema(
    FeedOntology,
    name="feed_knowledge_ontology",
)

_FEED_GUIDE: Final[str] = dedent(
    """
    [keywords — 영화 지표]
    keywords.kind 는 아래 7종 중 하나만 사용:
    - era          : 시대적 배경 (예: 1980년대, 조선시대)
    - environment  : 환경/공간 (예: 우주, 교도소, 어촌 마을)
    - key_object   : 핵심 소재 (예: 타임머신, 복권, 일기장)
    - source_form  : 원작 형태 (예: 웹툰 원작, 소설 원작, 리메이크)
    - culture_code : 문화 코드 (예: 홍콩 느와르, 한국 군대 문화)
    - entity       : 인물/단체/작품명
    - other        : 위에 해당하지 않는 지표
    - term: 원문 표면형. normalized: 영어 snake_case 표제어(필수).
    - themes/moods 등 전용 필드 값은 keywords 에 중복 금지.

    [keywords — 키워드]
    - keywords: 피드 본문에 포함되어 있는 영화 지표를 의미한다.
    - keywords.normalized 는 snake_case이며 필수값입니다.

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
    genre_fields=(),
    theme_fields=(),
    mood_fields=(),
)


def get_feed_schema_json() -> dict[str, Any]:
    return _SPEC.schema_json()


def build_feed_messages(
    *,
    feed_id: str,
    user_id: str,
    related_movie_id: str | None,
    known_movie_ids: list[str] | None,
    related_movie_plot_raw: str | None = None,
    content: str,
) -> dict[str, Any]:
    """피드 본문 → FeedOntology 매핑용 messages."""

    movie_plot_section = (
        dedent(
            f"""
            [관련 영화 원문 줄거리]
            \"\"\"
            {related_movie_plot_raw.strip()}
            \"\"\"
            """
        ).strip()
        if related_movie_plot_raw
        else ""
    )

    user_payload = dedent(
        f"""
        [피드 메타]
        - feed_id          : {feed_id}
        - user_id          : {user_id}
        - related_movie_id : {related_movie_id or "none"}
        - known_movie_ids  : {", ".join(known_movie_ids) if known_movie_ids else "none"}

        [영화 내용]
        {movie_plot_section or "(none)"}

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
