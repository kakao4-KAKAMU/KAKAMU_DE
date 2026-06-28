"""FastAPI 진입점.

``from src.api import create_app`` 으로 app 인스턴스 팩토리를 얻을 수 있다.
패키지 import 시 app 전체를 로드하지 않아 ingest/bootstrap 등과의 순환 import 를 방지한다.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable

    create_app: Callable[[], Any]


def __getattr__(name: str) -> Any:
    if name == "create_app":
        from src.api.app import create_app as _create_app

        return _create_app
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = ["create_app"]
