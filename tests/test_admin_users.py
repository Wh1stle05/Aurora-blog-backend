from app.api import deps
from app.core.security import create_access_token, hash_password
from app.models import User


def test_admin_users_include_avatar(client, db_session, monkeypatch):
    admin_email = "admin@example.com"
    monkeypatch.setattr(deps, "ADMIN_EMAILS", {admin_email})

    user = User(
        nickname="Admin",
        email=admin_email,
        password_hash=hash_password("testpass123"),
        avatar="/uploads/avatars/test.jpg",
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    token = create_access_token(str(user.id))
    res = client.get(
        "/api/admin/users?skip=0&limit=10",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data, list)

    matched = next((u for u in data if u["id"] == user.id), None)
    assert matched is not None
    assert matched["avatar"] == "/uploads/avatars/test.jpg"
