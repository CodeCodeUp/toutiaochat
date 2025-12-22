from datetime import datetime
from typing import Optional, List, Any
from uuid import UUID
from pydantic import BaseModel, Field

from app.models.article import ArticleStatus
from app.models.prompt import ContentType


class ArticleBase(BaseModel):
    title: str = Field(..., max_length=100, description="文章标题")
    content: str = Field(..., description="文章内容")


class ArticleCreate(BaseModel):
    title: str = Field(default="", max_length=100, description="文章标题")
    content: str = Field(default="", description="文章内容")
    content_type: ContentType = Field(default=ContentType.ARTICLE, description="内容类型")
    account_id: Optional[UUID] = Field(None, description="关联账号ID")


class ArticleUpdate(BaseModel):
    title: Optional[str] = Field(None, max_length=100)
    content: Optional[str] = None
    account_id: Optional[UUID] = None
    cover_url: Optional[str] = None
    images: Optional[List[Any]] = None
    image_prompts: Optional[List[Any]] = None


class ArticleResponse(ArticleBase):
    id: UUID
    content_type: ContentType
    cover_url: Optional[str]
    images: List[Any]
    image_prompts: List[Any]
    status: ArticleStatus
    account_id: Optional[UUID]
    ai_model: Optional[str]
    token_usage: int
    published_at: Optional[datetime]
    publish_url: Optional[str]
    error_message: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ArticleListResponse(BaseModel):
    items: List[ArticleResponse]
    total: int
    page: int
    page_size: int
