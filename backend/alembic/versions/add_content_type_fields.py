"""add content_type to prompts and workflow_sessions

Revision ID: add_content_type_001
Revises: 518df3a10cd5
Create Date: 2025-12-22

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'add_content_type_001'
down_revision: Union[str, Sequence[str], None] = '518df3a10cd5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # 创建 contenttype 枚举类型
    content_type_enum = sa.Enum('ARTICLE', 'WEITOUTIAO', name='contenttype')
    content_type_enum.create(op.get_bind(), checkfirst=True)

    # 添加 content_type 字段到 prompts 表
    op.add_column('prompts', sa.Column(
        'content_type',
        sa.Enum('ARTICLE', 'WEITOUTIAO', name='contenttype'),
        nullable=True,
        comment='内容类型: article-文章, weitoutiao-微头条'
    ))

    # 设置默认值为 ARTICLE
    op.execute("UPDATE prompts SET content_type = 'ARTICLE' WHERE content_type IS NULL")

    # 设置为非空
    op.alter_column('prompts', 'content_type', nullable=False)

    # 创建索引
    op.create_index(op.f('ix_prompts_content_type'), 'prompts', ['content_type'], unique=False)

    # 添加 content_type 字段到 workflow_sessions 表
    op.add_column('workflow_sessions', sa.Column(
        'content_type',
        sa.Enum('ARTICLE', 'WEITOUTIAO', name='contenttype'),
        nullable=True,
        comment='内容类型: article-文章, weitoutiao-微头条'
    ))

    # 设置默认值为 ARTICLE
    op.execute("UPDATE workflow_sessions SET content_type = 'ARTICLE' WHERE content_type IS NULL")

    # 设置为非空
    op.alter_column('workflow_sessions', 'content_type', nullable=False)


def downgrade() -> None:
    """Downgrade schema."""
    # 删除 workflow_sessions 表的 content_type 字段
    op.drop_column('workflow_sessions', 'content_type')

    # 删除 prompts 表的索引和字段
    op.drop_index(op.f('ix_prompts_content_type'), table_name='prompts')
    op.drop_column('prompts', 'content_type')

    # 删除枚举类型
    content_type_enum = sa.Enum('ARTICLE', 'WEITOUTIAO', name='contenttype')
    content_type_enum.drop(op.get_bind(), checkfirst=True)
