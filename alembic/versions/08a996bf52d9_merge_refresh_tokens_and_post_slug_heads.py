"""merge refresh_tokens and post_slug heads

Revision ID: 08a996bf52d9
Revises: 2b593a5bcd4e, c3d4e5f6a7b8
Create Date: 2026-09-16 03:08:16.785749

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '08a996bf52d9'
down_revision: Union[str, Sequence[str], None] = ('2b593a5bcd4e', 'c3d4e5f6a7b8')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
