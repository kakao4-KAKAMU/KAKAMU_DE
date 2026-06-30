"""POST /search/movie/title endpoint tests."""

from __future__ import annotations

from unittest.mock import MagicMock

from fastapi.testclient import TestClient

from src.api.app import create_app
from src.api.dependencies import AppContainer, set_container


def _build_fake_container() -> AppContainer:
    template_executor = MagicMock()
    template_executor.execute.return_value = [
        {
            "movie_id": "m1",
            "title": "기생충",
            "matched_title": "기생충",
            "title_country": "KR",
            "score": 1.5,
        }
    ]
    return AppContainer(
        settings=MagicMock(),
        embedder=MagicMock(),
        policy=MagicMock(),
        template_executor=template_executor,
        intent_resolver=MagicMock(),
        chat_history=MagicMock(),
        outbox=MagicMock(),
        chat_graph=MagicMock(),
        feedback_recorder=MagicMock(),
    )


def test_search_movie_by_title() -> None:
    container = _build_fake_container()
    set_container(container)
    client = TestClient(create_app())

    response = client.post(
        "/search/movie/title",
        json={"query": "기생충", "country": "KR", "top_k": 5},
    )

    assert response.status_code == 200
    body = response.json()
    assert len(body["movies"]) == 1
    assert body["movies"][0]["movie_id"] == "m1"
    assert body["movies"][0]["matched_title"] == "기생충"
    assert body["movies"][0]["title_country"] == "KR"

    template_executor = container.template_executor
    template_executor.execute.assert_called_once()
    assert template_executor.execute.call_args.args[0] == "movie_title_search"
    params = template_executor.execute.call_args.args[1]
    assert params["country"] == "KR"
    assert params["top_k"] == 5
    assert "기생충" in params["query"]

    set_container(None)
