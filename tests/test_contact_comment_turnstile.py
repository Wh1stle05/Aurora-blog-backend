import uuid

from app.core.security import create_access_token, hash_password
from app.models import Contact, Post, User


def test_contact_missing_turnstile_returns_400(client):
    res = client.post(
        "/api/contact",
        json={
            "nickname": "Alice",
            "email": "alice@example.com",
            "content": "Hello",
        },
    )

    assert res.status_code == 400
    assert res.json()["detail"] == "缺少人机验证"


def test_contact_invalid_turnstile_returns_403(client, monkeypatch):
    from app.api.routers import contact as contact_router

    monkeypatch.setattr(contact_router, "verify_turnstile", lambda *_args, **_kwargs: False)

    res = client.post(
        "/api/contact",
        json={
            "nickname": "Alice",
            "email": "alice@example.com",
            "content": "Hello",
            "turnstile_token": "bad",
        },
    )

    assert res.status_code == 403
    assert res.json()["detail"] == "人机验证失败"


def test_contact_valid_turnstile_persists_message(client, db_session, monkeypatch):
    from app.api.routers import contact as contact_router

    monkeypatch.setattr(contact_router, "verify_turnstile", lambda *_args, **_kwargs: True)

    payload = {
        "nickname": "Alice",
        "email": f"alice-{uuid.uuid4().hex[:8]}@example.com",
        "content": "Hello from the contact page.",
        "turnstile_token": "ok",
    }

    res = client.post("/api/contact", json=payload)

    assert res.status_code == 200
    assert res.json() == {"ok": True}

    saved = db_session.query(Contact).filter(Contact.email == payload["email"]).one()
    assert saved.nickname == payload["nickname"]
    assert saved.content == payload["content"]


def _seed_user_and_post(db_session):
    suffix = uuid.uuid4().hex[:8]
    user = User(
        nickname="Commenter",
        email=f"commenter-{suffix}@example.com",
        password_hash=hash_password("pass1234"),
    )
    db_session.add(user)
    db_session.flush()

    post = Post(
        title="Post",
        slug=f"post-{suffix}",
        content="Content",
        author_id=user.id,
    )
    db_session.add(post)
    db_session.commit()
    db_session.refresh(user)
    db_session.refresh(post)
    return user, post


def test_comment_missing_turnstile_returns_400(client, db_session):
    user, post = _seed_user_and_post(db_session)
    token = create_access_token(str(user.id))

    res = client.post(
        f"/api/posts/{post.id}/comments",
        headers={"Authorization": f"Bearer {token}"},
        json={"content": "Hello"},
    )

    assert res.status_code == 400
    assert res.json()["detail"] == "缺少人机验证"


def test_comment_invalid_turnstile_returns_403(client, db_session, monkeypatch):
    from app.api.routers import comments as comments_router

    monkeypatch.setattr(comments_router, "verify_turnstile", lambda *_args, **_kwargs: False)
    user, post = _seed_user_and_post(db_session)
    token = create_access_token(str(user.id))

    res = client.post(
        f"/api/posts/{post.id}/comments",
        headers={"Authorization": f"Bearer {token}"},
        json={"content": "Hello", "turnstile_token": "bad"},
    )

    assert res.status_code == 403
    assert res.json()["detail"] == "人机验证失败"


def test_comment_valid_turnstile_creates_comment(client, db_session, monkeypatch):
    from app.api.routers import comments as comments_router

    monkeypatch.setattr(comments_router, "verify_turnstile", lambda *_args, **_kwargs: True)
    user, post = _seed_user_and_post(db_session)
    token = create_access_token(str(user.id))

    res = client.post(
        f"/api/posts/{post.id}/comments",
        headers={"Authorization": f"Bearer {token}"},
        json={"content": "Hello", "turnstile_token": "ok"},
    )

    assert res.status_code == 200
    payload = res.json()
    assert payload["content"] == "Hello"
    assert payload["post_id"] == post.id
    assert payload["author"]["id"] == user.id
