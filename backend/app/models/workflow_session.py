"""工作流会话模型"""

from sqlalchemy import Column, String, ForeignKey, Enum as SQLEnum, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
import enum

from app.models.base import Base, UUIDMixin, TimestampMixin


class WorkflowMode(str, enum.Enum):
    """工作流模式"""
    AUTO = "auto"       # 全自动模式
    MANUAL = "manual"   # 半自动模式


class WorkflowStage(str, enum.Enum):
    """工作流阶段"""
    GENERATE = "generate"     # 文章生成阶段
    OPTIMIZE = "optimize"     # 优化阶段
    IMAGE = "image"           # 生图阶段
    EDIT = "edit"             # 编辑阶段
    COMPLETED = "completed"   # 完成


class WorkflowSession(Base, UUIDMixin, TimestampMixin):
    """工作流会话表"""
    __tablename__ = "workflow_sessions"

    article_id = Column(
        UUID(as_uuid=True),
        ForeignKey("articles.id", ondelete="CASCADE"),
        nullable=False,
        comment="关联文章ID"
    )
    mode = Column(
        SQLEnum(WorkflowMode),
        nullable=False,
        comment="工作流模式: auto-全自动, manual-半自动"
    )
    current_stage = Column(
        SQLEnum(WorkflowStage),
        default=WorkflowStage.GENERATE,
        nullable=False,
        comment="当前阶段"
    )
    stage_data = Column(
        JSONB,
        default=dict,
        comment="各阶段数据快照"
    )
    error_message = Column(
        Text,
        nullable=True,
        comment="错误信息"
    )
    progress = Column(
        String(10),
        default="0",
        comment="进度百分比"
    )

    # Relationships
    article = relationship("Article", back_populates="workflow_sessions")
    messages = relationship(
        "ConversationMessage",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="ConversationMessage.created_at"
    )
