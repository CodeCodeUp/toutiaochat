import enum
from sqlalchemy import Column, String, Text
from app.models.base import Base, UUIDMixin, TimestampMixin


class AIConfigType(str, enum.Enum):
    ARTICLE_GENERATE = "article_generate"  # 文章生成
    ARTICLE_HUMANIZE = "article_humanize"  # 文章优化
    IMAGE_GENERATE = "image_generate"      # 生图


class AIConfig(Base, UUIDMixin, TimestampMixin):
    """AI 配置表"""
    __tablename__ = "ai_configs"

    type = Column(String(50), unique=True, nullable=False, comment="配置类型")
    api_key = Column(Text, nullable=False, default="", comment="API Key")
    api_url = Column(String(500), nullable=False, default="", comment="API URL")
    model = Column(String(100), nullable=False, default="", comment="模型名称")
