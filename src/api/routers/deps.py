"""라우터 공통 FastAPI 의존성."""

from __future__ import annotations

from src.api.dependencies import AppContainer, get_container


def get_app_container() -> AppContainer:
    return get_container()


__all__ = ["get_app_container"]
