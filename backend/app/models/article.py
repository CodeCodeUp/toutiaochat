from sqlalchemy import Column, String, Text, Enum, Integer, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
import enum

from app.models.base import Base, UUIDMixin, TimestampMixin


class ArticleStatus(str, enum.Enum):
    DRAFT = "draft"                    # 草稿(可编辑)
    PUBLISHING = "publishing"          # 发布中
    PUBLISHED = "published"            # 已发布
    FAILED = "failed"                  # 发布失败


class ArticleCategory(str, enum.Enum):
    POLITICS = "政治"
    ECONOMY = "经济"
    SOCIETY = "社会"
    TECH = "科技"
    SPORTS = "体育"
    ENTERTAINMENT = "娱乐"
    INTERNATIONAL = "国际"
    MILITARY = "军事"
    CULTURE = "文化"
    LIFE = "生活"
    EDUCATION = "教育"
    HEALTH = "健康"
    DIGITAL = "数码3C"
    HOT = "时事热点"
    OTHER = "其他"


class Article(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "articles"

    title = Column(String(100), nullable=False, comment="文章标题")
    content = Column(Text, nullable=False, comment="文章内容")
    original_topic = Column(Text, nullable=True, comment="原始话题/素材")
    cover_url = Column(String(500), nullable=True, comment="封面图URL")
    images = Column(JSONB, default=list, comment="文章图片列表")
    image_prompts = Column(JSONB, default=list, comment="图片生成提示词")

    status = Column(Enum(ArticleStatus), default=ArticleStatus.DRAFT, comment="状态")
    category = Column(Enum(ArticleCategory), default=ArticleCategory.OTHER, comment="分类")

    account_id = Column(UUID(as_uuid=True), ForeignKey("accounts.id"), nullable=True, comment="关联账号")

    ai_model = Column(String(50), nullable=True, comment="使用的AI模型")
    token_usage = Column(Integer, default=0, comment="Token消耗")

    published_at = Column(DateTime, nullable=True, comment="发布时间")
    publish_url = Column(String(500), nullable=True, comment="发布后的文章URL")
    error_message = Column(Text, nullable=True, comment="发布失败原因")

    # Relationships
    account = relationship("Account", back_populates="articles")
    tasks = relationship("Task", back_populates="article")
    workflow_sessions = relationship(
        "WorkflowSession",
        back_populates="article",
        cascade="all, delete-orphan"
    )
