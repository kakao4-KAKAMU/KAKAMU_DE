"""Neo4j 에 적재된 온톨로지 요약 조회.

댓글 ingest 시 feed_id / parent_comment_id 로 부모 맥락을 불러온다.
"""

from __future__ import annotations

from typing import Optional, Protocol

from src.graph.client import Neo4jClient
from src.graph.cypher_statements import (
    GET_COMMENT_SUMMARY,
    GET_FEED_SUMMARY,
    GET_MOVIE_PLOT_RAW,
)


class CommentContextReader(Protocol):
    """댓글 온톨로지 추출에 필요한 부모 맥락 조회 추상화."""

    def get_feed_summary(self, feed_id: str) -> str | None: ...

    def get_comment_summary(self, comment_id: str) -> str | None: ...


class MoviePlotReader(Protocol):
    """피드 온톨로지 추출에 필요한 관련 영화 줄거리 조회 추상화."""

    def get_plot_raw(self, movie_id: str) -> str | None: ...


class NullCommentContextReader:
    """맥락 조회 없음 (테스트/스텁)."""

    def get_feed_summary(self, feed_id: str) -> str | None:
        return None

    def get_comment_summary(self, comment_id: str) -> str | None:
        return None


class NullMoviePlotReader:
    """영화 줄거리 조회 없음 (테스트/스텁)."""

    def get_plot_raw(self, movie_id: str) -> str | None:
        return None


class Neo4jCommentContextReader:
    """Neo4j Feed/Comment 노드의 summary 를 조회한다."""

    def __init__(self, neo4j: Neo4jClient) -> None:
        self._neo4j = neo4j

    def get_feed_summary(self, feed_id: str) -> str | None:
        return _first_summary(
            self._neo4j.execute_read(GET_FEED_SUMMARY, {"feed_id": feed_id})
        )

    def get_comment_summary(self, comment_id: str) -> str | None:
        return _first_summary(
            self._neo4j.execute_read(
                GET_COMMENT_SUMMARY, {"comment_id": comment_id}
            )
        )


class Neo4jMoviePlotReader:
    """Neo4j Movie 노드의 plot_raw 를 조회한다."""

    def __init__(self, neo4j: Neo4jClient) -> None:
        self._neo4j = neo4j

    def get_plot_raw(self, movie_id: str) -> str | None:
        return _first_plot_raw(
            self._neo4j.execute_read(GET_MOVIE_PLOT_RAW, {"movie_id": movie_id})
        )


def _first_summary(rows: list[dict]) -> str | None:
    if not rows:
        return None
    summary = rows[0].get("summary")
    if summary is None:
        return None
    text = str(summary).strip()
    return text or None


def _first_plot_raw(rows: list[dict]) -> str | None:
    if not rows:
        return None
    plot_raw = rows[0].get("plot_raw")
    if plot_raw is None:
        return None
    text = str(plot_raw).strip()
    return text or None


__all__ = [
    "CommentContextReader",
    "MoviePlotReader",
    "Neo4jCommentContextReader",
    "Neo4jMoviePlotReader",
    "NullCommentContextReader",
    "NullMoviePlotReader",
]
