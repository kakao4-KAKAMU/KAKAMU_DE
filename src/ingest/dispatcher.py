"""aggregate_type → 처리 핸들러 (extract + load)."""

from __future__ import annotations

import logging
from typing import Any, Callable, Mapping

logger = logging.getLogger(__name__)

Handler = Callable[[Mapping[str, Any]], None]


def mock_extract(aggregate_type: str, payload: Mapping[str, Any]) -> dict[str, Any]:
    """테스트/스텁용 온톨로지 추출."""
    return {"aggregate_type": aggregate_type, "source": dict(payload)}


def mock_load(aggregate_type: str, extracted: Mapping[str, Any]) -> None:
    """테스트/스텁용 Neo4j 적재."""
    logger.debug("mock_load %s keys=%s", aggregate_type, list(extracted.keys()))


def mock_extract_load_handler(aggregate_type: str) -> Handler:
    def _handler(payload: Mapping[str, Any]) -> None:
        extracted = mock_extract(aggregate_type, payload)
        mock_load(aggregate_type, extracted)

    return _handler


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
    """movie / feed / comment → mock extract+load."""
    d = IngestDispatcher()
    for t in ("movie", "feed", "comment"):
        d.register(t, mock_extract_load_handler(t))
    return d


__all__ = [
    "Handler",
    "IngestDispatcher",
    "default_dispatcher",
    "mock_extract",
    "mock_load",
    "mock_extract_load_handler",
]
