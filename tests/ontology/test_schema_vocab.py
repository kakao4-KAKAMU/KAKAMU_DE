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
    KEYWORD_KINDS,
    apply_vocab_enums,
    build_vocab_guide_lines,
    vocab_fingerprint,
    vocab_genres,
    vocab_moods,
    vocab_themes,
)
from src.ontology.schema import (
    COMMENT_REACTION_VALUES,
    COMMENT_TARGET_VALUES,
    FEED_CATEGORY_VALUES,
    KEYWORD_KIND_VALUES,
)


def _enum_items(schema: dict, field: str) -> list[str]:
    return schema["schema"]["properties"][field]["items"]["enum"]


def _assert_movie_payload_layout(payload: dict, *, cache_prefix: str) -> None:
    messages = payload["messages"]
    assert len(messages) == 4
    assert messages[0] == {"role": "system", "content": ONTOLOGY_SYSTEM_PROMPT}
    assert messages[1] == {"role": "system", "content": build_vocab_guide_lines()}
    assert messages[2]["role"] == "system"
    assert messages[3]["role"] == "user"
    assert payload["response_format"]["type"] == "json_schema"
    assert "json_schema" in payload["response_format"]
    assert payload["cache_salt"].startswith(cache_prefix)


def _assert_feed_comment_payload_layout(payload: dict, *, cache_prefix: str) -> None:
    messages = payload["messages"]
    assert len(messages) == 3
    assert messages[0] == {"role": "system", "content": ONTOLOGY_SYSTEM_PROMPT}
    assert messages[1]["role"] == "system"
    assert messages[2]["role"] == "user"
    assert payload["response_format"]["type"] == "json_schema"
    assert payload["cache_salt"].startswith(cache_prefix)


def test_vocab_loaders_non_empty() -> None:
    assert len(vocab_genres()) >= 60
    assert len(vocab_themes()) >= 30
    assert len(vocab_moods()) >= 8
    assert len(vocab_fingerprint()) == 12


def test_movie_schema_injects_vocab_enums() -> None:
    schema = get_movie_plot_schema_json()
    themes = _enum_items(schema, "themes")
    moods = _enum_items(schema, "moods")

    assert "identity" in themes
    assert "melancholic" in moods

    keyword_kind = schema["schema"]["properties"]["keywords"]["items"]["properties"]["kind"]
    assert set(keyword_kind["enum"]) == set(KEYWORD_KIND_VALUES)
    assert set(keyword_kind["enum"]) == set(KEYWORD_KINDS)


def test_feed_and_comment_schema_have_no_vocab_fields() -> None:
    for getter in (get_feed_schema_json, get_comment_schema_json):
        schema = getter()
        props = schema["schema"]["properties"]
        assert "genres" not in props
        assert "themes" not in props
        assert "moods" not in props
        keyword_kind = props["keywords"]["items"]["properties"]["kind"]
        assert set(keyword_kind["enum"]) == set(KEYWORD_KIND_VALUES)
    assert set(keyword_kind["enum"]) == set(KEYWORD_KINDS)


def test_feed_schema_has_category_enum() -> None:
    schema = get_feed_schema_json()
    category = schema["schema"]["properties"]["category"]
    assert set(category["enum"]) == set(FEED_CATEGORY_VALUES)


def test_comment_schema_has_target_reaction() -> None:
    schema = get_comment_schema_json()
    props = schema["schema"]["properties"]
    assert set(props["target"]["enum"]) == set(COMMENT_TARGET_VALUES)
    assert set(props["reaction"]["enum"]) == set(COMMENT_REACTION_VALUES)
    assert "intents" not in props


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
    _assert_movie_payload_layout(
        payload, cache_prefix="ontology:movie_plot:v1.5:vocab:"
    )
    schema = payload["response_format"]["json_schema"]
    assert "identity" in _enum_items(schema, "themes")


def test_feed_and_comment_payload_use_compact_layout() -> None:
    feed = build_feed_messages(
        feed_id="f1",
        user_id="u1",
        related_movie_id=None,
        known_movie_ids=None,
        content="좋은 영화였어요",
    )
    _assert_feed_comment_payload_layout(feed, cache_prefix="ontology:feed:v3:vocab:")

    comment = build_comment_messages(
        comment_id="c1",
        feed_id="f1",
        user_id="u1",
        mentioned_user_ids=None,
        parent_feed_summary=None,
        content="동의합니다",
    )
    _assert_feed_comment_payload_layout(comment, cache_prefix="ontology:comment:v3:vocab:")
