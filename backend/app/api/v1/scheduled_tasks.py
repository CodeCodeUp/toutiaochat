"""定时任务 API 路由"""

from uuid import UUID
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.core.database import get_db
from app.models import ScheduledTask, Task
from app.schemas.scheduled_task import (
    ScheduledTaskCreate,
    ScheduledTaskUpdate,
    ScheduledTaskResponse,
    ScheduledTaskListResponse,
    ScheduledTaskLogResponse,
    ScheduledTaskLogsResponse,
    SchedulerStatusResponse,
)
from app.services.scheduler import scheduler_service

router = APIRouter(prefix="/scheduled-tasks", tags=["定时任务"])


@router.post("", response_model=ScheduledTaskResponse)
async def create_scheduled_task(
    data: ScheduledTaskCreate,
    db: AsyncSession = Depends(get_db),
):
    """创建定时任务"""
    task = ScheduledTask(
        name=data.name,
        type=data.type,
        content_type=data.content_type,
        schedule_mode=data.schedule_mode,
        schedule_config=data.schedule_config,
        active_start_hour=data.active_start_hour,
        active_end_hour=data.active_end_hour,
        topic_mode=data.topic_mode,
        topics=data.topics,
        account_id=data.account_id,
        publish_mode=data.publish_mode,
        publish_batch_size=data.publish_batch_size,
        publish_order=data.publish_order,
        is_active=data.is_active,
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)

    # 添加到调度器
    if task.is_active:
        await scheduler_service.add_task(task.id)

    return task


@router.get("", response_model=ScheduledTaskListResponse)
async def list_scheduled_tasks(
    is_active: Optional[bool] = Query(default=None, description="是否启用"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """获取定时任务列表"""
    query = select(ScheduledTask)

    if is_active is not None:
        query = query.where(ScheduledTask.is_active == is_active)

    query = query.order_by(ScheduledTask.created_at.desc())

    # 总数
    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query) or 0

    # 分页
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    items = result.scalars().all()

    return ScheduledTaskListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{task_id}", response_model=ScheduledTaskResponse)
async def get_scheduled_task(
    task_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """获取定时任务详情"""
    task = await db.get(ScheduledTask, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="定时任务不存在")
    return task


@router.put("/{task_id}", response_model=ScheduledTaskResponse)
async def update_scheduled_task(
    task_id: UUID,
    data: ScheduledTaskUpdate,
    db: AsyncSession = Depends(get_db),
):
    """更新定时任务"""
    task = await db.get(ScheduledTask, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="定时任务不存在")

    update_dict = data.model_dump(exclude_unset=True)
    for key, value in update_dict.items():
        setattr(task, key, value)

    await db.commit()
    await db.refresh(task)

    # 更新调度器
    await scheduler_service.add_task(task.id)

    return task


@router.delete("/{task_id}")
async def delete_scheduled_task(
    task_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """删除定时任务"""
    task = await db.get(ScheduledTask, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="定时任务不存在")

    # 从调度器移除
    await scheduler_service.remove_task(task_id)

    await db.delete(task)
    await db.commit()

    return {"message": "删除成功"}


@router.post("/{task_id}/toggle", response_model=ScheduledTaskResponse)
async def toggle_scheduled_task(
    task_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """启用/禁用定时任务"""
    task = await db.get(ScheduledTask, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="定时任务不存在")

    task.is_active = not task.is_active
    await db.commit()
    await db.refresh(task)

    # 更新调度器
    if task.is_active:
        await scheduler_service.add_task(task.id)
    else:
        await scheduler_service.remove_task(task.id)

    return task


@router.post("/{task_id}/trigger")
async def trigger_scheduled_task(
    task_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """立即执行一次"""
    task = await db.get(ScheduledTask, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="定时任务不存在")

    success = await scheduler_service.trigger_now(task_id)
    if not success:
        raise HTTPException(status_code=500, detail="触发失败")

    return {"message": "已触发执行"}


@router.get("/{task_id}/logs", response_model=ScheduledTaskLogsResponse)
async def get_scheduled_task_logs(
    task_id: UUID,
    limit: int = Query(default=50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    """获取执行日志"""
    task = await db.get(ScheduledTask, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="定时任务不存在")

    query = (
        select(Task)
        .where(Task.scheduled_task_id == task_id)
        .order_by(Task.created_at.desc())
        .limit(limit)
    )
    result = await db.execute(query)
    logs = result.scalars().all()

    # 总数
    count_query = select(func.count()).where(Task.scheduled_task_id == task_id)
    total = await db.scalar(count_query) or 0

    return ScheduledTaskLogsResponse(
        items=[
            ScheduledTaskLogResponse(
                id=log.id,
                type=log.type.value,
                status=log.status.value,
                article_id=log.article_id,
                error_message=log.error_message,
                started_at=log.started_at,
                completed_at=log.completed_at,
                created_at=log.created_at,
            )
            for log in logs
        ],
        total=total,
    )


# ========== 调度器管理 ==========

scheduler_router = APIRouter(prefix="/scheduler", tags=["调度器"])


@scheduler_router.get("/status", response_model=SchedulerStatusResponse)
async def get_scheduler_status():
    """获取调度器状态"""
    return scheduler_service.get_status()


@scheduler_router.post("/pause")
async def pause_scheduler():
    """暂停所有任务"""
    await scheduler_service.pause_all()
    return {"message": "已暂停"}


@scheduler_router.post("/resume")
async def resume_scheduler():
    """恢复所有任务"""
    await scheduler_service.resume_all()
    return {"message": "已恢复"}
