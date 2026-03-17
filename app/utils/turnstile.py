import os
import httpx

TURNSTILE_SECRET_KEY = os.getenv("TURNSTILE_SECRET_KEY", "")


def verify_turnstile(token: str, remoteip: str | None = None) -> bool:
    if not TURNSTILE_SECRET_KEY:
        return False
    data = {
        "secret": TURNSTILE_SECRET_KEY,
        "response": token,
    }
    if remoteip:
        data["remoteip"] = remoteip
    with httpx.Client(timeout=5) as client:
        resp = client.post(
            "https://challenges.cloudflare.com/turnstile/v0/siteverify",
            data=data,
        )
    payload = resp.json()
    return bool(payload.get("success"))
