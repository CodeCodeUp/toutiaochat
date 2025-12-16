from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from uuid import UUID
from app.models.prompt import PromptType


class PromptBase(BaseModel):
    """提示词基础Schema"""
    name: str = Field(..., max_length=100, description="提示词名称")
    type: PromptType = Field(..., description="提示词类型")
    content: str = Field(..., description="提示词内容")
    is_active: str = Field(default="true", description="是否启用")
    description: Optional[str] = Field(None, max_length=500, description="提示词描述")


class PromptCreate(PromptBase):
    """创建提示词"""
    pass


class PromptUpdate(BaseModel):
    """更新提示词"""
    name: Optional[str] = Field(None, max_length=100)
    type: Optional[PromptType] = None
    content: Optional[str] = None
    is_active: Optional[str] = None
    description: Optional[str] = Field(None, max_length=500)


class PromptResponse(PromptBase):
    """提示词响应"""
    id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
