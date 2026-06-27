"""FastAPI application factory.

SOLID
-----
- SRP : 본 모듈은 app 인스턴스 조립만 담당. 비즈니스 로직은 routers 모듈에서.

실행::

    uvicorn src.api.app:app --host 0.0.0.0 --port 8080
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi


from src.api.middleware.rate_limit import RateLimitMiddleware
from src.api.middleware.request_size import RequestSizeLimitMiddleware
from src.api.routers import router
from src.config.settings import get_settings

logger = logging.getLogger(__name__)

origins = [
    'http://localhost:8081',
    'http://210.109.52.56',
]

@asynccontextmanager
async def _lifespan(app: FastAPI):
    yield
    try:
        from src.api.dependencies import get_container

        get_container().outbox.flush()
    except Exception:
        logger.exception("Failed to flush outbox on shutdown")


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        root_path="/chat-api",
        lifespan=_lifespan,
    )

    def custom_openapi():
        if app.openapi_schema:
            return app.openapi_schema
        openapi_schema = get_openapi(
            version="0.1.0",
            title="movie-recommend-system",
            description="Knowledge-graph based movie recommendation + LLM chat",
            openapi_version="3.2.0",
            routes=router.routes,
        )
        app.openapi_schema = openapi_schema
        return app.openapi_schema

    app.openapi = custom_openapi
    sec = settings.api_security
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(
        RateLimitMiddleware,
        default_rpm=sec.rate_limit_rpm_default,
        expensive_rpm=sec.rate_limit_rpm_expensive,
    )
    app.add_middleware(
        RequestSizeLimitMiddleware,
        max_body_bytes=sec.max_request_body_bytes,
    )
    app.include_router(router)
    logger.info("FastAPI app initialized (env=%s)", settings.env)
    return app


app = create_app()


__all__ = ["app", "create_app"]
