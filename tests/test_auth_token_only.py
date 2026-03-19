from app.core.security import hash_password
from app.models import User


def test_login_does_not_set_cookie(client, db_session, monkeypatch):
    from app.api.routers import auth as auth_router

    monkeypatch.setattr(auth_router, "verify_turnstile", lambda *_: True)

    user = User(email="tokenonly@example.com", nickname="tokenonly", password_hash=hash_password("pass1234"))
    db_session.add(user)
    db_session.commit()

    res = client.post(
        "/api/auth/login",
        json={"email": user.email, "password": "pass1234", "turnstile_token": "ok"},
    )

    assert res.status_code == 200
    assert "access_token" in res.json()
    assert "set-cookie" not in {key.lower() for key in res.headers.keys()}
