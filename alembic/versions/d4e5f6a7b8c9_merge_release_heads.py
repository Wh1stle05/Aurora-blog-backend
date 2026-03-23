"""merge release heads

Revision ID: d4e5f6a7b8c9
Revises: 2b593a5bcd4e, c3d4e5f6a7b8
Create Date: 2026-03-23
"""

from typing import Sequence, Union


revision: str = "d4e5f6a7b8c9"
down_revision: Union[str, Sequence[str], None] = ("2b593a5bcd4e", "c3d4e5f6a7b8")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
