"""创作灵感 Schema"""

from datetime import datetime
from typing import Optional, List
from uuid import UUID
from pydantic import BaseModel, Field


class InspirationTopicResponse(BaseModel):
    """话题响应"""
    id: UUID
    forum_id: str
    forum_name: str
    avatar_url: Optional[str] = None
    talk_count: int = 0
    read_count: int = 0
    usage_count: int = 0
    created_at: datetime

    class Config:
        from_attributes = True


class InspirationTopicListResponse(BaseModel):
    """话题列表响应"""
    items: List[InspirationTopicResponse]
    total: int


class InspirationTopicOption(BaseModel):
    """话题选项（用于下拉选择）"""
    id: UUID
    forum_name: str
    usage_count: int = 0

    class Config:
        from_attributes = True


class SyncTopicsRequest(BaseModel):
    """同步话题请求"""
    account_id: UUID = Field(..., description="账号ID（用于获取Cookie）")


class SyncTopicsResponse(BaseModel):
    """同步话题响应"""
    success: bool = True
    total_fetched: int = Field(..., description="获取总数")
    new_added: int = Field(..., description="新增数量（去重后）")
    message: str = ""


class FetchTopicsRequest(BaseModel):
    """实时获取话题请求"""
    account_id: UUID = Field(..., description="账号ID（用于获取Cookie）")
    offset: int = Field(0, ge=0, description="偏移量")


class FetchTopicsResponse(BaseModel):
    """实时获取话题响应"""
    success: bool = True
    total_fetched: int = Field(..., description="获取总数")
    new_added: int = Field(..., description="新增数量（去重后）")
    offset: int = Field(..., description="下次请求的偏移量")
    message: str = ""


class UseTopicResponse(BaseModel):
    """使用话题响应"""
    forum_name: str
    usage_count: int
