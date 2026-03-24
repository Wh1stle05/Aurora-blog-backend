import logging

import httpx

from app.services import revalidate


def test_trigger_frontend_revalidation_sends_user_agent(monkeypatch):
    monkeypatch.setenv("FRONTEND_REVALIDATE_URL", "https://aurorablog.me/api/revalidate")
    monkeypatch.setenv("FRONTEND_REVALIDATE_SECRET", "secret")

    captured = {}

    def fake_post(url, **kwargs):
      captured["url"] = url
      captured["kwargs"] = kwargs
      return httpx.Response(200, request=httpx.Request("POST", url))

    monkeypatch.setattr(revalidate.httpx, "post", fake_post)

    revalidate.trigger_frontend_revalidation(paths=["/", "/blog"], slug="hello-world")

    assert captured["url"] == "https://aurorablog.me/api/revalidate"
    assert captured["kwargs"]["headers"]["User-Agent"] == "aurora-backend-revalidate/1.0"
    assert captured["kwargs"]["json"] == {
        "secret": "secret",
        "paths": ["/", "/blog"],
        "slug": "hello-world",
    }


def test_trigger_frontend_revalidation_logs_response_status_on_http_error(monkeypatch, caplog):
    monkeypatch.setenv("FRONTEND_REVALIDATE_URL", "https://aurorablog.me/api/revalidate")
    monkeypatch.setenv("FRONTEND_REVALIDATE_SECRET", "secret")

    def fake_post(url, **kwargs):
        request = httpx.Request("POST", url)
        return httpx.Response(403, request=request, text="Forbidden")

    monkeypatch.setattr(revalidate.httpx, "post", fake_post)

    with caplog.at_level(logging.WARNING):
        revalidate.trigger_frontend_revalidation(paths=["/about"])

    assert "frontend revalidation failed with status 403" in caplog.text
    assert "Forbidden" in caplog.text


def test_trigger_frontend_revalidation_logs_success(monkeypatch, caplog):
    monkeypatch.setenv("FRONTEND_REVALIDATE_URL", "https://aurorablog.me/api/revalidate")
    monkeypatch.setenv("FRONTEND_REVALIDATE_SECRET", "secret")

    def fake_post(url, **kwargs):
        return httpx.Response(200, request=httpx.Request("POST", url), text='{"revalidated":true}')

    monkeypatch.setattr(revalidate.httpx, "post", fake_post)

    with caplog.at_level(logging.INFO):
        revalidate.trigger_frontend_revalidation(paths=["/", "/blog"], slug="hello-world")

    assert "frontend revalidation succeeded with status 200" in caplog.text
    assert "/blog/hello-world" not in caplog.text
