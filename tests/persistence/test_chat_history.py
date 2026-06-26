"""chat_history reply_metadata 정제 테스트."""

from __future__ import annotations

from src.persistence.chat_history import _sanitize_reply_metadata

_VALID_MOVIE_ID = "550e8400-e29b-41d4-a716-446655440000"
_OTHER_MOVIE_ID = "6ba7b810-9dad-11d1-80b4-00c04fd430c8"


def test_sanitize_reply_metadata_filters_non_uuid_movie_ids() -> None:
    metadata = {
        "movie": [
            {"type": "movie", "id": _VALID_MOVIE_ID},
            {"type": "movie", "id": "m1"},
            {"type": "movie", "id": "not-a-uuid"},
        ],
        "feed": [{"type": "feed", "id": "1"}],
    }

    sanitized = _sanitize_reply_metadata(metadata)

    assert sanitized == {
        "movie": [{"type": "movie", "id": _VALID_MOVIE_ID}],
        "feed": [{"type": "feed", "id": "1"}],
    }


def test_sanitize_reply_metadata_drops_empty_movie_list() -> None:
    metadata = {
        "movie": [{"type": "movie", "id": "m1"}],
        "feed": [{"type": "feed", "id": "1"}],
    }

    sanitized = _sanitize_reply_metadata(metadata)

    assert sanitized == {"feed": [{"type": "feed", "id": "1"}]}


def test_sanitize_reply_metadata_returns_none_for_empty_metadata() -> None:
    assert _sanitize_reply_metadata(None) is None
    assert _sanitize_reply_metadata({}) is None
    assert _sanitize_reply_metadata({"movie": [{"type": "movie", "id": "m1"}]}) is None


def test_sanitize_reply_metadata_keeps_multiple_valid_uuid_movies() -> None:
    metadata = {
        "movie": [
            {"type": "movie", "id": _VALID_MOVIE_ID},
            {"type": "movie", "id": _OTHER_MOVIE_ID},
        ]
    }

    sanitized = _sanitize_reply_metadata(metadata)

    assert sanitized == metadata
