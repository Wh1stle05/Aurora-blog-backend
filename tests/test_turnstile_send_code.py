import pytest


def test_send_code_missing_token_returns_400(client):
    res = client.post("/api/auth/send-code", json={"email": "a@b.com"})
    assert res.status_code == 400


def test_send_code_invalid_token_returns_403(client, monkeypatch):
    from app.api.routers import auth as auth_router

    def fake_verify(*_args, **_kwargs):
        return False

    monkeypatch.setattr(auth_router, "verify_turnstile", fake_verify)
    res = client.post("/api/auth/send-code", json={"email": "a@b.com", "turnstile_token": "bad"})
    assert res.status_code == 403


def test_send_code_valid_token_returns_200(client, monkeypatch):
    from app.api.routers import auth as auth_router

    def fake_verify(*_args, **_kwargs):
        return True

    monkeypatch.setattr(auth_router, "verify_turnstile", fake_verify)
    res = client.post("/api/auth/send-code", json={"email": "a@b.com", "turnstile_token": "ok"})
    assert res.status_code == 200
