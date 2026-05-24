"""BanditStore write-through round-trip (psycopg cursor mocked)."""

from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator
from unittest.mock import MagicMock

from src.recommend.bandit import ThompsonBandit
from src.recommend.bandit_store import BanditStateRow, BanditStore


class _FakeStore:
    """In-memory stand-in implementing BanditStateRepository."""

    def __init__(self) -> None:
        self.rows: dict[tuple[str, str], BanditStateRow] = {}

    def load_all(self) -> list[BanditStateRow]:
        return list(self.rows.values())

    def upsert_state(self, row: BanditStateRow) -> None:
        self.rows[(row.arm_id, row.context_key)] = row


def test_bandit_writes_through_on_update() -> None:
    store = _FakeStore()
    bandit = ThompsonBandit(store=store)
    bandit.update("baseline", "default", 1.0)
    row = store.rows[("baseline", "default")]
    assert row.alpha > 1.0
    assert row.n_pulls == 1
    assert row.n_rewards == 1


def test_bandit_hydrates_from_store_on_init() -> None:
    store = _FakeStore()
    store.rows[("baseline", "default")] = BanditStateRow(
        arm_id="baseline",
        context_key="default",
        alpha=5.0,
        beta=2.0,
        n_pulls=10,
        n_rewards=4,
    )
    bandit = ThompsonBandit(store=store)
    st = bandit.get_state("baseline", "default")
    assert st.alpha == 5.0
    assert st.beta == 2.0
    assert st.n_pulls == 10
    assert st.n_rewards == 4


def test_banditstore_uses_injected_connection_factory() -> None:
    """``BanditStore`` must reuse the injected connection factory (no direct psycopg.connect)."""

    conn = MagicMock()
    cursor = MagicMock()
    conn.cursor.return_value.__enter__.return_value = cursor
    conn.cursor.return_value.__exit__.return_value = False

    @contextmanager
    def factory() -> Iterator[MagicMock]:
        yield conn

    store = BanditStore(connection_factory=factory)
    store.upsert_state(
        BanditStateRow(
            arm_id="vec_heavy",
            context_key="u-1",
            alpha=2.0,
            beta=1.0,
            n_pulls=3,
            n_rewards=2,
        )
    )
    sql = cursor.execute.call_args[0][0]
    assert "bandit_state" in sql
    assert conn.commit.called
