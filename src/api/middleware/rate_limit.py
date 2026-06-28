"""IP 기반 rate limiting (비용 높은 엔드포인트)."""

from __future__ import annotations

import asyncio
import time
from collections import defaultdict, deque

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

_EXPENSIVE_PATHS = frozenset(
    {
        "/chat/stream",
        "/recommend/movie",
        "/recommend/feed",
    }
)


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client is not None:
        return request.client.host
    return "unknown"


class _SlidingWindowLimiter:
    def __init__(self, *, max_requests: int, window_sec: float = 60.0) -> None:
        self._max_requests = max_requests
        self._window_sec = window_sec
        self._events: dict[str, deque[float]] = defaultdict(deque)
        self._lock = asyncio.Lock()

    async def allow(self, key: str) -> bool:
        async with self._lock:
            now = time.monotonic()
            bucket = self._events[key]
            while bucket and bucket[0] <= now - self._window_sec:
                bucket.popleft()
            if len(bucket) >= self._max_requests:
                return False
            bucket.append(now)
            return True


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(
        self,
        app,
        *,
        default_rpm: int,
        expensive_rpm: int,
    ) -> None:
        super().__init__(app)
        self._default = _SlidingWindowLimiter(max_requests=default_rpm)
        self._expensive = _SlidingWindowLimiter(max_requests=expensive_rpm)

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        if request.method != "POST":
            return await call_next(request)

        path = request.url.path.rstrip("/") or "/"
        if path == "/healthz":
            return await call_next(request)

        limiter = self._expensive if path in _EXPENSIVE_PATHS else self._default
        key = f"{path}:{_client_ip(request)}"
        if not await limiter.allow(key):
            return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded. Try again later."},
            )
        return await call_next(request)


__all__ = ["RateLimitMiddleware"]
