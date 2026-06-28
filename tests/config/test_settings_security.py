"""AppSettings 보안 검증."""

from __future__ import annotations

import pytest

from src.config.settings import AppSettings, get_settings


@pytest.fixture(autouse=True)
def _clear_settings_cache() -> None:
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_prod_rejects_default_neo4j_password(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_ENV", "prod")
    monkeypatch.setenv("NEO4J_PASSWORD", "neo4j")
    monkeypatch.setenv("PG_PASSWORD", "strong-secret")
    with pytest.raises(ValueError, match="NEO4J_PASSWORD"):
        AppSettings()


def test_prod_rejects_default_pg_password(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_ENV", "prod")
    monkeypatch.setenv("NEO4J_PASSWORD", "strong-secret")
    monkeypatch.setenv("PG_PASSWORD", "postgres")
    with pytest.raises(ValueError, match="PG_PASSWORD"):
        AppSettings()


def test_local_allows_default_passwords(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_ENV", "local")
    monkeypatch.setenv("NEO4J_PASSWORD", "neo4j")
    monkeypatch.setenv("PG_PASSWORD", "postgres")
    settings = AppSettings()
    assert settings.env == "local"
