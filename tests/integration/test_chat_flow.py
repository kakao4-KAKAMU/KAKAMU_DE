"""Integration smoke: 실 Neo4j / Postgres / vLLM 가 모두 켜진 상태에서만 의미.

Run with::

    RUN_INTEGRATION=1 pytest tests/integration -m integration -q

본 테스트는 default `pytest` 실행에서는 skip 된다 (tests/conftest.py 참고).
"""

from __future__ import annotations

import os
import uuid

import pytest

pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def app_client():
    fastapi_testclient = pytest.importorskip("fastapi.testclient")
    from src.api.app import create_app

    return fastapi_testclient.TestClient(create_app())


def test_full_chat_flow_smoke(app_client) -> None:
    if not os.environ.get("RUN_INTEGRATION"):
        pytest.skip("RUN_INTEGRATION=1 이 아니면 외부 인프라 호출을 건너뜁니다.")

    resp = app_client.post(
        "/chat",
        json={
            "user_id": f"u-{uuid.uuid4()}",
            "message": "잔잔한 한국 영화 추천해줘",
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["session_id"]
    assert body["arm_id"]
