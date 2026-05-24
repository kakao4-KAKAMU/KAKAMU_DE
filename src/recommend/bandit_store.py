"""Thompson bandit 상태의 PostgreSQL write-through 저장소.

SOLID
-----
- SRP : ``bandit_state`` / ``bandit_arms`` 테이블 read/write 만 담당.
- DIP : ThompsonBandit 은 본 추상에만 의존한다 (in-memory 와 교체 가능).
"""

from __future__ import annotations

import json
import logging
from contextlib import AbstractContextManager, contextmanager
from dataclasses import dataclass
from typing import Callable, Iterable, Iterator, Optional, Protocol

import psycopg

from src.config.settings import PostgresSettings, get_settings
from src.persistence.db import get_connection
from src.recommend.arms import DEFAULT_ARMS, BanditArm

logger = logging.getLogger(__name__)

ConnectionFactory = Callable[[], AbstractContextManager[psycopg.Connection]]


@dataclass(frozen=True)
class BanditStateRow:
    arm_id: str
    context_key: str
    alpha: float
    beta: float
    n_pulls: int
    n_rewards: int


class BanditStateRepository(Protocol):
    """ThompsonBandit 에서 사용하는 최소 인터페이스."""

    def load_all(self) -> list[BanditStateRow]: ...

    def upsert_state(self, row: BanditStateRow) -> None: ...


_SEED_ARMS_SQL = """
INSERT INTO bandit_arms (arm_id, context_key, weights, description)
VALUES (%s, %s, %s::jsonb, %s)
ON CONFLICT (arm_id) DO UPDATE
    SET weights = EXCLUDED.weights,
        description = EXCLUDED.description
"""

_UPSERT_STATE_SQL = """
INSERT INTO bandit_state (arm_id, context_key, alpha, beta, n_pulls, n_rewards, updated_at)
VALUES (%s, %s, %s, %s, %s, %s, NOW())
ON CONFLICT (arm_id, context_key) DO UPDATE
    SET alpha = EXCLUDED.alpha,
        beta = EXCLUDED.beta,
        n_pulls = EXCLUDED.n_pulls,
        n_rewards = EXCLUDED.n_rewards,
        updated_at = NOW()
"""

_LOAD_STATE_SQL = """
SELECT arm_id, context_key, alpha, beta, n_pulls, n_rewards FROM bandit_state
"""


class BanditStore:
    """psycopg connection pool 기반 BanditState 영속화."""

    def __init__(
        self,
        settings: Optional[PostgresSettings] = None,
        *,
        connection_factory: Optional[ConnectionFactory] = None,
    ) -> None:
        self._settings = settings or get_settings().postgres
        self._connection_factory = connection_factory

    @contextmanager
    def _connection(self) -> Iterator[psycopg.Connection]:
        if self._connection_factory is not None:
            with self._connection_factory() as conn:
                yield conn
            return
        with get_connection(self._settings) as conn:
            yield conn

    # ------------------------------------------------------------------
    # Seed
    # ------------------------------------------------------------------
    def seed_arms(self, arms: Iterable[BanditArm] | None = None) -> None:
        arms = list(arms or DEFAULT_ARMS)
        with self._connection() as conn:
            with conn.cursor() as cur:
                for arm in arms:
                    cur.execute(
                        _SEED_ARMS_SQL,
                        (
                            arm.arm_id,
                            "default",
                            json.dumps(dict(arm.weights)),
                            arm.description,
                        ),
                    )
            conn.commit()

    # ------------------------------------------------------------------
    # State
    # ------------------------------------------------------------------
    def load_all(self) -> list[BanditStateRow]:
        with self._connection() as conn:
            with conn.cursor() as cur:
                cur.execute(_LOAD_STATE_SQL)
                rows = cur.fetchall()
        return [
            BanditStateRow(
                arm_id=str(r[0]),
                context_key=str(r[1]),
                alpha=float(r[2]),
                beta=float(r[3]),
                n_pulls=int(r[4]),
                n_rewards=int(r[5]),
            )
            for r in rows
        ]

    def upsert_state(self, row: BanditStateRow) -> None:
        with self._connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    _UPSERT_STATE_SQL,
                    (
                        row.arm_id,
                        row.context_key,
                        row.alpha,
                        row.beta,
                        row.n_pulls,
                        row.n_rewards,
                    ),
                )
            conn.commit()

    def upsert_many(self, rows: Iterable[BanditStateRow]) -> None:
        rows = list(rows)
        if not rows:
            return
        with self._connection() as conn:
            with conn.cursor() as cur:
                cur.executemany(
                    _UPSERT_STATE_SQL,
                    [
                        (
                            r.arm_id,
                            r.context_key,
                            r.alpha,
                            r.beta,
                            r.n_pulls,
                            r.n_rewards,
                        )
                        for r in rows
                    ],
                )
            conn.commit()


__all__ = [
    "BanditStateRepository",
    "BanditStateRow",
    "BanditStore",
    "ConnectionFactory",
]
