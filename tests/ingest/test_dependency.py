"""DependencyResolver 매핑 테스트."""

from __future__ import annotations

from src.ingest.dependency import Dependency, DependencyResolver


def _resolver() -> DependencyResolver:
    return DependencyResolver()


def test_movie_has_no_deps() -> None:
    deps = _resolver().resolve("movie", {"movie_id": "m-1", "title": "t"})
    assert deps == ()


def test_feed_has_no_deps() -> None:
    deps = _resolver().resolve("feed", {"feed_id": "f-1", "user_id": "u-1", "content": "x"})
    assert deps == ()


def test_comment_depends_on_feed() -> None:
    deps = _resolver().resolve("comment", {"comment_id": "c-1", "feed_id": "f-1", "user_id": "u-1", "content": "hi"})
    assert Dependency("feed", "f-1") in deps


def test_comment_depends_on_parent_comment() -> None:
    deps = _resolver().resolve(
        "comment",
        {"comment_id": "c-2", "feed_id": "f-1", "user_id": "u-1",
         "parent_comment_id": "c-1", "content": "reply"},
    )
    assert Dependency("feed", "f-1") in deps
    assert Dependency("comment", "c-1") in deps
    assert len(deps) == 2


def test_comment_no_parent_comment_dep() -> None:
    deps = _resolver().resolve(
        "comment",
        {"comment_id": "c-1", "feed_id": "f-1", "user_id": "u-1", "content": "hi"},
    )
    assert len(deps) == 1
    assert deps[0].dep_type == "feed"


def test_comment_modify_depends_on_comment() -> None:
    deps = _resolver().resolve("comment_modify", {"comment_id": "c-1", "feed_id": "f-1", "user_id": "u-1", "content": "edited"})
    assert deps == (Dependency("comment", "c-1"),)


def test_comment_delete_depends_on_comment() -> None:
    deps = _resolver().resolve("comment_delete", {"comment_id": "c-1", "user_id": "u-1"})
    assert deps == (Dependency("comment", "c-1"),)


def test_comment_like_depends_on_comment() -> None:
    deps = _resolver().resolve("comment_like", {"comment_id": "c-1", "user_id": "u-1"})
    assert deps == (Dependency("comment", "c-1"),)


def test_feed_modify_depends_on_feed() -> None:
    deps = _resolver().resolve("feed_modify", {"feed_id": "f-1", "user_id": "u-1", "content": "edited"})
    assert deps == (Dependency("feed", "f-1"),)


def test_feed_delete_depends_on_feed() -> None:
    deps = _resolver().resolve("feed_delete", {"feed_id": "f-1", "user_id": "u-1"})
    assert deps == (Dependency("feed", "f-1"),)


def test_feed_like_depends_on_feed() -> None:
    deps = _resolver().resolve("feed_like", {"feed_id": "f-1", "user_id": "u-1"})
    assert deps == (Dependency("feed", "f-1"),)


def test_movie_judge_depends_on_movie() -> None:
    deps = _resolver().resolve("movie_judge", {"movie_id": "m-1", "user_id": "u-1"})
    assert deps == (Dependency("movie", "m-1"),)


def test_person_judge_has_no_deps() -> None:
    deps = _resolver().resolve("person_judge", {"person_id": "p-1", "user_id": "u-1"})
    assert deps == ()


def test_unknown_aggregate_type_has_no_deps() -> None:
    deps = _resolver().resolve("unknown_type", {"foo": "bar"})
    assert deps == ()
