from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from app.api import deps
from app.core.security import create_access_token, hash_password
from app.models import Post, User
from app.utils.datetimes import parse_optional_datetime


def _naive(value: str) -> datetime:
    """把 API 返回的时间字符串归一化成可比较的 naive datetime。"""
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return parsed.astimezone(timezone.utc).replace(tzinfo=None) if parsed.tzinfo else parsed


@pytest.fixture()
def admin_headers(db_session, monkeypatch):
    # 每个测试用独立邮箱：测试之间共享同一个 sqlite 内存库
    email = f"published-at-admin-{uuid4().hex[:8]}@example.com"
    monkeypatch.setattr(deps, "ADMIN_EMAILS", {email})
    user = User(nickname="Admin", email=email, password_hash=hash_password("testpass123"))
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return {"Authorization": f"Bearer {create_access_token(str(user.id))}"}, user


def _make_post(db_session, author, *, slug, title="时间测试", content="正文内容", **kwargs):
    post = Post(title=title, slug=slug, content=content, author_id=author.id, **kwargs)
    db_session.add(post)
    db_session.commit()
    db_session.refresh(post)
    return post


def test_display_time_defaults_to_upload_time(client, db_session, admin_headers):
    _, author = admin_headers
    post = _make_post(db_session, author, slug="display-default")

    res = client.get("/api/posts/display-default?skip_view=true")
    assert res.status_code == 200
    body = res.json()

    assert body["published_at"] is None
    assert _naive(body["created_at"]) == _naive(body["uploaded_at"]) == post.created_at.replace(tzinfo=None)


def test_manual_published_at_overrides_display_time(client, db_session, admin_headers):
    _, author = admin_headers
    manual = datetime(2026, 3, 25, 14, 42, 9, tzinfo=timezone.utc)
    post = _make_post(db_session, author, slug="display-manual", published_at=manual)

    body = client.get("/api/posts/display-manual?skip_view=true").json()
    assert _naive(body["created_at"]) == manual.replace(tzinfo=None)
    assert _naive(body["published_at"]) == manual.replace(tzinfo=None)
    # 真实上传时间仍然是数据库里的 created_at
    assert _naive(body["uploaded_at"]) == post.created_at


def test_admin_can_update_and_clear_published_at(client, db_session, admin_headers):
    headers, author = admin_headers
    post = _make_post(db_session, author, slug="display-edit")
    new_time = (datetime.now(timezone.utc) - timedelta(days=30)).replace(microsecond=0)

    res = client.put(
        f"/api/admin/posts/{post.id}",
        json={"published_at": new_time.isoformat()},
        headers=headers,
    )
    assert res.status_code == 200
    assert _naive(res.json()["created_at"]) == new_time.replace(tzinfo=None)

    # 显式传 null -> 回到上传时间
    res = client.put(f"/api/admin/posts/{post.id}", json={"published_at": None}, headers=headers)
    assert res.status_code == 200
    body = res.json()
    assert body["published_at"] is None
    assert _naive(body["created_at"]) == _naive(body["uploaded_at"])

    # 不传该字段 -> 不改动
    res = client.put(f"/api/admin/posts/{post.id}", json={"title": "改个标题"}, headers=headers)
    assert res.status_code == 200
    assert res.json()["published_at"] is None


def test_paginated_list_exposes_display_time_and_sorts_by_it(client, db_session, admin_headers):
    _, author = admin_headers
    older = datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    newer = datetime(2026, 8, 1, 0, 0, 0, tzinfo=timezone.utc)
    _make_post(db_session, author, slug="sort-old-created-new-display", published_at=newer)
    _make_post(db_session, author, slug="sort-new-created-old-display", published_at=older)

    res = client.get("/api/posts/paginated?page=1&page_size=50")
    assert res.status_code == 200
    rows = res.json()["data"]["data"]

    slugs = [r["slug"] for r in rows]
    assert slugs.index("sort-old-created-new-display") < slugs.index("sort-new-created-old-display")

    first = next(r for r in rows if r["slug"] == "sort-old-created-new-display")
    assert _naive(first["created_at"]) == newer.replace(tzinfo=None)
    assert _naive(first["published_at"]) == newer.replace(tzinfo=None)
    assert _naive(first["uploaded_at"]) != newer.replace(tzinfo=None)


def test_upload_full_accepts_published_at(client, db_session, admin_headers):
    headers, _ = admin_headers
    manual = "2026-04-01T08:30:00Z"

    res = client.post(
        "/api/admin/posts/upload-full",
        data={"published_at": manual, "slug": "upload-with-time"},
        files={"md_file": ("upload-with-time.md", "# 上传时间测试\n\n正文".encode(), "text/markdown")},
        headers=headers,
    )
    assert res.status_code == 200

    body = client.get("/api/posts/upload-with-time?skip_view=true").json()
    assert _naive(body["created_at"]) == datetime(2026, 4, 1, 8, 30, tzinfo=timezone.utc).replace(tzinfo=None)
    assert _naive(body["published_at"]) == _naive(body["created_at"])
    assert _naive(body["uploaded_at"]) != _naive(body["created_at"])


def test_upload_full_rejects_invalid_published_at(client, db_session, admin_headers):
    headers, _ = admin_headers

    res = client.post(
        "/api/admin/posts/upload-full",
        data={"published_at": "不是时间"},
        files={"md_file": ("bad-time.md", "# 坏时间\n\n正文".encode(), "text/markdown")},
        headers=headers,
    )
    assert res.status_code == 400


@pytest.mark.parametrize(
    "value,expected",
    [
        (None, None),
        ("", None),
        ("   ", None),
        ("2026-03-25T14:42:09Z", datetime(2026, 3, 25, 14, 42, 9, tzinfo=timezone.utc)),
        ("2026-03-25T22:42:09+08:00", datetime(2026, 3, 25, 14, 42, 9, tzinfo=timezone.utc)),
        ("2026-03-25T14:42:09", datetime(2026, 3, 25, 14, 42, 9, tzinfo=timezone.utc)),
        ("2026-03-25", datetime(2026, 3, 25, tzinfo=timezone.utc)),
    ],
)
def test_parse_optional_datetime(value, expected):
    assert parse_optional_datetime(value) == expected


def test_parse_optional_datetime_rejects_garbage():
    with pytest.raises(ValueError):
        parse_optional_datetime("2026/03/25 14:42")
