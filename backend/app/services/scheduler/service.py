"""调度服务 - 基于 APScheduler"""

import asyncio
import random
from datetime import datetime, timedelta, time
from uuid import UUID
from typing import Optional
import structlog
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.date import DateTrigger
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.models import ScheduledTask, ScheduleMode
from app.services.scheduler.executor import task_executor

logger = structlog.get_logger()


class SchedulerService:
    """调度服务"""

    def __init__(self):
        self.scheduler: Optional[AsyncIOScheduler] = None
        self.running = False
        self.semaphore = asyncio.Semaphore(3)  # 最大并发数
        self._running_tasks: dict[str, asyncio.Task] = {}

    async def start(self):
        """启动调度器"""
        if self.running:
            logger.warning("scheduler_already_running")
            return

        self.scheduler = AsyncIOScheduler(
            timezone="Asia/Shanghai",
            job_defaults={
                "coalesce": True,  # 合并错过的任务
                "max_instances": 1,  # 每个任务最多一个实例
                "misfire_grace_time": 60 * 5,  # 5分钟内的错过任务仍执行
            }
        )

        # 从数据库加载所有活跃任务
        await self._load_tasks()

        self.scheduler.start()
        self.running = True

        logger.info("scheduler_started", job_count=len(self.scheduler.get_jobs()))

    async def stop(self):
        """停止调度器"""
        if not self.running:
            return

        if self.scheduler:
            self.scheduler.shutdown(wait=False)
            self.scheduler = None

        self.running = False
        logger.info("scheduler_stopped")

    async def _load_tasks(self):
        """从数据库加载所有活跃任务"""
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(ScheduledTask).where(ScheduledTask.is_active == True)
            )
            tasks = result.scalars().all()

            for task in tasks:
                await self._add_job(task)

            logger.info("scheduler_tasks_loaded", count=len(tasks))

    async def add_task(self, task_id: UUID):
        """添加或更新定时任务"""
        if not self.scheduler:
            return

        async with AsyncSessionLocal() as db:
            task = await db.get(ScheduledTask, task_id)
            if not task:
                return

            # 先移除旧的 job
            job_id = f"scheduled_task_{task_id}"
            if self.scheduler.get_job(job_id):
                self.scheduler.remove_job(job_id)

            if task.is_active:
                await self._add_job(task)

    async def remove_task(self, task_id: UUID):
        """移除定时任务"""
        if not self.scheduler:
            return

        job_id = f"scheduled_task_{task_id}"
        if self.scheduler.get_job(job_id):
            self.scheduler.remove_job(job_id)
            logger.info("scheduler_job_removed", task_id=str(task_id))

    async def trigger_now(self, task_id: UUID) -> bool:
        """立即执行一次"""
        async with AsyncSessionLocal() as db:
            task = await db.get(ScheduledTask, task_id)
            if not task:
                return False

            # 在后台执行
            asyncio.create_task(self._execute_with_limit(task_id))
            return True

    async def _add_job(self, task: ScheduledTask):
        """添加 APScheduler Job"""
        if not self.scheduler:
            return

        job_id = f"scheduled_task_{task.id}"

        # 计算下次执行时间
        next_run = await self._calculate_next_run(task)

        if task.schedule_mode == ScheduleMode.CRON:
            # Cron 模式
            cron_expr = task.schedule_config.get("cron", "0 9 * * *")
            trigger = CronTrigger.from_crontab(cron_expr)
        elif task.schedule_mode == ScheduleMode.INTERVAL:
            # 固定间隔模式
            minutes = task.schedule_config.get("minutes", 60)
            trigger = IntervalTrigger(minutes=minutes)
        else:
            # 随机间隔模式 - 使用 DateTrigger，执行后重新调度
            trigger = DateTrigger(run_date=next_run)

        self.scheduler.add_job(
            self._job_wrapper,
            trigger=trigger,
            id=job_id,
            args=[task.id],
            replace_existing=True,
        )

        # 更新数据库中的下次执行时间
        async with AsyncSessionLocal() as db:
            db_task = await db.get(ScheduledTask, task.id)
            if db_task:
                db_task.next_run_at = next_run
                await db.commit()

        logger.info(
            "scheduler_job_added",
            task_id=str(task.id),
            task_name=task.name,
            next_run=next_run.isoformat() if next_run else None,
        )

    async def _job_wrapper(self, task_id: UUID):
        """Job 包装器"""
        await self._execute_with_limit(task_id)

        # 如果是随机间隔模式，重新调度
        async with AsyncSessionLocal() as db:
            task = await db.get(ScheduledTask, task_id)
            if task and task.is_active and task.schedule_mode == ScheduleMode.RANDOM_INTERVAL:
                await self._reschedule_random_interval(task)

    async def _execute_with_limit(self, task_id: UUID):
        """带并发限制的执行"""
        async with self.semaphore:
            async with AsyncSessionLocal() as db:
                task = await db.get(ScheduledTask, task_id)
                if not task:
                    return

                await task_executor.execute(db, task)

    async def _reschedule_random_interval(self, task: ScheduledTask):
        """重新调度随机间隔任务"""
        if not self.scheduler:
            return

        job_id = f"scheduled_task_{task.id}"
        next_run = await self._calculate_next_run(task)

        # 移除旧的 job
        if self.scheduler.get_job(job_id):
            self.scheduler.remove_job(job_id)

        # 添加新的 job
        self.scheduler.add_job(
            self._job_wrapper,
            DateTrigger(run_date=next_run),
            id=job_id,
            args=[task.id],
        )

        # 更新数据库
        async with AsyncSessionLocal() as db:
            db_task = await db.get(ScheduledTask, task.id)
            if db_task:
                db_task.next_run_at = next_run
                await db.commit()

        logger.info(
            "scheduler_job_rescheduled",
            task_id=str(task.id),
            next_run=next_run.isoformat(),
        )

    async def _calculate_next_run(self, task: ScheduledTask) -> datetime:
        """计算下次执行时间"""
        now = datetime.now()

        if task.schedule_mode == ScheduleMode.CRON:
            # Cron 模式由 APScheduler 自动计算
            cron_expr = task.schedule_config.get("cron", "0 9 * * *")
            trigger = CronTrigger.from_crontab(cron_expr)
            return trigger.get_next_fire_time(None, now)

        elif task.schedule_mode == ScheduleMode.INTERVAL:
            # 固定间隔
            minutes = task.schedule_config.get("minutes", 60)
            return now + timedelta(minutes=minutes)

        else:
            # 随机间隔
            config = task.schedule_config
            min_minutes = config.get("min_minutes", 60)
            max_minutes = config.get("max_minutes", 120)
            interval = random.randint(min_minutes, max_minutes)
            next_time = now + timedelta(minutes=interval)

            # 检查是否在活跃时段内
            start_hour = task.active_start_hour
            end_hour = task.active_end_hour

            if next_time.hour >= end_hour:
                # 超出今天活跃时段，推到明天
                tomorrow = now.date() + timedelta(days=1)
                random_offset = random.randint(0, 59)
                next_time = datetime.combine(
                    tomorrow,
                    time(start_hour, random_offset)
                )
            elif next_time.hour < start_hour:
                # 还没到今天活跃时段
                random_offset = random.randint(0, 59)
                next_time = datetime.combine(
                    now.date(),
                    time(start_hour, random_offset)
                )

            return next_time

    def get_status(self) -> dict:
        """获取调度器状态"""
        if not self.scheduler:
            return {
                "running": False,
                "active_tasks": 0,
                "pending_jobs": 0,
            }

        jobs = self.scheduler.get_jobs()
        return {
            "running": self.running,
            "active_tasks": len(jobs),
            "pending_jobs": len([j for j in jobs if j.next_run_time]),
        }

    async def pause_all(self):
        """暂停所有任务"""
        if self.scheduler:
            self.scheduler.pause()
            logger.info("scheduler_paused")

    async def resume_all(self):
        """恢复所有任务"""
        if self.scheduler:
            self.scheduler.resume()
            logger.info("scheduler_resumed")


# 全局实例
scheduler_service = SchedulerService()
