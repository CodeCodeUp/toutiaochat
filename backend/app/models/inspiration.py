"""创作灵感 - 话题模型"""

from sqlalchemy import Column, String, Text, Integer, Boolean
from sqlalchemy.dialects.postgresql import JSONB

from app.models.base import Base, UUIDMixin, TimestampMixin


class InspirationTopic(Base, UUIDMixin, TimestampMixin):
    """创作灵感 - 话题"""
    __tablename__ = "inspiration_topics"

    # 话题唯一标识（头条 forum_id，用于去重）
    forum_id = Column(String(50), nullable=False, unique=True, index=True, comment="话题ID")

    # 话题信息
    forum_name = Column(String(500), nullable=False, comment="话题名称")
    avatar_url = Column(String(1000), nullable=True, comment="封面图URL")
    talk_count = Column(Integer, default=0, comment="讨论数")
    read_count = Column(Integer, default=0, comment="阅读数")

    # 使用统计
    usage_count = Column(Integer, default=0, index=True, comment="使用次数")

    # 逻辑删除标记
    is_deleted = Column(Boolean, default=False, index=True, comment="是否已删除")

    # 原始数据（保留完整API响应）
    raw_data = Column(JSONB, default={}, comment="原始数据")
