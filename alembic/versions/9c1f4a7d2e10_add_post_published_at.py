"""add posts.published_at

展示用的发布时间（可手动修改），为空时使用 created_at（真实上传时间）。

Revision ID: 9c1f4a7d2e10
Revises: 08a996bf52d9
Create Date: 2026-09-18
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "9c1f4a7d2e10"
down_revision: Union[str, Sequence[str], None] = "08a996bf52d9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "posts",
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_posts_published_at", "posts", ["published_at"])


def downgrade() -> None:
    op.drop_index("ix_posts_published_at", table_name="posts")
    op.drop_column("posts", "published_at")
