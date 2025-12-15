from sqlalchemy import Column, String, Text, Enum, Integer, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import enum

from app.models.base import Base, UUIDMixin, TimestampMixin


class TaskType(str, enum.Enum):
    GENERATE = "generate"      # 生成文章
    HUMANIZE = "humanize"      # 去AI化
    IMAGE_GEN = "image_gen"    # 生成图片
    PUBLISH = "publish"        # 发布文章


class TaskStatus(str, enum.Enum):
    PENDING = "pending"        # 等待中
    RUNNING = "running"        # 执行中
    COMPLETED = "completed"    # 已完成
    FAILED = "failed"          # 失败
    CANCELLED = "cancelled"    # 已取消


class Task(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "tasks"

    type = Column(Enum(TaskType), nullable=False, comment="任务类型")
    status = Column(Enum(TaskStatus), default=TaskStatus.PENDING, comment="任务状态")

    article_id = Column(UUID(as_uuid=True), ForeignKey("articles.id"), nullable=True, comment="关联文章")
    account_id = Column(UUID(as_uuid=True), ForeignKey("accounts.id"), nullable=True, comment="关联账号")

    priority = Column(Integer, default=0, comment="优先级")
    retry_count = Column(Integer, default=0, comment="重试次数")
    error_message = Column(Text, nullable=True, comment="错误信息")

    started_at = Column(DateTime, nullable=True, comment="开始时间")
    completed_at = Column(DateTime, nullable=True, comment="完成时间")

    # Relationships
    article = relationship("Article", back_populates="tasks")
    account = relationship("Account", back_populates="tasks")
