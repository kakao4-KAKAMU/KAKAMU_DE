"""Neo4j tool 결과 파싱 단위 테스트."""

from __future__ import annotations

import json

from langchain_core.messages import ToolMessage

from src.chat.nodes.tools import (
    _flatten_neo4j_row,
    _rows_to_retrieved,
    merge_tool_results_into_state,
    resolve_retrieved_media,
)


def test_flatten_neo4j_row_unwraps_row_wrapper() -> None:
    row = {
        "row": {
            "movie_id": "m1",
            "title": "기생충",
            "plot_raw": "줄거리",
        }
    }
    flat = _flatten_neo4j_row(row)
    assert flat["movie_id"] == "m1"
    assert flat["title"] == "기생충"
    assert flat["plot_raw"] == "줄거리"


def test_rows_to_retrieved_splits_mixed_row_wrapper_payload() -> None:
    rows = [
        {
            "row": {
                "movie_id": "m1",
                "title": "기생충",
                "plot_raw": "줄거리",
            }
        },
        {
            "row": {
                "feed_id": "f1",
                "summary": "감상 후기",
            }
        },
    ]
    movies, feeds = _rows_to_retrieved(rows)
    assert len(movies) == 1
    assert len(feeds) == 1
    assert movies[0]["movie_id"] == "m1"
    assert feeds[0]["feed_id"] == "f1"


def test_merge_tool_results_parses_combined_movie_and_feed_response() -> None:
    tool_payload = json.dumps(
        {
            "status": "ok",
            "cypher": "CALL { ... } RETURN row",
            "rows": [
                {
                    "row": {
                        "movie_id": "m1",
                        "title": "기생충",
                        "plot_raw": "줄거리",
                    }
                },
                {
                    "row": {
                        "feed_id": "f1",
                        "summary": "감상 후기",
                    }
                },
            ],
        },
        ensure_ascii=False,
    )
    out = merge_tool_results_into_state(
        {"messages": [ToolMessage(content=tool_payload, tool_call_id="call_1")]},
        {},
    )
    assert out["intent_scope"] == "both"
    assert out["retrieved_movies"][0]["movie_id"] == "m1"
    assert out["retrieved_feeds"][0]["feed_id"] == "f1"
    assert out["graph_query_results"][0]["rows"][0]["row"]["movie_id"] == "m1"


def test_resolve_retrieved_media_reads_graph_query_results_with_row_wrapper() -> None:
    movies, feeds = resolve_retrieved_media(
        {
            "graph_query_results": [
                {
                    "cypher": "CALL { ... } RETURN row",
                    "rows": [
                        {"row": {"movie_id": "m1", "title": "기생충"}},
                        {"row": {"feed_id": "f1", "summary": "후기"}},
                    ],
                }
            ],
        },
        top_k=10,
    )
    assert movies[0]["movie_id"] == "m1"
    assert feeds[0]["feed_id"] == "f1"


def test_rows_to_retrieved_ignores_null_movie_id_from_union_padding() -> None:
    rows = [
        {
            "movie_id": None,
            "feed_id": "f1",
            "summary": "후기",
        }
    ]
    movies, feeds = _rows_to_retrieved(rows)
    assert movies == []
    assert feeds[0]["feed_id"] == "f1"
