from __future__ import annotations
from typing import Any, Final
from textwrap import dedent
from .pipeline import OntologyPromptSpec

ONTOLOGY_MOVIE_CACHE_SALT: Final[str] = "ontology:movie_plot:v1.4"

_MOVIE_PLOT_SCHEMA_BASE: Final[dict[str, Any]] = {
    "name": "movie_knowledge_ontology",
    "strict": True,
    "schema": {
        "type": "object",
        "properties": {
            "schema_version": {"type": "string", "enum": ["1.0"]},
            "source_id": {"type": "string"},
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
    [Movie Plot 전용 가이드]
    - summary 는 줄거리의 인과(원인→사건→결말) 가 드러나도록 작성한다.
    - 단, 영화의 결말 spoiler 라 판단되는 경우 결말 표현은 추상화한다.
    - themes 는 폐쇄형 vocabulary (snake_case) 에서만 선택한다.
    - moods 는 폐쇄형 vocabulary (snake_case) 에서만 선택한다.
      (예: time_loop, anti_hero, found_family, redemption_arc)
    - keywords 는 검색 anchor 가 되는 구체 표현만 담는다.
      장르/테마/무드는 themes/moods 로만 추출하고 keywords 에 중복 금지.
    - keywords.kind 분포 가이드(허용 kind: entity/object/concept/location/other):
        entity(인물/단체)/object 합쳐 40~50%, 나머지는 concept/location/other.
        이외 다른 kind 는 사용할 수 없다.
    - 입력 메타의 제작진(persons: 감독/배우 등)은 사실로 간주한다.
    - 관객 리뷰(reviews)가 제공되면 themes/moods/keywords 추출에 반영하되,
      리뷰 의견을 줄거리 사실로 혼동하지 않는다.
    - toxicity_score 는 욕설/공격성/혐오표현 수위(0.1~1.0).
    """
).strip()

_SPEC = OntologyPromptSpec(
    name="movie_plot",
    base_schema=_MOVIE_PLOT_SCHEMA_BASE,
    guide=_MOVIE_PLOT_GUIDE,
    cache_salt=ONTOLOGY_MOVIE_CACHE_SALT,
)


def get_movie_plot_schema_json() -> dict[str, Any]:
    return _SPEC.schema_json()


def _format_persons(persons: list[dict[str, str]] | None) -> str:
    if not persons:
        return "없음"
    lines = [f"  - {p['name']} ({p['job']}, id={p['person_id']})" for p in persons]
    return "\n".join(lines)


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
    """영화 줄거리 → MoviePlotOntology 매핑용 messages + response_format 생성.

    Args:
        movie_id: 영화 고유 ID. 결과 JSON 의 source_id 로 들어간다.
        title: 영화 제목.
        producing_year: 제작연도(없으면 None).
        country: 제작국가(없으면 None).
        genres: TMDB/KMDB 의 장르명 리스트.
        plot: 정제 대상이 되는 짧은 줄거리 원문.
        persons: 감독/배우 등 제작진 메타 (person_id, name, job).
        reviews: 관객 리뷰 샘플. themes/moods 추출 보강용.

    Returns:
        OpenAI/vLLM Chat Completions 호환 messages 리스트.
    """
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

    return _SPEC.build_payload(user_payload=user_payload, frequency_penalty=0.5)


__all__ = [
    "ONTOLOGY_MOVIE_CACHE_SALT",
    "build_movie_plot_messages",
    "get_movie_plot_schema_json",
]
