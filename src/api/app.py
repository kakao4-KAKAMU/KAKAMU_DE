"""FastAPI application factory.

SOLID
-----
- SRP : 본 모듈은 app 인스턴스 조립만 담당. 비즈니스 로직은 routers 모듈에서.

실행::

    uvicorn src.api.app:app --host 0.0.0.0 --port 8080
"""

from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.routers import router
from src.config.settings import get_settings

logger = logging.getLogger(__name__)

origins = [
    'http://localhost:8081',
    'http://210.109.52.56',
]

def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="movie-recommend-system",
        version="0.1.0",
        description="Knowledge-graph based movie recommendation + LLM chat",
        openapi_url="openapi.json",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(router)
    logger.info("FastAPI app initialized (env=%s)", settings.env)
    return app


app = create_app()


__all__ = ["app", "create_app"]
