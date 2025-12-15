from datetime import datetime
from typing import Optional, List
from uuid import UUID
from pydantic import BaseModel, Field

from app.models.article import ArticleStatus, ArticleCategory


class ArticleBase(BaseModel):
    title: str = Field(..., max_length=100, description="文章标题")
    content: str = Field(..., description="文章内容")
    category: ArticleCategory = Field(default=ArticleCategory.OTHER, description="分类")


class ArticleCreate(BaseModel):
    topic: str = Field(..., description="文章话题/素材")
    category: ArticleCategory = Field(default=ArticleCategory.OTHER, description="分类")
    account_id: Optional[UUID] = Field(None, description="关联账号ID")
    auto_humanize: bool = Field(default=False, description="是否自动去AI化")
    generate_images: bool = Field(default=False, description="是否生成图片")


class ArticleUpdate(BaseModel):
    title: Optional[str] = Field(None, max_length=100)
    content: Optional[str] = None
    category: Optional[ArticleCategory] = None
    account_id: Optional[UUID] = None
    cover_url: Optional[str] = None
    images: Optional[List[str]] = None


class ArticleReview(BaseModel):
    approved: bool = Field(..., description="是否通过")
    reject_reason: Optional[str] = Field(None, description="拒绝原因")


class ArticleResponse(ArticleBase):
    id: UUID
    original_topic: Optional[str]
    cover_url: Optional[str]
    images: List[str]
    image_prompts: List[str]
    status: ArticleStatus
    account_id: Optional[UUID]
    ai_model: Optional[str]
    token_usage: int
    published_at: Optional[datetime]
    publish_url: Optional[str]
    reject_reason: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ArticleListResponse(BaseModel):
    items: List[ArticleResponse]
    total: int
    page: int
    page_size: int
