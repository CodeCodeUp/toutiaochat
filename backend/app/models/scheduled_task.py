"""定时任务模型"""

from sqlalchemy import Column, String, Text, Enum as SQLEnum, Integer, DateTime, Boolean, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
import enum

from app.models.base import Base, UUIDMixin, TimestampMixin
from app.models.prompt import ContentType


class ScheduleMode(str, enum.Enum):
    """调度模式"""
    CRON = "cron"                        # 标准 cron 表达式
    INTERVAL = "interval"                # 固定间隔
    RANDOM_INTERVAL = "random_interval"  # 随机间隔


class ScheduledTaskType(str, enum.Enum):
    """定时任务类型"""
    GENERATE = "generate"                        # 定时生成文章
    PUBLISH = "publish"                          # 定时发布已完成文章
    GENERATE_AND_PUBLISH = "generate_and_publish"  # 生成并发布


class PublishMode(str, enum.Enum):
    """发布模式"""
    ALL = "all"        # 发布所有草稿
    ONE = "one"        # 每次发布一篇
    BATCH = "batch"    # 批量发布指定数量


class TopicMode(str, enum.Enum):
    """话题模式"""
    RANDOM = "random"  # AI 自选
    FIXED = "fixed"    # 固定话题
    LIST = "list"      # 列表轮流


class ScheduledTask(Base, UUIDMixin, TimestampMixin):
    """定时任务表"""

    __tablename__ = "scheduled_tasks"

    # 基本信息
    name = Column(String(100), nullable=False, comment="任务名称")
    type = Column(
        SQLEnum(ScheduledTaskType),
        nullable=False,
        comment="任务类型"
    )
    content_type = Column(
        SQLEnum(ContentType),
        nullable=False,
        comment="内容类型"
    )

    # 调度配置
    schedule_mode = Column(
        SQLEnum(ScheduleMode),
        nullable=False,
        comment="调度模式"
    )
    schedule_config = Column(
        JSONB,
        nullable=False,
        default=dict,
        comment="调度配置: {cron} | {minutes} | {min_minutes, max_minutes}"
    )
    active_start_hour = Column(
        Integer,
        default=0,
        nullable=False,
        comment="活跃开始时间(小时) 0-23"
    )
    active_end_hour = Column(
        Integer,
        default=24,
        nullable=False,
        comment="活跃结束时间(小时) 1-24"
    )

    # 话题配置
    topic_mode = Column(
        SQLEnum(TopicMode),
        default=TopicMode.RANDOM,
        nullable=False,
        comment="话题模式"
    )
    topics = Column(
        JSONB,
        default=list,
        nullable=False,
        comment="话题列表"
    )
    current_topic_index = Column(
        Integer,
        default=0,
        nullable=False,
        comment="当前话题索引"
    )

    # 发布配置
    account_id = Column(
        UUID(as_uuid=True),
        ForeignKey("accounts.id"),
        nullable=True,
        comment="发布账号"
    )
    publish_mode = Column(
        SQLEnum(PublishMode),
        default=PublishMode.ONE,
        nullable=False,
        comment="发布模式"
    )
    publish_batch_size = Column(
        Integer,
        default=1,
        nullable=False,
        comment="批量发布数量"
    )
    publish_order = Column(
        String(20),
        default="oldest",
        nullable=False,
        comment="发布顺序: oldest/newest/random"
    )

    # 状态
    is_active = Column(
        Boolean,
        default=True,
        nullable=False,
        comment="是否启用"
    )
    last_run_at = Column(
        DateTime,
        nullable=True,
        comment="上次执行时间"
    )
    next_run_at = Column(
        DateTime,
        nullable=True,
        comment="下次执行时间"
    )
    run_count = Column(
        Integer,
        default=0,
        nullable=False,
        comment="执行次数"
    )
    last_error = Column(
        Text,
        nullable=True,
        comment="最后一次错误信息"
    )

    # 关联
    account = relationship("Account", backref="scheduled_tasks")

    def __repr__(self):
        return f"<ScheduledTask {self.name} ({self.type.value})>"
