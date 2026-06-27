"""공유 PostgreSQL 커넥션 풀.

SOLID
-----
- SRP: 본 모듈은 ConnectionPool 의 lifecycle 관리만 담당한다.
- DIP: Store 들은 본 모듈의 ``get_pool()`` / ``get_connection()`` 만 사용한다.

psycopg3 의 ``psycopg_pool.ConnectionPool`` 을 사용하며,
동시 채팅 부하 대비 기본 max_size 를 키워두었다.
"""

from __future__ import annotations

import logging
from contextlib import contextmanager
from functools import lru_cache
from typing import Iterator, Optional

import psycopg
from psycopg_pool import ConnectionPool

from src.config.settings import PostgresSettings, get_settings

logger = logging.getLogger(__name__)


def _build_conninfo(settings: PostgresSettings) -> str:
    return (
        f"host={settings.host} port={settings.port} dbname={settings.database} "
        f"user={settings.user} password={settings.password}"
    )


async def async_ping_check(conn):
    """Callback to pre-ping the connection."""
    return conn.execute("SELECT 1")


@lru_cache(maxsize=1)
def get_pool(
    settings: Optional[PostgresSettings] = None,
    *,
    min_size: int = 1,
    max_size: int = 40,
) -> ConnectionPool:
    """프로세스 공용 ConnectionPool 싱글톤."""
    cfg = settings or get_settings().postgres
    conninfo = _build_conninfo(cfg)
    logger.info("Initializing PostgreSQL connection pool (max_size=%d)", max_size)
    pool = ConnectionPool(
        conninfo=conninfo,
        check=async_ping_check,
        min_size=min_size,
        max_size=max_size,
        reconnect_timeout=300,
        timeout=5,
        open=True,
        kwargs={"autocommit": False},
    )
    return pool


@contextmanager
def get_connection(
    settings: Optional[PostgresSettings] = None,
) -> Iterator[psycopg.Connection]:
    """공유 풀에서 connection 을 빌려온다.

    사용 예
    -------
    >>> with get_connection() as conn, conn.cursor() as cur:
    ...     cur.execute("SELECT 1")
    """
    pool = get_pool(settings)
    with pool.connection() as conn:
        yield conn


def close_pool() -> None:
    """테스트/종료 시 풀을 닫고 캐시를 비운다."""
    try:
        pool = get_pool.__wrapped__()  # type: ignore[attr-defined]
    except Exception:
        return
    pool.close()
    get_pool.cache_clear()


__all__ = ["close_pool", "get_connection", "get_pool"]
