from datetime import datetime
from typing import Optional, List
from uuid import UUID
from pydantic import BaseModel

from app.models.task import TaskType, TaskStatus


class TaskResponse(BaseModel):
    id: UUID
    type: TaskType
    status: TaskStatus
    article_id: Optional[UUID]
    account_id: Optional[UUID]
    priority: int
    retry_count: int
    error_message: Optional[str]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True


class TaskListResponse(BaseModel):
    items: List[TaskResponse]
    total: int
    page: int
    page_size: int
