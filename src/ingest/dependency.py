"""Outbox row 간 선행 의존성 매핑.

SRP: aggregate_type + payload → 필요한 선행 작업(Dependency) 목록만 해석한다.
     DB 조회·상태 전이 로직은 Worker 가 담당한다.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence


@dataclass(frozen=True, slots=True)
class Dependency:
    """선행 완료되어야 하는 outbox row 를 식별하는 값 객체."""

    dep_type: str
    dep_id: str


class DependencyResolver:
    """aggregate_type + payload 에서 선행 의존성을 해석한다.

    규칙
    ----
    - comment            → feed(feed_id), [comment(parent_comment_id)]
    - comment_modify/delete/like → comment(comment_id)
    - feed_modify/delete/like   → feed(feed_id)
    - movie_judge        → movie(movie_id)
    - movie / feed / person_judge → 선행 없음
    """

    def resolve(
        self, aggregate_type: str, payload: Mapping[str, Any]
    ) -> Sequence[Dependency]:
        resolver = _RESOLVERS.get(aggregate_type)
        if resolver is None:
            return ()
        return resolver(payload)


def _resolve_comment(payload: Mapping[str, Any]) -> Sequence[Dependency]:
    deps: list[Dependency] = [Dependency("feed", payload["feed_id"])]
    parent = payload.get("parent_comment_id")
    if parent:
        deps.append(Dependency("comment", parent))
    return deps


def _resolve_comment_action(payload: Mapping[str, Any]) -> Sequence[Dependency]:
    return (Dependency("comment", payload["comment_id"]),)


def _resolve_feed_action(payload: Mapping[str, Any]) -> Sequence[Dependency]:
    return (Dependency("feed", payload["feed_id"]),)


def _resolve_movie_judge(payload: Mapping[str, Any]) -> Sequence[Dependency]:
    return (Dependency("movie", payload["movie_id"]),)


_RESOLVERS: dict[str, Any] = {
    "comment": _resolve_comment,
    "comment_modify": _resolve_comment_action,
    "comment_delete": _resolve_comment_action,
    "comment_like": _resolve_comment_action,
    "feed_modify": _resolve_feed_action,
    "feed_delete": _resolve_feed_action,
    "feed_like": _resolve_feed_action,
    "movie_judge": _resolve_movie_judge,
}


__all__ = ["Dependency", "DependencyResolver"]
