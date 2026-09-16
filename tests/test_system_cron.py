import pytest

from app.api.routers import monitor as monitor_router
from app.api.routers import system as system_router


def test_health_reports_database_status(client):
    response = client.get("/api/system/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["database"] is True


def test_cron_monitor_requires_configuration(client, monkeypatch):
    monkeypatch.delenv("CRON_SECRET", raising=False)
    response = client.get("/api/system/cron/monitor")
    assert response.status_code == 503


def test_cron_monitor_rejects_wrong_secret(client, monkeypatch):
    monkeypatch.setenv("CRON_SECRET", "top-secret")
    assert client.get("/api/system/cron/monitor").status_code == 401
    assert client.get("/api/system/cron/monitor?secret=nope").status_code == 401
    assert (
        client.get(
            "/api/system/cron/monitor",
            headers={"Authorization": "Bearer nope"},
        ).status_code
        == 401
    )


@pytest.mark.parametrize(
    "request_kwargs",
    [
        {"headers": {"Authorization": "Bearer top-secret"}},
        {"params": {"secret": "top-secret"}},
    ],
)
def test_cron_monitor_runs_once_without_load_check(client, monkeypatch, request_kwargs):
    monkeypatch.setenv("CRON_SECRET", "top-secret")
    calls = []

    def fake_run_monitor_once(*, check_system_load=True):
        calls.append(check_system_load)
        return {"checked_system_load": check_system_load, "skipped": False, "banned_users": []}

    monkeypatch.setattr(system_router, "run_monitor_once", fake_run_monitor_once)

    response = client.get("/api/system/cron/monitor", **request_kwargs)
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["banned_users"] == []
    assert calls == [False]


def test_run_monitor_once_skips_abuse_check_when_load_is_normal(monkeypatch):
    monkeypatch.setattr(
        monitor_router,
        "_read_system_load",
        lambda: {"cpu": 1.0, "memory": 10.0, "disk": 10.0},
    )
    monkeypatch.setattr(monitor_router, "ban_abusive_users", lambda: pytest.fail("should not run"))

    result = monitor_router.run_monitor_once(check_system_load=True)
    assert result["skipped"] is True
    assert result["banned_users"] == []


def test_run_monitor_once_checks_abuse_when_load_is_high(monkeypatch):
    monkeypatch.setattr(
        monitor_router,
        "_read_system_load",
        lambda: {"cpu": 99.0, "memory": 10.0, "disk": 10.0},
    )
    monkeypatch.setattr(monitor_router, "ban_abusive_users", lambda: [7])

    result = monitor_router.run_monitor_once(check_system_load=True)
    assert result["skipped"] is False
    assert result["banned_users"] == [7]


def test_run_monitor_once_serverless_mode_skips_load_metrics(monkeypatch):
    def explode():
        raise AssertionError("psutil must not be used in serverless mode")

    monkeypatch.setattr(monitor_router, "_read_system_load", explode)
    monkeypatch.setattr(monitor_router, "ban_abusive_users", lambda: [])

    result = monitor_router.run_monitor_once(check_system_load=False)
    assert result["checked_system_load"] is False
    assert result["load"] is None
    assert result["skipped"] is False
