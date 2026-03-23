import re
import secrets
import unicodedata

from sqlalchemy.orm import Session

from app.models import Post


def slugify(value: str) -> str:
    text = unicodedata.normalize("NFKC", (value or "").strip()).lower()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[-\s]+", "-", text).strip("-_")
    if text:
        return text
    return f"post-{secrets.token_hex(4)}"


def generate_unique_slug(
    db: Session,
    *,
    title: str,
    preferred_slug: str | None = None,
    current_post_id: int | None = None,
) -> str:
    base_slug = slugify(preferred_slug or title)
    candidate = base_slug
    suffix = 2

    while True:
        query = db.query(Post).filter(Post.slug == candidate)
        if current_post_id is not None:
            query = query.filter(Post.id != current_post_id)
        if query.first() is None:
            return candidate
        candidate = f"{base_slug}-{suffix}"
        suffix += 1


def build_summary(content: str, limit: int = 160) -> str:
    compact = re.sub(r"\s+", " ", (content or "").strip())
    if len(compact) <= limit:
        return compact
    return f"{compact[:limit].rstrip()}..."
