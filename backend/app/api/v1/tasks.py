from typing import Optional
from uuid import UUID
from datetime import datetime
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.core.database import get_db
from app.core.exceptions import NotFoundException
from app.models import Task, TaskStatus, TaskType
from app.schemas.task import TaskResponse, TaskListResponse

router = APIRouter(prefix="/tasks", tags=["任务管理"])


@router.get("", response_model=TaskListResponse, summary="任务列表")
async def list_tasks(
    status: Optional[TaskStatus] = Query(None, description="状态筛选"),
    task_type: Optional[TaskType] = Query(None, description="类型筛选"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """获取任务列表"""
    query = select(Task)

    if status:
        query = query.where(Task.status == status)
    if task_type:
        query = query.where(Task.type == task_type)

    query = query.order_by(Task.created_at.desc())

    # 总数
    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query)

    # 分页
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    items = result.scalars().all()

    return TaskListResponse(
        items=items,
        total=total or 0,
        page=page,
        page_size=page_size,
    )


@router.get("/{task_id}", response_model=TaskResponse, summary="任务详情")
async def get_task(
    task_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """获取任务详情"""
    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()

    if not task:
        raise NotFoundException("Task")

    return task


@router.post("/{task_id}/retry", response_model=TaskResponse, summary="重试任务")
async def retry_task(
    task_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """重试失败的任务"""
    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()

    if not task:
        raise NotFoundException("Task")

    if task.status != TaskStatus.FAILED:
        raise ValueError("只能重试失败的任务")

    task.status = TaskStatus.PENDING
    task.retry_count += 1
    task.error_message = None
    task.started_at = None
    task.completed_at = None

    await db.commit()
    await db.refresh(task)

    return task


@router.delete("/{task_id}", summary="取消任务")
async def cancel_task(
    task_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """取消等待中的任务"""
    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()

    if not task:
        raise NotFoundException("Task")

    if task.status not in [TaskStatus.PENDING, TaskStatus.RUNNING]:
        raise ValueError("只能取消等待中或运行中的任务")

    task.status = TaskStatus.CANCELLED
    task.completed_at = datetime.utcnow()

    await db.commit()

    return {"message": "任务已取消"}
