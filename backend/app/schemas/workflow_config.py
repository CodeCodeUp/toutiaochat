from pydantic import BaseModel
from typing import Optional
from uuid import UUID
from datetime import datetime
from app.models.prompt import ContentType


class WorkflowConfigBase(BaseModel):
    """工作流配置基础字段"""
    enable_custom_topic: bool = False
    enable_optimize: bool = True
    enable_image_gen: bool = True
    enable_auto_publish: bool = False
    custom_topic: str = ""


class WorkflowConfigCreate(WorkflowConfigBase):
    """创建工作流配置"""
    content_type: ContentType


class WorkflowConfigUpdate(BaseModel):
    """更新工作流配置"""
    enable_custom_topic: Optional[bool] = None
    enable_optimize: Optional[bool] = None
    enable_image_gen: Optional[bool] = None
    enable_auto_publish: Optional[bool] = None
    custom_topic: Optional[str] = None


class WorkflowConfigResponse(WorkflowConfigBase):
    """工作流配置响应"""
    id: UUID
    content_type: ContentType
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class WorkflowConfigListResponse(BaseModel):
    """工作流配置列表响应"""
    configs: dict[str, WorkflowConfigResponse | None]
