"""ontology prompt JSON schema vocabulary injection tests."""

from __future__ import annotations

from src.ontology.prompts.base import ONTOLOGY_SYSTEM_PROMPT
from src.ontology.prompts.comment import (
    build_comment_messages,
    get_comment_schema_json,
)
from src.ontology.prompts.feed import build_feed_messages, get_feed_schema_json
from src.ontology.prompts.movie import build_movie_plot_messages, get_movie_plot_schema_json
from src.ontology.prompts.schema_vocab import (
    apply_vocab_enums,
    build_vocab_guide_lines,
    vocab_fingerprint,
    vocab_genres,
    vocab_moods,
    vocab_themes,
)


def _enum_items(schema: dict, field: str) -> list[str]:
    return schema["schema"]["properties"][field]["items"]["enum"]


def _assert_standard_payload_layout(payload: dict, *, cache_prefix: str) -> None:
    messages = payload["messages"]
    assert len(messages) == 4
    assert messages[0] == {"role": "system", "content": ONTOLOGY_SYSTEM_PROMPT}
    assert messages[1] == {"role": "system", "content": build_vocab_guide_lines()}
    assert messages[2]["role"] == "system"
    assert messages[3]["role"] == "user"
    assert payload["response_format"]["type"] == "json_schema"
    assert "json_schema" in payload["response_format"]
    assert payload["cache_salt"].startswith(cache_prefix)


def test_vocab_loaders_non_empty() -> None:
    assert len(vocab_genres()) >= 60
    assert len(vocab_themes()) >= 30
    assert len(vocab_moods()) >= 8
    assert len(vocab_fingerprint()) == 12


def test_movie_schema_injects_vocab_enums() -> None:
    schema = get_movie_plot_schema_json()
    genres = _enum_items(schema, "genres")
    themes = _enum_items(schema, "themes")
    moods = _enum_items(schema, "moods")

    assert "드라마" in genres
    assert "identity" in themes
    assert "melancholic" in moods

    keyword_kind = schema["schema"]["properties"]["keywords"]["items"]["properties"]["kind"]
    assert "genre" in keyword_kind["enum"]


def test_feed_and_comment_schema_inject_vocab_enums() -> None:
    for getter in (get_feed_schema_json, get_comment_schema_json):
        schema = getter()
        assert "액션" in _enum_items(schema, "genres")
        assert "loss" in _enum_items(schema, "themes")
        assert "warm" in _enum_items(schema, "moods")


def test_apply_vocab_enums_defaults_inject_standard_fields() -> None:
    base = {
        "name": "test",
        "schema": {
            "type": "object",
            "properties": {
                "genres": {"type": "array", "items": {"type": "string"}},
                "themes": {"type": "array", "items": {"type": "string"}},
                "moods": {"type": "array", "items": {"type": "string"}},
            },
        },
    }
    result = apply_vocab_enums(base)
    for field in ("genres", "themes", "moods"):
        assert "enum" in result["schema"]["properties"][field]["items"]


def test_apply_vocab_enums_is_immutable_template() -> None:
    base = {
        "name": "test",
        "schema": {
            "type": "object",
            "properties": {
                "themes": {"type": "array", "items": {"type": "string"}},
            },
        },
    }
    first = apply_vocab_enums(base, theme_fields=("themes",))
    second = apply_vocab_enums(base, theme_fields=("themes",))
    assert first is not second
    assert base["schema"]["properties"]["themes"]["items"]["type"] == "string"
    assert "enum" in first["schema"]["properties"]["themes"]["items"]


def test_build_movie_plot_messages_uses_vocab_cache_salt() -> None:
    payload = build_movie_plot_messages(
        movie_id="m1",
        title="테스트",
        producing_year=2020,
        country="KR",
        genres=["드라마"],
        plot="테스트 줄거리",
    )
    _assert_standard_payload_layout(
        payload, cache_prefix="ontology:movie_plot:v1:vocab:"
    )
    schema = payload["response_format"]["json_schema"]
    assert "드라마" in _enum_items(schema, "genres")


def test_feed_and_comment_payload_use_standard_layout() -> None:
    feed = build_feed_messages(
        feed_id="f1",
        user_id="u1",
        related_movie_id=None,
        known_movie_ids=None,
        content="좋은 영화였어요",
    )
    _assert_standard_payload_layout(feed, cache_prefix="ontology:feed:v1:vocab:")

    comment = build_comment_messages(
        comment_id="c1",
        feed_id="f1",
        user_id="u1",
        mentioned_user_ids=None,
        parent_feed_summary=None,
        content="동의합니다",
    )
    _assert_standard_payload_layout(comment, cache_prefix="ontology:comment:v1:vocab:")
