import asyncio
import io
import importlib
from types import SimpleNamespace


def test_save_file_uses_r2_when_env_configured(monkeypatch):
    monkeypatch.setenv("R2_ENDPOINT", "https://example.r2.cloudflarestorage.com")
    monkeypatch.setenv("R2_ACCESS_KEY_ID", "key")
    monkeypatch.setenv("R2_SECRET_ACCESS_KEY", "secret")
    monkeypatch.setenv("R2_BUCKET", "bucket")
    monkeypatch.setenv("R2_PUBLIC_BASE_URL", "https://cdn.example.com")

    called = {"put": False}

    class FakeClient:
        def put_object(self, **kwargs):
            called["put"] = True

    def fake_client(*args, **kwargs):
        return FakeClient()

    import app.services.storage as storage
    importlib.reload(storage)
    monkeypatch.setattr(storage, "_build_r2_client", fake_client, raising=False)

    file = SimpleNamespace(
        filename="a.png",
        content_type="image/png",
        file=io.BytesIO(b"x"),
    )

    async def fake_read():
        return b"x"

    async def fake_seek(_):
        return None

    file.read = fake_read
    file.seek = fake_seek

    url = asyncio.run(storage.save_file(file, subfolder="avatars"))
    assert called["put"] is True
    assert url.startswith("https://cdn.example.com/avatars/")
