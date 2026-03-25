from app.api import deps
from app.core.security import create_access_token, hash_password
from app.models import Contact, User


def test_admin_can_list_contacts(client, db_session, monkeypatch):
    admin_email = "admin@example.com"
    monkeypatch.setattr(deps, "ADMIN_EMAILS", {admin_email})

    admin = User(
        nickname="Admin",
        email=admin_email,
        password_hash=hash_password("password123"),
    )
    db_session.add(admin)
    db_session.add_all([
        Contact(nickname="Alice", email="contact-alice@example.com", content="Hello"),
        Contact(nickname="Bob", email="contact-bob@example.com", content="Need help"),
    ])
    db_session.commit()
    db_session.refresh(admin)

    token = create_access_token(str(admin.id))
    res = client.get(
        "/api/admin/contacts?skip=0&limit=10",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert res.status_code == 200
    data = res.json()
    assert len(data) == 2
    emails = {item["email"] for item in data}
    assert "contact-alice@example.com" in emails
    assert "contact-bob@example.com" in emails


def test_non_admin_cannot_list_contacts(client, db_session):
    user = User(
        nickname="User",
        email="user@example.com",
        password_hash=hash_password("password123"),
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    token = create_access_token(str(user.id))
    res = client.get(
        "/api/admin/contacts?skip=0&limit=10",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert res.status_code == 403
