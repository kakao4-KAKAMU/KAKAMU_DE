"""LangGraph PostgresSaver checkpoint 어댑터.

SOLID
-----
- SRP : PostgresSaver lifecycle + DDL 적용만 담당.
- DIP : ChatGraph 는 본 모듈이 반환하는 ``Checkpointer`` (or None) 에만 의존.
"""

from __future__ import annotations

import logging
from contextlib import AbstractContextManager
from typing import Optional

from langgraph.checkpoint.postgres import PostgresSaver

from src.config.settings import PostgresSettings, get_settings

logger = logging.getLogger(__name__)


def _conninfo(settings: PostgresSettings) -> str:
    return (
        f"host={settings.host} port={settings.port} dbname={settings.database} "
        f"user={settings.user} password={settings.password}"
    )


def setup_checkpoint_tables(settings: Optional[PostgresSettings] = None) -> None:
    """LangGraph 체크포인트 DDL 을 멱등 적용한다.

    ``PostgresSaver.setup()`` 은 내부 migration 을 모두 적용한다.
    """

    cfg = settings or get_settings().postgres
    with PostgresSaver.from_conn_string(_conninfo(cfg)) as saver:
        saver.setup()
        logger.info("LangGraph PostgresSaver checkpoint tables ready.")


class CheckpointerSession(AbstractContextManager[PostgresSaver]):
    """Application lifecycle 동안 PostgresSaver 를 유지하는 헬퍼.

    사용 예
    -------
    >>> with CheckpointerSession() as saver:
    ...     graph = build_chat_graph(deps, checkpointer=saver)
    ...     graph.invoke(state)
    """

    def __init__(self, settings: Optional[PostgresSettings] = None) -> None:
        self._settings = settings or get_settings().postgres
        self._ctx: Optional[AbstractContextManager[PostgresSaver]] = None
        self._saver: Optional[PostgresSaver] = None

    def __enter__(self) -> PostgresSaver:
        self._ctx = PostgresSaver.from_conn_string(_conninfo(self._settings))
        self._saver = self._ctx.__enter__()
        return self._saver

    def __exit__(self, exc_type, exc, tb) -> None:
        if self._ctx is not None:
            self._ctx.__exit__(exc_type, exc, tb)
        self._ctx = None
        self._saver = None


__all__ = ["CheckpointerSession", "setup_checkpoint_tables"]
