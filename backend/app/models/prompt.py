from sqlalchemy import Column, String, Text, Enum as SQLEnum
import enum
from .base import Base, UUIDMixin, TimestampMixin


class PromptType(str, enum.Enum):
    """提示词类型"""
    GENERATE = "generate"  # 文章生成
    HUMANIZE = "humanize"  # 文章优化/去AI化
    IMAGE = "image"  # 图片生成


class Prompt(Base, UUIDMixin, TimestampMixin):
    """提示词模型 - 管理AI生成的各类提示词"""

    __tablename__ = "prompts"

    name = Column(String(100), nullable=False, comment="提示词名称")
    type = Column(SQLEnum(PromptType), nullable=False, index=True, comment="提示词类型")
    content = Column(Text, nullable=False, comment="提示词内容")
    is_active = Column(String(10), default="true", comment="是否启用(true/false)")
    description = Column(String(500), comment="提示词描述")
