import uuid

from app.api import deps
from app.core.security import create_access_token, hash_password
from app.models import Post, User


def _seed_admin(db_session):
    suffix = uuid.uuid4().hex[:8]
    admin = User(
        nickname="Admin",
        email=f"admin-{suffix}@example.com",
        password_hash=hash_password("adminpass123"),
    )
    db_session.add(admin)
    db_session.commit()
    db_session.refresh(admin)
    return admin


def _admin_headers(admin):
    token = create_access_token(str(admin.id))
    return {"Authorization": f"Bearer {token}"}


def test_upload_full_post_triggers_frontend_revalidation(client, db_session, monkeypatch):
    from app.api.routers import admin as admin_router

    admin = _seed_admin(db_session)
    monkeypatch.setattr(deps, "ADMIN_EMAILS", {admin.email})

    calls = []
    monkeypatch.setattr(
        admin_router,
        "trigger_frontend_revalidation",
        lambda **kwargs: calls.append(kwargs),
    )

    suffix = uuid.uuid4().hex[:8]
    response = client.post(
        "/api/admin/posts/upload-full",
        headers=_admin_headers(admin),
        files={"md_file": (f"Git-commands-{suffix}.md", f"# Git commands {suffix}\n\n正文".encode("utf-8"), "text/markdown")},
    )

    assert response.status_code == 200
    payload = response.json()
    assert calls == [{"paths": ["/", "/blog"], "slug": payload["slug"]}]


def test_delete_post_triggers_frontend_revalidation(client, db_session, monkeypatch):
    from app.api.routers import admin as admin_router

    admin = _seed_admin(db_session)
    monkeypatch.setattr(deps, "ADMIN_EMAILS", {admin.email})
    slug = f"post-slug-{uuid.uuid4().hex[:8]}"
    post = Post(title="Post", slug=slug, content="Body", author_id=admin.id)
    db_session.add(post)
    db_session.commit()
    db_session.refresh(post)

    calls = []
    monkeypatch.setattr(
        admin_router,
        "trigger_frontend_revalidation",
        lambda **kwargs: calls.append(kwargs),
    )

    response = client.delete(f"/api/admin/posts/{post.id}", headers=_admin_headers(admin))

    assert response.status_code == 200
    assert calls == [{"paths": ["/", "/blog"], "slug": slug}]


def test_restore_revision_triggers_frontend_revalidation(client, db_session, monkeypatch):
    from app.api.routers import admin as admin_router
    from app.models import PostRevision

    admin = _seed_admin(db_session)
    monkeypatch.setattr(deps, "ADMIN_EMAILS", {admin.email})
    slug = f"post-slug-{uuid.uuid4().hex[:8]}"
    post = Post(title="Post", slug=slug, content="Current", author_id=admin.id)
    db_session.add(post)
    db_session.flush()
    revision = PostRevision(post_id=post.id, content="Old body", revision_note="seed")
    db_session.add(revision)
    db_session.commit()
    db_session.refresh(revision)

    calls = []
    monkeypatch.setattr(
        admin_router,
        "trigger_frontend_revalidation",
        lambda **kwargs: calls.append(kwargs),
    )

    response = client.post(f"/api/admin/revisions/{revision.id}/restore", headers=_admin_headers(admin))

    assert response.status_code == 200
    assert calls == [{"paths": ["/", "/blog"], "slug": slug}]


def test_about_update_triggers_frontend_revalidation(client, db_session, monkeypatch):
    from app.api.routers import about as about_router

    admin = _seed_admin(db_session)
    monkeypatch.setattr(deps, "ADMIN_EMAILS", {admin.email})

    calls = []
    monkeypatch.setattr(
        about_router,
        "trigger_frontend_revalidation",
        lambda **kwargs: calls.append(kwargs),
    )

    response = client.post(
        "/api/about",
        headers=_admin_headers(admin),
        json={"content": "# About\n\nUpdated"},
    )

    assert response.status_code == 200
    assert calls == [{"paths": ["/about"]}]
