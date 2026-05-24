from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def pytest_collection_modifyitems(config, items):
    """``integration`` 마커가 붙은 테스트는 기본 skip.

    ``RUN_INTEGRATION=1`` 환경변수 또는 ``-m integration`` 플래그가 있을 때만 실행한다.
    """
    if os.environ.get("RUN_INTEGRATION") == "1":
        return
    expr = (config.getoption("-m") or "").strip()
    if expr == "integration":
        return
    skip = pytest.mark.skip(reason="integration test (set RUN_INTEGRATION=1 to enable)")
    for item in items:
        if "integration" in item.keywords:
            item.add_marker(skip)
