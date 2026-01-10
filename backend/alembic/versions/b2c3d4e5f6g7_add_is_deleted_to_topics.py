"""add is_deleted to inspiration_topics

Revision ID: b2c3d4e5f6g7
Revises: a1b2c3d4e5f6
Create Date: 2025-12-27 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'b2c3d4e5f6g7'
down_revision: Union[str, Sequence[str], None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add is_deleted column to inspiration_topics table."""
    op.add_column(
        'inspiration_topics',
        sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default='false', comment='是否已删除')
    )
    op.create_index('ix_inspiration_topics_is_deleted', 'inspiration_topics', ['is_deleted'])


def downgrade() -> None:
    """Remove is_deleted column from inspiration_topics table."""
    op.drop_index('ix_inspiration_topics_is_deleted', table_name='inspiration_topics')
    op.drop_column('inspiration_topics', 'is_deleted')
