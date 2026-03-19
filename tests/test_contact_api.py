from app.models import Contact


def test_contact_submission_persists_message(client, db_session):
    payload = {
        "nickname": "Alice",
        "email": "alice@example.com",
        "content": "Hello from the contact page.",
    }

    res = client.post("/api/contact", json=payload)

    assert res.status_code == 200
    assert res.json() == {"ok": True}

    saved = db_session.query(Contact).filter(Contact.email == payload["email"]).one()
    assert saved.nickname == payload["nickname"]
    assert saved.content == payload["content"]
