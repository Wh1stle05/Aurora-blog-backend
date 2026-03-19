import pytest
from datetime import datetime, timedelta, timezone
from app.models import VerificationCode, User


def test_refresh_token_model_available():
    from app.models import RefreshToken
    assert RefreshToken is not None

def test_register_and_login(client, db_session, monkeypatch):
    email = "test@example.com"
    code = "123456"
    # Create verification code
    vc = VerificationCode(email=email, code=code, expires_at=datetime.now(timezone.utc) + timedelta(minutes=10))
    db_session.add(vc)
    db_session.commit()

    register_payload = {
        "nickname": "测试用户",
        "email": email,
        "password": "testpass123",
        "code": code
    }
    res = client.post("/api/auth/register", json=register_payload)
    assert res.status_code == 200
    data = res.json()
    assert data["email"] == register_payload["email"]
    assert data["nickname"] == register_payload["nickname"]

    from app.api.routers import auth as auth_router
    monkeypatch.setattr(auth_router, "verify_turnstile", lambda *_: True)
    login_payload = {"email": email, "password": "testpass123", "turnstile_token": "ok"}
    res = client.post("/api/auth/login", json=login_payload)
    assert res.status_code == 200
    token = res.json()["access_token"]
    assert token

    res = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    me = res.json()
    assert me["email"] == email


def test_register_duplicate_email(client, db_session):
    email = "dup@example.com"
    code = "654321"
    
    vc = VerificationCode(email=email, code=code, expires_at=datetime.now(timezone.utc) + timedelta(minutes=10))
    db_session.add(vc)
    db_session.commit()

    payload = {"nickname": "AA", "email": email, "password": "testpass123", "code": code}
    res = client.post("/api/auth/register", json=payload)
    assert res.status_code == 200

    # Try duplicate
    res = client.post("/api/auth/register", json=payload)
    assert res.status_code == 400
