"""chat reply JSON schema tests."""

from __future__ import annotations

from typing import Any

from src.ontology.prompts.reply import get_reply_schema_json
from src.ontology.schema import ChatReplyBoth, ChatReplyMovie, build_strict_object_schema


def _assert_strict_object(node: dict[str, Any]) -> None:
    if node.get("type") == "object" and "properties" in node:
        assert node.get("additionalProperties") is False
        assert set(node["required"]) == set(node["properties"].keys())
        for prop in node["properties"].values():
            _assert_strict_object(prop)
    if node.get("type") == "array" and "items" in node:
        _assert_strict_object(node["items"])
    if "anyOf" in node:
        for item in node["anyOf"]:
            _assert_strict_object(item)


def test_movie_reply_schema_is_strict_with_movie_metadata() -> None:
    wrapper = get_reply_schema_json("movie")
    schema = wrapper["schema"]

    assert wrapper["strict"] is True
    assert wrapper["name"] == "reply_movie_ontology"
    _assert_strict_object(schema)

    movie_items = schema["properties"]["metadata"]["properties"]["movie"]["items"]
    assert set(movie_items["required"]) == {"type", "id"}
    assert movie_items["properties"]["type"]["enum"] == ["movie"]


def test_both_reply_schema_requires_movie_and_feed_arrays() -> None:
    schema = get_reply_schema_json("both")["schema"]
    metadata_props = schema["properties"]["metadata"]["properties"]

    assert "movie" in metadata_props
    assert "feed" in metadata_props
    assert metadata_props["feed"]["items"]["properties"]["type"]["enum"] == ["feed"]


def test_none_reply_schema_has_empty_metadata_object() -> None:
    schema = get_reply_schema_json("none")["schema"]
    metadata = schema["properties"]["metadata"]

    assert metadata["properties"] == {}
    assert metadata["required"] == []


def test_chat_reply_models_match_strict_schema_builder() -> None:
    movie_schema = build_strict_object_schema(ChatReplyMovie)
    both_schema = build_strict_object_schema(ChatReplyBoth)

    assert "reply" in movie_schema["properties"]
    assert "movie" in movie_schema["properties"]["metadata"]["properties"]
    assert "feed" in both_schema["properties"]["metadata"]["properties"]


def test_build_reply_messages_puts_candidates_in_system_not_user() -> None:
    from src.ontology.prompts.reply import build_reply_messages

    chat_payload = build_reply_messages(
        scope="both",
        payload={
            "query": "잔잔한 영화와 후기 추천",
            "intent_scope": "both",
            "movie_filters": {"genres": ["drama"]},
            "feed_filters": {"categories": ["review"]},
            "movie_candidates": [
                {
                    "movie_id": "m1",
                    "title": "Movie 1",
                    "producing_year": 2019,
                    "country": "kr",
                    "plot_summary": "plot",
                    "score": 0.9,
                }
            ],
            "feed_candidates": [
                {
                    "feed_id": "f1",
                    "summary": "좋은 영화였어요",
                    "sentiment_score": 0.8,
                    "score": 0.7,
                }
            ],
        },
    )
    messages = chat_payload["messages"]
    system_text = "\n".join(m["content"] for m in messages if m["role"] == "system")
    user_text = next(m["content"] for m in messages if m["role"] == "user")

    assert "[영화 추천 후보 목록]" in system_text
    assert "[피드 추천 후보 목록]" in system_text
    assert '"movie_id": "m1"' in system_text
    assert '"feed_id": "f1"' in system_text
    assert "movie_candidates" not in user_text
    assert "feed_candidates" not in user_text
    assert "잔잔한 영화와 후기 추천" in user_text
