"""post_images_object_key

Revision ID: b2a1d6d9f7c4
Revises: 7f9134265b3f
Create Date: 2026-03-18
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'b2a1d6d9f7c4'
down_revision = '7f9134265b3f'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('post_images', sa.Column('object_key', sa.String(length=255), nullable=False, server_default=''))
    op.drop_column('post_images', 'data')


def downgrade():
    op.add_column('post_images', sa.Column('data', sa.Text(), nullable=False, server_default=''))
    op.drop_column('post_images', 'object_key')
