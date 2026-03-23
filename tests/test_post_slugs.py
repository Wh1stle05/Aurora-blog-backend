from app.api import deps
from app.core.security import create_access_token, hash_password
from app.models import User


def make_admin(client, db_session, monkeypatch, email="admin@example.com"):
    monkeypatch.setattr(deps, "ADMIN_EMAILS", {email})
    admin = User(
        nickname="Admin",
        email=email,
        password_hash=hash_password("testpass123"),
    )
    db_session.add(admin)
    db_session.commit()
    db_session.refresh(admin)
    token = create_access_token(str(admin.id))
    return admin, {"Authorization": f"Bearer {token}"}


def upload_markdown_post(client, headers, title, body, slug=None):
    markdown = f"# {title}\n\n{body}".encode("utf-8")
    data = {}
    if slug is not None:
        data["slug"] = slug
    return client.post(
        "/api/admin/posts/upload-full",
        headers=headers,
        data=data,
        files={"md_file": (f"{title}.md", markdown, "text/markdown")},
    )


def test_upload_full_accepts_manual_slug_override_and_public_slug_lookup(client, db_session, monkeypatch):
    _, headers = make_admin(client, db_session, monkeypatch, email="slug-admin@example.com")

    res = upload_markdown_post(
        client,
        headers,
        title="Git Commands Cheat Sheet",
        body="A short guide.",
        slug="git-cheat-sheet",
    )
    assert res.status_code == 200
    assert res.json()["slug"] == "git-cheat-sheet"

    detail = client.get("/api/posts/git-cheat-sheet", params={"skip_view": "true"})
    assert detail.status_code == 200
    assert detail.json()["slug"] == "git-cheat-sheet"


def test_upload_full_generates_unique_slugs_for_duplicate_titles(client, db_session, monkeypatch):
    _, headers = make_admin(client, db_session, monkeypatch, email="dup-slug-admin@example.com")

    first = upload_markdown_post(client, headers, title="Deploy Notes", body="First body")
    second = upload_markdown_post(client, headers, title="Deploy Notes", body="Second body")

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["slug"] == "deploy-notes"
    assert second.json()["slug"] == "deploy-notes-2"


def test_paginated_posts_include_slug_and_summary(client, db_session, monkeypatch):
    _, headers = make_admin(client, db_session, monkeypatch, email="list-slug-admin@example.com")

    res = upload_markdown_post(
        client,
        headers,
        title="SEO Migration Checklist",
        body="This post explains the migration steps in detail.",
    )
    assert res.status_code == 200

    listing = client.get("/api/posts/paginated", params={"page": 1, "page_size": 6})
    assert listing.status_code == 200
    payload = listing.json()["data"]["data"]
    matched = next(item for item in payload if item["title"] == "SEO Migration Checklist")
    assert matched["slug"] == "seo-migration-checklist"
    assert matched["summary"]
