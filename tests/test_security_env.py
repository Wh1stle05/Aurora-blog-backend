import importlib

import pytest

from app.core import security


def _reload_with(monkeypatch, **env):
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    return importlib.reload(security)


def test_empty_env_values_fall_back_to_defaults(monkeypatch):
    """Vercel 上把变量留成空字符串时，不能变成 int('') 崩溃。"""
    module = _reload_with(
        monkeypatch,
        JWT_EXPIRES_MINUTES="",
        REFRESH_TOKEN_EXPIRES_DAYS="",
        JWT_SECRET="",
        REFRESH_TOKEN_PEPPER="",
    )
    try:
        assert module.JWT_EXPIRES_MINUTES == 120
        assert module.REFRESH_TOKEN_EXPIRES_DAYS == 30
        assert module.JWT_SECRET == "dev_secret_change_me"
        assert module.hash_refresh_token("token") == security.hash_refresh_token("token")
    finally:
        monkeypatch.undo()
        importlib.reload(security)


def test_invalid_int_env_raises_readable_error(monkeypatch):
    monkeypatch.setenv("JWT_EXPIRES_MINUTES", "not-a-number")
    with pytest.raises(RuntimeError, match="JWT_EXPIRES_MINUTES"):
        importlib.reload(security)

    monkeypatch.undo()
    importlib.reload(security)


def test_valid_env_values_are_used(monkeypatch):
    module = _reload_with(
        monkeypatch,
        JWT_EXPIRES_MINUTES="7",
        REFRESH_TOKEN_EXPIRES_DAYS="3",
        JWT_SECRET="unit-test-secret",
    )
    try:
        assert module.JWT_EXPIRES_MINUTES == 7
        assert module.REFRESH_TOKEN_EXPIRES_DAYS == 3
        assert module.JWT_SECRET == "unit-test-secret"
    finally:
        monkeypatch.undo()
        importlib.reload(security)
