"""对话消息模型"""

from sqlalchemy import Column, String, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from app.models.base import Base, UUIDMixin, TimestampMixin


class ConversationMessage(Base, UUIDMixin, TimestampMixin):
    """对话消息表 - 记录工作流中的对话历史"""
    __tablename__ = "conversation_messages"

    session_id = Column(
        UUID(as_uuid=True),
        ForeignKey("workflow_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="关联的工作流会话ID"
    )
    stage = Column(
        String(20),
        nullable=False,
        index=True,
        comment="所属阶段: generate/optimize/image"
    )
    role = Column(
        String(20),
        nullable=False,
        comment="消息角色: user/assistant/system"
    )
    content = Column(
        Text,
        nullable=False,
        comment="消息内容"
    )
    extra_data = Column(
        JSONB,
        default=dict,
        comment="额外元数据: token_usage, prompt_id, model等"
    )

    # Relationships
    session = relationship("WorkflowSession", back_populates="messages")
