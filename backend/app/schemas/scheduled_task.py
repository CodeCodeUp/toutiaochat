"""定时任务 Schema"""

from datetime import datetime
from uuid import UUID
from typing import Optional, Literal
from pydantic import BaseModel, Field

from app.models.scheduled_task import (
    ScheduledTaskType,
    ScheduleMode,
    PublishMode,
    TopicMode,
)
from app.models.prompt import ContentType


# ========== 调度配置 ==========

class CronScheduleConfig(BaseModel):
    """Cron 调度配置"""
    cron: str = Field(..., description="Cron 表达式，如 '0 9 * * *'")


class IntervalScheduleConfig(BaseModel):
    """固定间隔调度配置"""
    minutes: int = Field(..., ge=1, description="间隔分钟数")


class RandomIntervalScheduleConfig(BaseModel):
    """随机间隔调度配置"""
    min_minutes: int = Field(..., ge=1, description="最小间隔分钟数")
    max_minutes: int = Field(..., ge=1, description="最大间隔分钟数")


# ========== 请求 Schema ==========

class ScheduledTaskCreate(BaseModel):
    """创建定时任务"""
    name: str = Field(..., min_length=1, max_length=100, description="任务名称")
    type: ScheduledTaskType = Field(..., description="任务类型")
    content_type: ContentType = Field(..., description="内容类型")

    # 调度配置
    schedule_mode: ScheduleMode = Field(..., description="调度模式")
    schedule_config: dict = Field(..., description="调度配置")
    active_start_hour: int = Field(default=0, ge=0, le=23, description="活跃开始时间")
    active_end_hour: int = Field(default=24, ge=1, le=24, description="活跃结束时间")

    # 话题配置
    topic_mode: TopicMode = Field(default=TopicMode.RANDOM, description="话题模式")
    topics: list[str] = Field(default_factory=list, description="话题列表")

    # 发布配置
    account_id: Optional[UUID] = Field(default=None, description="发布账号ID")
    publish_mode: PublishMode = Field(default=PublishMode.ONE, description="发布模式")
    publish_batch_size: int = Field(default=1, ge=1, description="批量发布数量")
    publish_order: Literal["oldest", "newest", "random"] = Field(
        default="oldest", description="发布顺序"
    )

    is_active: bool = Field(default=True, description="是否启用")


class ScheduledTaskUpdate(BaseModel):
    """更新定时任务"""
    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    type: Optional[ScheduledTaskType] = None
    content_type: Optional[ContentType] = None

    schedule_mode: Optional[ScheduleMode] = None
    schedule_config: Optional[dict] = None
    active_start_hour: Optional[int] = Field(default=None, ge=0, le=23)
    active_end_hour: Optional[int] = Field(default=None, ge=1, le=24)

    topic_mode: Optional[TopicMode] = None
    topics: Optional[list[str]] = None

    account_id: Optional[UUID] = None
    publish_mode: Optional[PublishMode] = None
    publish_batch_size: Optional[int] = Field(default=None, ge=1)
    publish_order: Optional[Literal["oldest", "newest", "random"]] = None

    is_active: Optional[bool] = None


# ========== 响应 Schema ==========

class ScheduledTaskResponse(BaseModel):
    """定时任务响应"""
    id: UUID
    name: str
    type: ScheduledTaskType
    content_type: ContentType

    schedule_mode: ScheduleMode
    schedule_config: dict
    active_start_hour: int
    active_end_hour: int

    topic_mode: TopicMode
    topics: list[str]
    current_topic_index: int

    account_id: Optional[UUID]
    publish_mode: PublishMode
    publish_batch_size: int
    publish_order: str

    is_active: bool
    last_run_at: Optional[datetime]
    next_run_at: Optional[datetime]
    run_count: int
    last_error: Optional[str]

    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ScheduledTaskListResponse(BaseModel):
    """定时任务列表响应"""
    items: list[ScheduledTaskResponse]
    total: int
    page: int
    page_size: int


class ScheduledTaskLogResponse(BaseModel):
    """执行日志响应"""
    id: UUID
    type: str
    status: str
    article_id: Optional[UUID]
    error_message: Optional[str]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True


class ScheduledTaskLogsResponse(BaseModel):
    """执行日志列表响应"""
    items: list[ScheduledTaskLogResponse]
    total: int


class SchedulerStatusResponse(BaseModel):
    """调度器状态响应"""
    running: bool
    active_tasks: int
    pending_jobs: int
