"""SSE node 필터 단위 테스트."""

from __future__ import annotations

from src.api.routers.chat.sse_filter import (
    filter_sse_node_chunk,
    public_error_detail,
    sse_node_mode,
)


def test_sse_node_mode_local_dev_full() -> None:
    assert sse_node_mode("local") == "full"
    assert sse_node_mode("dev") == "full"


def test_sse_node_mode_stg_prod_filtered() -> None:
    assert sse_node_mode("stg") == "filtered"
    assert sse_node_mode("prod") == "filtered"


def test_filter_sse_node_chunk_strips_internal_state() -> None:
    chunk = {
        "agent": {
            "messages": [{"role": "assistant", "content": "secret"}],
            "graph_query_results": [{"cypher": "MATCH (m:Movie) RETURN m", "rows": []}],
        },
        "persist_history": {
            "reply": "안녕하세요",
            "reply_metadata": {"movie": [{"type": "movie", "id": "m1"}]},
            "ontology_ref": {"movie_ids": ["m1"]},
        },
    }
    filtered = filter_sse_node_chunk(chunk)
    assert filtered["agent"] == {"status": "ok"}
    assert filtered["persist_history"]["reply"] == "안녕하세요"
    assert "ontology_ref" not in filtered["persist_history"]


def test_public_error_detail_masks_prod() -> None:
    assert public_error_detail("prod", RuntimeError("db password leaked")) == (
        "An internal error occurred"
    )
    assert "db password" in public_error_detail("local", RuntimeError("db password leaked"))
