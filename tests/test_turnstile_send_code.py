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

    monkeypatch.setenv("RESEND_API_KEY", "testkey")
    monkeypatch.setenv("RESEND_FROM", "Aurora Blog <no-reply@aurorablog.me>")

    def fake_send(_payload):
        return {"id": "x"}

    monkeypatch.setattr(auth_router.resend.Emails, "send", fake_send)
    res = client.post("/api/auth/send-code", json={"email": "a1@b.com", "turnstile_token": "ok"})
    assert res.status_code == 200


def test_send_code_missing_resend_key_returns_500(client, monkeypatch):
    from app.api.routers import auth as auth_router

    monkeypatch.setattr(auth_router, "verify_turnstile", lambda *_: True)
    monkeypatch.setenv("RESEND_API_KEY", "")
    res = client.post("/api/auth/send-code", json={"email": "a2@b.com", "turnstile_token": "ok"})
    assert res.status_code == 500


def test_send_code_success_uses_resend_from(client, monkeypatch):
    from app.api.routers import auth as auth_router

    monkeypatch.setattr(auth_router, "verify_turnstile", lambda *_: True)
    monkeypatch.setenv("RESEND_API_KEY", "testkey")
    monkeypatch.setenv("RESEND_FROM", "Aurora Blog <no-reply@aurorablog.me>")

    sent = {}

    def fake_send(payload):
        sent.update(payload)
        return {"id": "x"}

    monkeypatch.setattr(auth_router.resend.Emails, "send", fake_send)
    res = client.post("/api/auth/send-code", json={"email": "a3@b.com", "turnstile_token": "ok"})
    assert res.status_code == 200
    assert sent["from"] == "Aurora Blog <no-reply@aurorablog.me>"


def test_send_code_resend_failure_returns_502_with_reason(client, monkeypatch):
    from app.api.routers import auth as auth_router

    monkeypatch.setattr(auth_router, "verify_turnstile", lambda *_: True)
    monkeypatch.setenv("RESEND_API_KEY", "testkey")

    class FakeResendError(Exception):
        error_type = "validation_error"
        code = 400
        message = "API key is invalid"
        suggested_action = None

    def fake_send(_payload):
        raise FakeResendError("API key is invalid")

    monkeypatch.setattr(auth_router.resend.Emails, "send", fake_send)
    res = client.post("/api/auth/send-code", json={"email": "a4@b.com", "turnstile_token": "ok"})
    # 502：上游邮件服务拒绝，且把原因带出来，方便前端/运维定位
    assert res.status_code == 502
    assert "API key is invalid" in res.json()["detail"]
