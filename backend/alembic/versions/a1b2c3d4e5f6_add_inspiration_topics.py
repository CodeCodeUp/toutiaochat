"""add inspiration_topics table

Revision ID: a1b2c3d4e5f6
Revises: 9a97fb68e6f6
Create Date: 2025-12-27 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = '9a97fb68e6f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'inspiration_topics',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('forum_id', sa.String(50), nullable=False, comment='话题ID'),
        sa.Column('forum_name', sa.String(500), nullable=False, comment='话题名称'),
        sa.Column('avatar_url', sa.String(1000), nullable=True, comment='封面图URL'),
        sa.Column('talk_count', sa.Integer(), nullable=False, server_default='0', comment='讨论数'),
        sa.Column('read_count', sa.Integer(), nullable=False, server_default='0', comment='阅读数'),
        sa.Column('usage_count', sa.Integer(), nullable=False, server_default='0', comment='使用次数'),
        sa.Column('raw_data', postgresql.JSONB(astext_type=sa.Text()), nullable=True, server_default='{}', comment='原始数据'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
    )

    # 创建索引（注意：不要重复创建）
    op.create_index('ix_inspiration_topics_forum_id', 'inspiration_topics', ['forum_id'], unique=True)
    op.create_index('ix_inspiration_topics_usage_count', 'inspiration_topics', ['usage_count'])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_inspiration_topics_usage_count', table_name='inspiration_topics')
    op.drop_index('ix_inspiration_topics_forum_id', table_name='inspiration_topics')
    op.drop_table('inspiration_topics')
