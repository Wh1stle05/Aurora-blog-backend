"""add_post_slug_fields

Revision ID: c3d4e5f6a7b8
Revises: b2a1d6d9f7c4
Create Date: 2026-03-23
"""

from alembic import op
import sqlalchemy as sa


revision = "c3d4e5f6a7b8"
down_revision = "b2a1d6d9f7c4"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("posts", sa.Column("slug", sa.String(length=255), nullable=True))
    op.add_column("posts", sa.Column("summary", sa.String(length=300), nullable=True))
    op.add_column("posts", sa.Column("cover_image", sa.String(length=255), nullable=True))
    op.add_column(
        "posts",
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    posts = sa.table(
        "posts",
        sa.column("id", sa.Integer),
        sa.column("title", sa.String),
        sa.column("content", sa.Text),
        sa.column("slug", sa.String),
        sa.column("summary", sa.String),
    )
    connection = op.get_bind()
    rows = connection.execute(sa.select(posts.c.id, posts.c.title, posts.c.content)).fetchall()

    def make_slug(value: str) -> str:
        import re
        import unicodedata

        text = unicodedata.normalize("NFKC", (value or "").strip()).lower()
        text = re.sub(r"[^\w\s-]", "", text)
        text = re.sub(r"[-\s]+", "-", text).strip("-_")
        return text or "post"

    seen = set()
    for row in rows:
        base = make_slug(row.title)
        candidate = base
        suffix = 2
        while candidate in seen:
            candidate = f"{base}-{suffix}"
            suffix += 1
        seen.add(candidate)

        compact = " ".join((row.content or "").split())
        summary = compact[:160].rstrip()
        if len(compact) > 160:
            summary = f"{summary}..."

        connection.execute(
            posts.update().where(posts.c.id == row.id).values(slug=candidate, summary=summary)
        )

    op.alter_column("posts", "slug", existing_type=sa.String(length=255), nullable=False)
    op.create_index("ix_posts_slug", "posts", ["slug"], unique=True)


def downgrade():
    op.drop_index("ix_posts_slug", table_name="posts")
    op.drop_column("posts", "updated_at")
    op.drop_column("posts", "cover_image")
    op.drop_column("posts", "summary")
    op.drop_column("posts", "slug")
