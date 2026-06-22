"""LLM 기반 사용자 질의 → 영화/피드 온톨로지 필터 분석.

SOLID
-----
- SRP : 질의 분석·정규화만 담당. 검색/응답 생성은 외부 노드에서.
- DIP : ``JSONChatLLM`` Protocol 과 ``IntentResolver``(폴백) 에만 의존.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Literal, Protocol

from src.ontology.prompts.query_analysis import build_query_analysis_messages
from src.recommend.intent_resolver import IntentResolver

logger = logging.getLogger(__name__)

IntentScope = Literal["movie", "feed", "both", "none"]


class JSONChatLLM(Protocol):
    def chat_json(
        self,
        messages: list[dict[str, str]],
        *,
        user_id: str | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
        response_format: dict[str, Any] | None = None,
        cache_salt: str | None = None,
        guided_json_schema: dict[str, Any] | None = None,
    ) -> dict[str, Any]: ...


@dataclass(frozen=True)
class MovieQueryFilters:
    genres: list[str] = field(default_factory=list)
    themes: list[str] = field(default_factory=list)
    moods: list[str] = field(default_factory=list)
    keywords: list[str] = field(default_factory=list)
    person_names: list[str] = field(default_factory=list)
    person_jobs: list[str] = field(default_factory=list)
    country: str = ""
    min_year: int = 0
    max_year: int = 0


@dataclass(frozen=True)
class FeedQueryFilters:
    categories: list[str] = field(default_factory=list)
    emotions: list[str] = field(default_factory=list)
    keywords: list[str] = field(default_factory=list)
    sentiment: str = "neutral"
    contains_spoiler: bool = False
    related_movie_title: str = ""


@dataclass(frozen=True)
class QueryAnalysis:
    intent_scope: IntentScope
    movie: MovieQueryFilters
    feed: FeedQueryFilters
    direct_reply_hint: str = ""


def _keyword_terms(items: list[dict[str, Any]] | None) -> list[str]:
    terms: list[str] = []
    for item in items or []:
        normalized = str(item.get("normalized") or "").strip()
        term = str(item.get("term") or "").strip()
        token = normalized or term
        if token:
            terms.append(token)
    return terms


def _parse_movie_filters(raw: dict[str, Any] | None) -> MovieQueryFilters:
    data = raw or {}
    kw_terms = _keyword_terms(data.get("keywords"))
    genres = [str(g).strip() for g in data.get("genres") or [] if str(g).strip()]
    return MovieQueryFilters(
        genres=genres,
        themes=[str(t).strip() for t in data.get("themes") or [] if str(t).strip()],
        moods=[str(m).strip() for m in data.get("moods") or [] if str(m).strip()],
        keywords=list(dict.fromkeys(kw_terms + genres)),
        person_names=[
            str(n).strip() for n in data.get("person_names") or [] if str(n).strip()
        ],
        person_jobs=[
            str(j).strip() for j in data.get("person_jobs") or [] if str(j).strip()
        ],
        country=str(data.get("country") or "").strip(),
        min_year=int(data.get("min_year") or 0),
        max_year=int(data.get("max_year") or 0),
    )


def _parse_feed_filters(raw: dict[str, Any] | None) -> FeedQueryFilters:
    data = raw or {}
    kw_terms = _keyword_terms(data.get("keywords"))
    categories = [str(c).strip() for c in data.get("categories") or [] if str(c).strip()]
    emotions = [str(e).strip() for e in data.get("emotions") or [] if str(e).strip()]
    return FeedQueryFilters(
        categories=categories,
        emotions=emotions,
        keywords=list(dict.fromkeys(kw_terms + categories + emotions)),
        sentiment=str(data.get("sentiment") or "neutral").strip() or "neutral",
        contains_spoiler=bool(data.get("contains_spoiler")),
        related_movie_title=str(data.get("related_movie_title") or "").strip(),
    )


def _parse_analysis(raw: dict[str, Any]) -> QueryAnalysis:
    scope = str(raw.get("intent_scope") or "none").strip().lower()
    if scope not in ("movie", "feed", "both", "none"):
        scope = "none"
    return QueryAnalysis(
        intent_scope=scope,  # type: ignore[arg-type]
        movie=_parse_movie_filters(raw.get("movie")),
        feed=_parse_feed_filters(raw.get("feed")),
        direct_reply_hint=str(raw.get("direct_reply_hint") or "").strip(),
    )


def _fallback_from_resolver(intent_resolver: IntentResolver, query: str) -> QueryAnalysis:
    """LLM 실패 시 룰 기반 intent_resolver 로 movie 스코프 폴백."""
    resolved = intent_resolver.resolve(query)
    movie = MovieQueryFilters(
        genres=[],
        themes=list(resolved.themes),
        moods=list(resolved.moods),
        keywords=list(resolved.keywords),
    )
    return QueryAnalysis(intent_scope="movie", movie=movie, feed=FeedQueryFilters())


class LLMQueryAnalyzer:
    """json_schema 강제 LLM 으로 질의를 온톨로지 필터로 분석한다."""

    def __init__(
        self,
        llm: JSONChatLLM,
        *,
        intent_resolver: IntentResolver | None = None,
        max_tokens: int = 512,
        temperature: float = 0.0,
    ) -> None:
        self._llm = llm
        self._intent_resolver = intent_resolver
        self._max_tokens = max_tokens
        self._temperature = temperature

    def analyze(self, query: str, *, user_id: str | None = None) -> QueryAnalysis:
        text = (query or "").strip()
        if not text:
            return QueryAnalysis(
                intent_scope="none",
                movie=MovieQueryFilters(),
                feed=FeedQueryFilters(),
            )
        payload = build_query_analysis_messages(user_query=text)
        try:
            raw = self._llm.chat_json(
                payload["messages"],
                response_format=payload.get("response_format"),
                cache_salt=payload.get("cache_salt"),
                user_id=user_id,
                max_tokens=self._max_tokens,
                temperature=self._temperature,
            )
            return _parse_analysis(raw)
        except Exception:
            logger.exception("LLM query analysis failed; using fallback.")
            if self._intent_resolver is not None:
                return _fallback_from_resolver(self._intent_resolver, text)
            return QueryAnalysis(
                intent_scope="movie",
                movie=MovieQueryFilters(),
                feed=FeedQueryFilters(),
            )


__all__ = [
    "FeedQueryFilters",
    "IntentScope",
    "LLMQueryAnalyzer",
    "MovieQueryFilters",
    "QueryAnalysis",
]
