from sqlalchemy import Column, String, Boolean, Enum as SQLEnum
from .base import Base, UUIDMixin, TimestampMixin
from .prompt import ContentType


class WorkflowConfig(Base, UUIDMixin, TimestampMixin):
    """工作流配置表 - 管理全自动模式的各项开关"""

    __tablename__ = "workflow_configs"

    content_type = Column(
        SQLEnum(ContentType),
        unique=True,
        nullable=False,
        index=True,
        comment="内容类型: article-文章, weitoutiao-微头条"
    )

    # 工作流开关配置
    enable_custom_topic = Column(
        Boolean,
        default=False,
        nullable=False,
        comment="是否启用自定义话题"
    )
    enable_optimize = Column(
        Boolean,
        default=True,
        nullable=False,
        comment="是否启用内容优化（去AI化）"
    )
    enable_image_gen = Column(
        Boolean,
        default=True,
        nullable=False,
        comment="是否启用AI生图"
    )
    enable_auto_publish = Column(
        Boolean,
        default=False,
        nullable=False,
        comment="是否启用自动发布"
    )

    # 可选：自定义话题内容
    custom_topic = Column(
        String(500),
        default="",
        nullable=False,
        comment="自定义话题内容（当 enable_custom_topic=True 时使用）"
    )

    def __repr__(self):
        return f"<WorkflowConfig {self.content_type.value}>"
