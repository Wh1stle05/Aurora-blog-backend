import pytest
import uuid
from sqlalchemy import func

from app import deps
from app.auth import create_access_token, hash_password
from app.models import Comment, Post, User


def _flatten_ids(nodes):
    ids = []
    for node in nodes:
        ids.append(node["id"])
        ids.extend(_flatten_ids(node.get("children", [])))
    return ids


@pytest.fixture()
def seeded_comments(db_session):
    suffix = uuid.uuid4().hex
    author = User(
        nickname="Author",
        email=f"author-{suffix}@example.com",
        password_hash=hash_password("testpass123"),
    )
    admin_email = f"admin-{suffix}@example.com"
    admin = User(
        nickname="Admin",
        email=admin_email,
        password_hash=hash_password("adminpass123"),
    )
    db_session.add_all([author, admin])
    db_session.flush()

    post = Post(
        title="Post",
        content="Content",
        author_id=author.id,
    )
    db_session.add(post)
    db_session.flush()

    visible = Comment(
        post_id=post.id,
        author_id=author.id,
        content="visible",
        is_visible=1,
    )
    hidden = Comment(
        post_id=post.id,
        author_id=author.id,
        content="hidden",
        is_visible=0,
    )
    hidden_child = Comment(
        post_id=post.id,
        author_id=author.id,
        parent=hidden,
        content="hidden-child",
        is_visible=1,
    )
    deleted_parent = Comment(
        post_id=post.id,
        author_id=author.id,
        content="deleted",
        is_visible=-1,
        deleted_at=func.now(),
    )
    deleted_child = Comment(
        post_id=post.id,
        author_id=author.id,
        parent=deleted_parent,
        content="deleted-child",
        is_visible=1,
    )
    db_session.add_all([visible, hidden, hidden_child, deleted_parent, deleted_child])
    db_session.commit()

    return {
        "post_id": post.id,
        "admin_id": admin.id,
        "admin_email": admin_email,
        "visible_id": visible.id,
        "admin_hidden_id": hidden.id,
        "hidden_child_id": hidden_child.id,
        "deleted_parent_id": deleted_parent.id,
        "deleted_child_id": deleted_child.id,
    }


def test_public_comments_hide_user_deleted_and_descendants(client, seeded_comments):
    post_id = seeded_comments["post_id"]
    res = client.get(f"/api/posts/{post_id}/comments")
    assert res.status_code == 200
    data = res.json()
    ids = set(_flatten_ids(data))

    assert seeded_comments["deleted_parent_id"] not in ids
    assert seeded_comments["deleted_child_id"] not in ids


def test_public_comments_include_admin_hidden_with_placeholder(client, seeded_comments):
    post_id = seeded_comments["post_id"]
    res = client.get(f"/api/posts/{post_id}/comments")
    assert res.status_code == 200
    data = res.json()

    hidden = next(c for c in data if c["id"] == seeded_comments["admin_hidden_id"])
    assert hidden["is_visible"] == 0
    assert hidden["content"] in ("", "—— 该内容已被管理员隐藏 ——")

    hidden_child_ids = _flatten_ids(hidden.get("children", []))
    assert seeded_comments["hidden_child_id"] in hidden_child_ids


def test_admin_comments_include_visibility(client, seeded_comments, monkeypatch):
    monkeypatch.setattr(deps, "ADMIN_EMAILS", {seeded_comments["admin_email"]})
    token = create_access_token(str(seeded_comments["admin_id"]))

    res = client.get(
        "/api/admin/comments?skip=0&limit=10",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data
    assert "is_visible" in data[0]


def test_admin_comment_set_visibility(client, seeded_comments, monkeypatch):
    monkeypatch.setattr(deps, "ADMIN_EMAILS", {seeded_comments["admin_email"]})
    token = create_access_token(str(seeded_comments["admin_id"]))

    comment_id = seeded_comments["admin_hidden_id"]
    res = client.post(
        f"/api/admin/comments/{comment_id}/toggle_visibility",
        headers={"Authorization": f"Bearer {token}"},
        json={"is_visible": 1},
    )
    assert res.status_code == 200
    assert res.json()["is_visible"] == 1
