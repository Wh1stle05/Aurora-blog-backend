import logging
import os

import httpx

logger = logging.getLogger(__name__)


def _get_revalidate_url() -> str:
    explicit = os.getenv("FRONTEND_REVALIDATE_URL", "").strip()
    if explicit:
        return explicit

    site_url = os.getenv("FRONTEND_SITE_URL", "").strip().rstrip("/")
    if site_url:
        return f"{site_url}/api/revalidate"

    return ""


def trigger_frontend_revalidation(*, paths: list[str], slug: str | None = None) -> None:
    secret = os.getenv("FRONTEND_REVALIDATE_SECRET", "").strip()
    url = _get_revalidate_url()
    if not secret or not url:
        return

    payload = {"secret": secret, "paths": paths}
    if slug:
        payload["slug"] = slug

    try:
        response = httpx.post(
            url,
            json=payload,
            timeout=5,
            follow_redirects=True,
            headers={"User-Agent": "aurora-backend-revalidate/1.0"},
        )
        response.raise_for_status()
        logger.info(
            "frontend revalidation succeeded with status %s for paths=%s slug=%s",
            response.status_code,
            paths,
            slug,
        )
    except httpx.HTTPStatusError as exc:
        body = exc.response.text[:500] if exc.response is not None else ""
        logger.warning(
            "frontend revalidation failed with status %s: %s",
            exc.response.status_code if exc.response is not None else "unknown",
            body,
        )
    except Exception as exc:
        logger.warning("frontend revalidation failed: %s", exc)
