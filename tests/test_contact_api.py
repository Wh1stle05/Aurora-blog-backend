from app.models import Contact


def test_contact_submission_persists_message(client, db_session, monkeypatch):
    from app.api.routers import contact as contact_router

    monkeypatch.setattr(contact_router, "verify_turnstile", lambda *_args, **_kwargs: True)
    payload = {
        "nickname": "Alice",
        "email": "contact-api-alice@example.com",
        "content": "Hello from the contact page.",
        "turnstile_token": "ok",
    }

    res = client.post("/api/contact", json=payload)

    assert res.status_code == 200
    assert res.json() == {"ok": True}

    saved = db_session.query(Contact).filter(Contact.email == payload["email"]).order_by(Contact.id.desc()).first()
    assert saved is not None
    assert saved.nickname == payload["nickname"]
    assert saved.content == payload["content"]
