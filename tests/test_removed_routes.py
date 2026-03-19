def test_monitor_ban_route_is_not_available(client):
    res = client.post("/api/monitor/ban/1")
    assert res.status_code == 404


def test_single_image_upload_route_is_not_available(client):
    res = client.post("/api/admin/upload")
    assert res.status_code == 404


def test_reaction_summary_route_is_not_available(client):
    res = client.get("/api/reactions/summary", params={"target_type": "post", "target_id": 1})
    assert res.status_code == 404


def test_refresh_route_is_not_available(client):
    res = client.post("/api/auth/refresh")
    assert res.status_code == 404


def test_post_create_route_is_not_available(client):
    res = client.post("/api/posts", json={"title": "x", "content": "y"})
    assert res.status_code == 405


def test_post_update_route_is_not_available(client):
    res = client.put("/api/posts/1", json={"title": "x"})
    assert res.status_code == 405


def test_post_delete_route_is_not_available(client):
    res = client.delete("/api/posts/1")
    assert res.status_code == 405
