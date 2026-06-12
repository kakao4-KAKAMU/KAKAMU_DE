from __future__ import annotations
from typing import Any, Final
from textwrap import dedent
from .pipeline import OntologyPromptSpec
from src.ontology.schema import SCHEMA_VERSION_VALUES

ONTOLOGY_MOVIE_CACHE_SALT: Final[str] = "ontology:movie_plot:v1.5"

_MOVIE_PLOT_SCHEMA_BASE: Final[dict[str, Any]] = {
    "name": "movie_knowledge_ontology",
    "strict": True,
    "schema": {
        "type": "object",
        "properties": {
            "schema_version": {"type": "string", "enum": SCHEMA_VERSION_VALUES},
            "source_id": {"type": "string"},
            "language": {"type": "string"},
            "summary": {"type": "string"},
            "themes": {"type": "array", "items": {"type": "string"}},
            "moods": {"type": "array", "items": {"type": "string"}},
            "keywords": {
                "type": "array",
                "items": {"type": "object"},
            },
            "toxicity_score": {"type": "number"},
        },
        "required": [
            "schema_version",
            "source_id",
            "language",
            "summary",
            "themes",
            "moods",
            "keywords",
            "toxicity_score",
        ],
        "additionalProperties": False,
    },
}


_MOVIE_PLOT_GUIDE: Final[str] = dedent(
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

    [Movie Plot]
    - summary: 줄거리 인과(원인→사건→결말). 결말 스포일러는 추상화.
    - themes/moods: 폐쇄형 vocabulary 에서만 선택. 근거 없으면 [].
    - keywords: 영화 지표(era/environment/key_object/source_form/culture_code/entity/other).
      themes/moods 와 중복 금지. 5~15개 권장.
    - 관객 리뷰는 themes/moods/keywords 보강에만 사용. 리뷰 의견을 사실로 혼동 금지.
    - toxicity_score: 욕설/공격성/혐오 수위(0.0~1.0).
    """
).strip()

_SPEC = OntologyPromptSpec(
    name="movie_plot",
    base_schema=_MOVIE_PLOT_SCHEMA_BASE,
    guide=_MOVIE_PLOT_GUIDE,
    cache_salt=ONTOLOGY_MOVIE_CACHE_SALT,
    include_vocab_guide=True,
)


def get_movie_plot_schema_json() -> dict[str, Any]:
    return _SPEC.schema_json()


def _format_reviews(reviews: list[str] | None) -> str:
    if not reviews:
        return ""
    blocks = []
    for idx, review in enumerate(reviews, start=1):
        text = review.strip()
        if text:
            blocks.append(f"[리뷰 {idx}]\n{text}")
    return "\n\n".join(blocks)


def build_movie_plot_messages(
    *,
    movie_id: str,
    title: str,
    producing_year: int | None,
    country: str | None,
    genres: list[str] | None,
    plot: str,
    persons: list[dict[str, str]] | None = None,
    reviews: list[str] | None = None,
):
    """영화 줄거리 → MoviePlotOntology 매핑용 messages + response_format 생성."""
    review_block = _format_reviews(reviews)
    review_section = (
        dedent(
            f"""
            [관객 리뷰 샘플]
            \"\"\"
            {review_block}
            \"\"\"
            """
        ).strip()
        if review_block
        else ""
    )

    user_payload = dedent(
        f"""
        [영화 메타]
        - movie_id      : {movie_id}
        - title         : {title}
        - producing_year: {producing_year if producing_year is not None else "unknown"}
        - country       : {country or "unknown"}
        - genres        : {", ".join(genres) if genres else "unknown"}

        [원문 줄거리]
        \"\"\"
        {plot.strip()}
        \"\"\"
        {review_section}
        """
    ).strip()

    return _SPEC.build_payload(user_payload=user_payload)


__all__ = [
    "ONTOLOGY_MOVIE_CACHE_SALT",
    "build_movie_plot_messages",
    "get_movie_plot_schema_json",
]
