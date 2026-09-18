from datetime import datetime, timedelta, timezone

import pytest

from app.api.routers import auth as auth_router
from app.core.security import create_access_token, hash_password, verify_password
from app.models import RefreshToken, User, VerificationCode


def _make_user(db_session, email, *, password="oldpass123", nickname="Tester"):
    user = User(nickname=nickname, email=email, password_hash=hash_password(password))
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def _headers(user):
    return {"Authorization": f"Bearer {create_access_token(str(user.id))}"}


def _stub_mail(monkeypatch):
    """把 Resend 换成内存收集器，返回已发送邮件列表。"""
    monkeypatch.setenv("RESEND_API_KEY", "testkey")
    monkeypatch.setenv("RESEND_FROM", "Aurora Blog <no-reply@aurorablog.me>")
    sent = []

    def fake_send(payload):
        sent.append(payload)
        return {"id": "x"}

    monkeypatch.setattr(auth_router.resend.Emails, "send", fake_send)
    return sent


def test_send_password_code_requires_login(client):
    res = client.post("/api/auth/password/send-code")
    assert res.status_code == 401


def test_send_password_code_sends_to_bound_email(client, db_session, monkeypatch):
    user = _make_user(db_session, "pw-send@example.com")
    sent = _stub_mail(monkeypatch)

    res = client.post("/api/auth/password/send-code", headers=_headers(user))
    assert res.status_code == 200
    assert res.json()["email"] == "pw-send@example.com"

    assert len(sent) == 1
    assert sent[0]["to"] == "pw-send@example.com"
    assert "修改密码" in sent[0]["subject"]

    row = db_session.query(VerificationCode).filter(VerificationCode.email == user.email).first()
    assert row is not None
    assert len(row.code) == 6 and row.code.isdigit()
    # 验证码内容应该出现在邮件正文里
    assert row.code in sent[0]["html"]


def test_send_password_code_rate_limited(client, db_session, monkeypatch):
    user = _make_user(db_session, "pw-ratelimit@example.com")
    _stub_mail(monkeypatch)

    assert client.post("/api/auth/password/send-code", headers=_headers(user)).status_code == 200
    res = client.post("/api/auth/password/send-code", headers=_headers(user))
    assert res.status_code == 429


def test_update_password_requires_login(client):
    res = client.put("/api/auth/password", json={"code": "123456", "new_password": "newpass123"})
    assert res.status_code == 401


def test_update_password_with_wrong_code_keeps_old_password(client, db_session, monkeypatch):
    user = _make_user(db_session, "pw-wrongcode@example.com")
    _stub_mail(monkeypatch)
    client.post("/api/auth/password/send-code", headers=_headers(user))

    res = client.put(
        "/api/auth/password",
        json={"code": "000000", "new_password": "newpass123"},
        headers=_headers(user),
    )
    assert res.status_code == 400

    db_session.refresh(user)
    assert verify_password("oldpass123", user.password_hash)


def test_update_password_with_expired_code(client, db_session, monkeypatch):
    user = _make_user(db_session, "pw-expired@example.com")
    _stub_mail(monkeypatch)
    client.post("/api/auth/password/send-code", headers=_headers(user))

    row = db_session.query(VerificationCode).filter(VerificationCode.email == user.email).first()
    row.expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
    db_session.commit()

    res = client.put(
        "/api/auth/password",
        json={"code": row.code, "new_password": "newpass123"},
        headers=_headers(user),
    )
    assert res.status_code == 400


def test_update_password_success_and_revokes_sessions(client, db_session, monkeypatch):
    user = _make_user(db_session, "pw-success@example.com")
    _stub_mail(monkeypatch)

    session = RefreshToken(
        user_id=user.id,
        token_hash="hash-1",
        expires_at=datetime.now(timezone.utc) + timedelta(days=30),
    )
    db_session.add(session)
    db_session.commit()

    client.post("/api/auth/password/send-code", headers=_headers(user))
    code = db_session.query(VerificationCode).filter(VerificationCode.email == user.email).first().code

    res = client.put(
        "/api/auth/password",
        json={"code": code, "new_password": "brand-new-pass"},
        headers=_headers(user),
    )
    assert res.status_code == 200
    assert res.json()["revoked_sessions"] == 1

    db_session.refresh(user)
    assert verify_password("brand-new-pass", user.password_hash)
    assert not verify_password("oldpass123", user.password_hash)

    # 验证码用完即删
    assert db_session.query(VerificationCode).filter(VerificationCode.email == user.email).count() == 0

    db_session.refresh(session)
    assert session.revoked_at is not None


def test_update_password_rejects_same_password(client, db_session, monkeypatch):
    user = _make_user(db_session, "pw-same@example.com")
    _stub_mail(monkeypatch)
    client.post("/api/auth/password/send-code", headers=_headers(user))
    code = db_session.query(VerificationCode).filter(VerificationCode.email == user.email).first().code

    res = client.put(
        "/api/auth/password",
        json={"code": code, "new_password": "oldpass123"},
        headers=_headers(user),
    )
    assert res.status_code == 400


@pytest.mark.parametrize(
    "payload",
    [
        {"code": "12345", "new_password": "newpass123"},   # 验证码长度不对
        {"code": "123456", "new_password": "12345"},       # 新密码太短
    ],
)
def test_update_password_validates_payload(client, db_session, monkeypatch, payload):
    user = _make_user(db_session, f"pw-invalid-{payload['code']}@example.com")
    _stub_mail(monkeypatch)

    res = client.put("/api/auth/password", json=payload, headers=_headers(user))
    assert res.status_code == 422
