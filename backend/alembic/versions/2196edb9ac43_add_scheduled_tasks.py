"""add_scheduled_tasks

Revision ID: 2196edb9ac43
Revises: 5ebf51b6ca35
Create Date: 2025-12-24 09:11:38.372016

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '2196edb9ac43'
down_revision: Union[str, Sequence[str], None] = '5ebf51b6ca35'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # 先创建新的枚举类型
    scheduledtasktype = postgresql.ENUM('GENERATE', 'PUBLISH', 'GENERATE_AND_PUBLISH', name='scheduledtasktype', create_type=False)
    schedulemode = postgresql.ENUM('CRON', 'INTERVAL', 'RANDOM_INTERVAL', name='schedulemode', create_type=False)
    topicmode = postgresql.ENUM('RANDOM', 'FIXED', 'LIST', name='topicmode', create_type=False)
    publishmode = postgresql.ENUM('ALL', 'ONE', 'BATCH', name='publishmode', create_type=False)

    # 创建枚举类型（如果不存在）
    scheduledtasktype.create(op.get_bind(), checkfirst=True)
    schedulemode.create(op.get_bind(), checkfirst=True)
    topicmode.create(op.get_bind(), checkfirst=True)
    publishmode.create(op.get_bind(), checkfirst=True)

    # 使用已存在的 contenttype 枚举
    contenttype = postgresql.ENUM('ARTICLE', 'WEITOUTIAO', name='contenttype', create_type=False)

    op.create_table('scheduled_tasks',
    sa.Column('name', sa.String(length=100), nullable=False, comment='任务名称'),
    sa.Column('type', scheduledtasktype, nullable=False, comment='任务类型'),
    sa.Column('content_type', contenttype, nullable=False, comment='内容类型'),
    sa.Column('schedule_mode', schedulemode, nullable=False, comment='调度模式'),
    sa.Column('schedule_config', postgresql.JSONB(astext_type=sa.Text()), nullable=False, comment='调度配置: {cron} | {minutes} | {min_minutes, max_minutes}'),
    sa.Column('active_start_hour', sa.Integer(), nullable=False, comment='活跃开始时间(小时) 0-23'),
    sa.Column('active_end_hour', sa.Integer(), nullable=False, comment='活跃结束时间(小时) 1-24'),
    sa.Column('topic_mode', topicmode, nullable=False, comment='话题模式'),
    sa.Column('topics', postgresql.JSONB(astext_type=sa.Text()), nullable=False, comment='话题列表'),
    sa.Column('current_topic_index', sa.Integer(), nullable=False, comment='当前话题索引'),
    sa.Column('account_id', sa.UUID(), nullable=True, comment='发布账号'),
    sa.Column('publish_mode', publishmode, nullable=False, comment='发布模式'),
    sa.Column('publish_batch_size', sa.Integer(), nullable=False, comment='批量发布数量'),
    sa.Column('publish_order', sa.String(length=20), nullable=False, comment='发布顺序: oldest/newest/random'),
    sa.Column('is_active', sa.Boolean(), nullable=False, comment='是否启用'),
    sa.Column('last_run_at', sa.DateTime(), nullable=True, comment='上次执行时间'),
    sa.Column('next_run_at', sa.DateTime(), nullable=True, comment='下次执行时间'),
    sa.Column('run_count', sa.Integer(), nullable=False, comment='执行次数'),
    sa.Column('last_error', sa.Text(), nullable=True, comment='最后一次错误信息'),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['account_id'], ['accounts.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.add_column('tasks', sa.Column('scheduled_task_id', sa.UUID(), nullable=True, comment='关联定时任务'))
    op.create_foreign_key('fk_tasks_scheduled_task_id', 'tasks', 'scheduled_tasks', ['scheduled_task_id'], ['id'])
    # ### end Alembic commands ###


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint('fk_tasks_scheduled_task_id', 'tasks', type_='foreignkey')
    op.drop_column('tasks', 'scheduled_task_id')
    op.drop_table('scheduled_tasks')
    # 删除新创建的枚举类型
    op.execute('DROP TYPE IF EXISTS scheduledtasktype')
    op.execute('DROP TYPE IF EXISTS schedulemode')
    op.execute('DROP TYPE IF EXISTS topicmode')
    op.execute('DROP TYPE IF EXISTS publishmode')
