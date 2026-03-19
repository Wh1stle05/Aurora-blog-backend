from uuid import uuid4

from app.models import User
from app.core.security import hash_password


def _seed_user(db):
    email = f"tester-login-{uuid4().hex}@example.com"
    user = User(
        nickname="tester",
        email=email,
        password_hash=hash_password("pass123"),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def test_login_missing_turnstile_returns_400(client, db_session):
    user = _seed_user(db_session)
    res = client.post("/api/auth/login", json={"email": user.email, "password": "pass123"})
    assert res.status_code == 400


def test_login_invalid_turnstile_returns_403(client, db_session, monkeypatch):
    from app.api.routers import auth as auth_router
    monkeypatch.setattr(auth_router, "verify_turnstile", lambda *_: False)
    user = _seed_user(db_session)
    res = client.post(
        "/api/auth/login",
        json={"email": user.email, "password": "pass123", "turnstile_token": "bad"},
    )
    assert res.status_code == 403


def test_login_valid_turnstile_returns_200(client, db_session, monkeypatch):
    from app.api.routers import auth as auth_router
    monkeypatch.setattr(auth_router, "verify_turnstile", lambda *_: True)
    user = _seed_user(db_session)
    res = client.post(
        "/api/auth/login",
        json={"email": user.email, "password": "pass123", "turnstile_token": "ok"},
    )
    assert res.status_code == 200
