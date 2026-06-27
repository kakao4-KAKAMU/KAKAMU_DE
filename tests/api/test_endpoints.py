"""FastAPI endpoints (fastapi.testclient + container override)."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from src.api.app import create_app
from src.api.dependencies import AppContainer, set_container
from src.recommend.arms import BanditArm
from src.recommend.intent_resolver import ResolvedIntent


def _parse_sse_events(body: str) -> list[tuple[str | None, str]]:
    """SSE 본문을 (event, data) 목록으로 파싱."""
    events: list[tuple[str | None, str]] = []
    current_event: str | None = None
    current_data: list[str] = []
    for line in body.splitlines():
        if line.startswith("event:"):
            current_event = line.removeprefix("event:").strip()
        elif line.startswith("data:"):
            current_data.append(line.removeprefix("data:").strip())
        elif line == "" and current_data:
            events.append((current_event, "\n".join(current_data)))
            current_event = None
            current_data = []
    if current_data:
        events.append((current_event, "\n".join(current_data)))
    return events


async def _fake_chat_astream(
    state: dict[str, Any], config: dict[str, Any] | None = None
) -> AsyncIterator[dict[str, Any]]:
    del state, config
    yield {
        "persist_history": {
            "reply": "추천드려요",
            "ontology_ref": {"movie_ids": ["m1"]},
        }
    }


def _build_fake_container() -> AppContainer:
    history = MagicMock()
    history.open_session.return_value = None
    history.append.return_value = 42
    session = MagicMock()
    session.persona_id = None
    history.get_session_by_id.return_value = session

    intent = MagicMock()
    intent.resolve.return_value = ResolvedIntent(
        keywords=["성장"], themes=["성장"], moods=["잔잔한"]
    )

    embedder = MagicMock()
    embedder.embed.return_value = [0.1, 0.2]

    policy = MagicMock()
    policy.select_arm.return_value = BanditArm(
        "balanced",
        {"w_vec": 0.5, "w_kw": 0.15, "w_theme": 0.15, "w_mood": 0.1, "w_user": 0.1},
    )

    template_executor = MagicMock()
    template_executor.execute.return_value = [
        {
            "movie_id": "m1",
            "title": "Movie 1",
            "plot_summary": "A dream within a dream.",
            "score": 0.9,
        }
    ]

    chat_graph = MagicMock()
    chat_graph.astream = _fake_chat_astream

    feedback_recorder = MagicMock()
    feedback_recorder.record.return_value = MagicMock(arm_id="balanced", reward=3.0)

    outbox = MagicMock()
    outbox.enqueue.return_value = 7

    return AppContainer(
        settings=MagicMock(),
        embedder=embedder,
        policy=policy,
        template_executor=template_executor,
        intent_resolver=intent,
        chat_history=history,
        outbox=outbox,
        chat_graph=chat_graph,
        feedback_recorder=feedback_recorder,
    )


@pytest.fixture(autouse=True)
def _override_container():
    container = _build_fake_container()
    set_container(container)
    yield container
    set_container(None)


@pytest.fixture
def client() -> TestClient:
    return TestClient(create_app())


def test_healthz(client: TestClient) -> None:
    resp = client.get("/healthz")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_chat_stream_returns_sse(client: TestClient, _override_container) -> None:
    resp = client.post(
        "/chat/stream",
        json={"user_id": "u1", "message": "잔잔한 영화 추천", "session_id": "s1"},
    )
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/event-stream")

    events = _parse_sse_events(resp.text)
    event_names = [name for name, _ in events]
    assert "open" in event_names
    assert "node" in event_names
    assert "done" in event_names

    _override_container.chat_history.open_session.assert_called_once()
    _override_container.chat_history.append.assert_called()


def test_recommend_uses_intent_and_template(
    client: TestClient, _override_container
) -> None:
    resp = client.post(
        "/recommend/movie",
        json={"user_id": "u1", "query": "잔잔한 성장 영화"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["arm_id"] == "balanced"
    assert body["themes"] == ["성장"]
    assert body["moods"] == ["잔잔한"]
    assert body["movies"][0]["movie_id"] == "m1"
    _override_container.intent_resolver.resolve.assert_called_once_with("잔잔한 성장 영화")
    _override_container.template_executor.execute.assert_called_once()


def test_ingest_movie_enqueues(client: TestClient, _override_container) -> None:
    resp = client.post(
        "/ingest/movie/regist",
        json={
            "payload": {
                "movie_id": "m-inception",
                "title": "Inception",
                "plot": "A thief enters dreams.",
            }
        },
    )
    assert resp.status_code == 200
    assert resp.json() == {"outbox_id": 7}
    _override_container.outbox.enqueue.assert_called_once()


def test_feedback_records_reward(client: TestClient, _override_container) -> None:
    resp = client.post(
        "/feedback",
        json={
            "user_id": "u1",
            "arm_id": "balanced",
            "action": "like",
            "content_type": "movie",
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["arm_id"] == "balanced"
    assert body["reward"] == 3.0
    _override_container.feedback_recorder.record.assert_called_once()
