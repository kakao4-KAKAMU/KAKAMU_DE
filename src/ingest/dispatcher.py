"""aggregate_type → 처리 핸들러."""

from __future__ import annotations

import logging
from typing import Any, Callable, Mapping

logger = logging.getLogger(__name__)

Handler = Callable[[Mapping[str, Any]], None]


class IngestDispatcher:
    def __init__(self) -> None:
        self._handlers: dict[str, Handler] = {}

    def register(self, aggregate_type: str, handler: Handler) -> None:
        self._handlers[aggregate_type] = handler

    def dispatch(self, aggregate_type: str, payload: Mapping[str, Any]) -> None:
        handler = self._handlers.get(aggregate_type)
        if handler is None:
            raise ValueError(f"No handler for aggregate_type={aggregate_type}")
        handler(payload)


def default_dispatcher() -> IngestDispatcher:
    """테스트/스텁용 기본 디스패처."""

    def _noop(_: Mapping[str, Any]) -> None:
        logger.debug("noop ingest handler")

    d = IngestDispatcher()
    for t in ("movie", "feed", "comment"):
        d.register(t, _noop)
    return d


__all__ = ["IngestDispatcher", "default_dispatcher"]
