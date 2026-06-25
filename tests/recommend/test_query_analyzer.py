"""query_analyzer 파서 단위 테스트."""

from __future__ import annotations

from src.ontology.schema import Keyword, keyword_search_terms
from src.recommend.query_analyzer import (
    MovieQueryFilters,
    _parse_analysis,
    _parse_movie_filters,
)


def test_parse_movie_filters_builds_keyword_models() -> None:
    filters = _parse_movie_filters(
        {
            "genres": ["드라마"],
            "themes": ["growth"],
            "moods": ["calm"],
            "keywords": [
                {"term": "성장", "normalized": "growth", "weight": 1.0, "kind": "other"}
            ],
            "person_names": ["봉준호"],
            "person_jobs": ["director"],
            "country": "KR",
            "min_year": 2010,
            "max_year": 2024,
        }
    )
    assert isinstance(filters.keywords[0], Keyword)
    assert filters.keywords[0].normalized == "growth"
    assert filters.country == "kr"
    assert keyword_search_terms(filters.keywords) == ["growth"]


def test_parse_analysis_invalid_scope_falls_back_to_none() -> None:
    analysis = _parse_analysis(
        {
            "intent_scope": "unknown",
            "movie": {},
            "feed": {},
            "direct_reply_hint": "",
        }
    )
    assert analysis.intent_scope == "none"
    assert analysis.movie == MovieQueryFilters()


def test_keyword_search_terms_deduplicates_mixed_inputs() -> None:
    terms = keyword_search_terms(
        [
            Keyword(term="성장", normalized="growth"),
            {"term": "성장", "normalized": "growth"},
            "growth",
            "family",
        ]
    )
    assert terms == ["growth", "family"]
