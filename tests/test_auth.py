import pytest
from datetime import datetime, timedelta, timezone
from app.models import VerificationCode, User


def test_refresh_token_model_available():
    from app.models import RefreshToken
    assert RefreshToken is not None


def test_refresh_token_hashing_is_deterministic(monkeypatch):
    monkeypatch.setenv("REFRESH_TOKEN_PEPPER", "pepper")
    from app.core import security
    token = "rawtoken"
    a = security.hash_refresh_token(token)
    b = security.hash_refresh_token(token)
    assert a == b


def test_refresh_flow_rotates_token(client, db_session, monkeypatch):
    from app.api.routers import auth as auth_router
    monkeypatch.setattr(auth_router, "verify_turnstile", lambda *_: True)

    from app.models import User
    from app.core.security import hash_password
    user = User(email="r@e.com", nickname="r", password_hash=hash_password("pass"))
    db_session.add(user)
    db_session.commit()

    res = client.post("/api/auth/login", json={"email": "r@e.com", "password": "pass", "turnstile_token": "ok"})
    assert res.status_code == 200
    assert "access_token" in res.json()

    res2 = client.post("/api/auth/refresh")
    assert res2.status_code == 200
    assert "access_token" in res2.json()


def test_get_current_user_uses_authorization_header_only(client, db_session, monkeypatch):
    from app.api.routers import auth as auth_router
    monkeypatch.setattr(auth_router, "verify_turnstile", lambda *_: True)

    from app.models import User
    from app.core.security import hash_password
    user = User(email="h@e.com", nickname="h", password_hash=hash_password("pass"))
    db_session.add(user)
    db_session.commit()

    res = client.post("/api/auth/login", json={"email": "h@e.com", "password": "pass", "turnstile_token": "ok"})
    token = res.json()["access_token"]

    res = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200


def test_register_rejects_expired_code(client, db_session):
    email = "expired@example.com"
    vc = VerificationCode(
        email=email,
        code="000000",
        expires_at=datetime.now(timezone.utc) - timedelta(minutes=1),
    )
    db_session.add(vc)
    db_session.commit()

    payload = {"nickname": "AA", "email": email, "password": "pass", "code": "000000"}
    res = client.post("/api/auth/register", json=payload)
    assert res.status_code == 400


def test_cors_allows_admin_origin(client):
    res = client.options(
        "/api/auth/login",
        headers={
            "Origin": "https://admin.aurorablog.me",
            "Access-Control-Request-Method": "POST",
        },
    )
    assert res.status_code in (200, 204)
    assert res.headers.get("access-control-allow-origin") == "https://admin.aurorablog.me"
    assert res.headers.get("access-control-allow-credentials") == "true"

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
