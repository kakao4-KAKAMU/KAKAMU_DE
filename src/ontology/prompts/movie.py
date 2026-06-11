from __future__ import annotations
from typing import Any, Final
from textwrap import dedent
from .pipeline import OntologyPromptSpec

ONTOLOGY_MOVIE_CACHE_SALT: Final[str] = "ontology:movie_plot:v1"

_MOVIE_PLOT_SCHEMA_BASE: Final[dict[str, Any]] = {
    "name": "movie_knowledge_ontology",
    "strict": True,
    "schema": {
        "type": "object",
        "properties": {
            "schema_version": {"type": "string", "enum": ["1.0"]},
            "source_id": {"type": "string"},
            "language": {"type": "string"},
            "summary": {"type": "string"},
            "genres": {"type": "array", "items": {"type": "string"}},
            "themes": {"type": "array", "items": {"type": "string"}},
            "moods": {"type": "array", "items": {"type": "string"}},
            "tropes": {"type": "array", "items": {"type": "string"}},
            "keywords": {
                "type": "array",
                "items": {"type": "object"},
            },
            "characters": {"type": "array", "items": {"type": "string"}},
            "locations": {"type": "array", "items": {"type": "string"}},
            "target_audience": {"type": "array", "items": {"type": "string"}},
            "toxicity_score": {"type": "number"},
        },
        "required": [
            "schema_version",
            "source_id",
            "language",
            "summary",
            "genres",
            "themes",
            "moods",
            "tropes",
            "keywords",
            "characters",
            "locations",
            "target_audience",
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
    - genres 는 메타 장르와 줄거리 근거를 종합해 폐쇄형 vocabulary 에서만 선택한다.
    - themes 는 폐쇄형 vocabulary (snake_case) 에서만 선택한다.
    - moods 는 폐쇄형 vocabulary (snake_case) 에서만 선택한다.
    - tropes 는 영화/장르 클리셰의 식별자. snake_case 로 통일.
      (예: time_loop, anti_hero, found_family, redemption_arc)
    - keywords.kind 분포 가이드:
        theme/mood/genre 합쳐 30~40%,
        entity(인물/단체)/location/object 합쳐 40~50%,
        나머지는 concept/other
        이외 다른 kind는 사용할 수 없다.
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


def build_movie_plot_messages(
    *,
    movie_id: str,
    title: str,
    producing_year: int | None,
    country: str | None,
    genres: list[str] | None,
    plot: str,
) -> dict[str, Any]:
    """영화 줄거리 → MoviePlotOntology 매핑용 messages + response_format 생성.

    Args:
        movie_id: 영화 고유 ID. 결과 JSON 의 source_id 로 들어간다.
        title: 영화 제목.
        producing_year: 제작연도(없으면 None).
        country: 제작국가(없으면 None).
        genres: TMDB/KMDB 의 장르명 리스트.
        plot: 정제 대상이 되는 짧은 줄거리 원문.

    Returns:
        OpenAI/vLLM Chat Completions 호환 messages 리스트.
    """

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
        """
    ).strip()

    return _SPEC.build_payload(user_payload=user_payload)


__all__ = [
    "ONTOLOGY_MOVIE_CACHE_SALT",
    "build_movie_plot_messages",
    "get_movie_plot_schema_json",
]
