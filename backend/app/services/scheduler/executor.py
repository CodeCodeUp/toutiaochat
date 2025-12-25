"""任务执行器"""

import random
from datetime import datetime
from uuid import UUID
import structlog
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import json

from app.models import (
    ScheduledTask,
    ScheduledTaskType,
    TopicMode,
    PublishMode,
    Article,
    ArticleStatus,
    Task,
    TaskType,
    TaskStatus,
    Account,
    AccountStatus,
)
from app.models.workflow_session import WorkflowMode
from app.services.workflow import workflow_engine

logger = structlog.get_logger()


class TaskExecutor:
    """任务执行器"""

    async def execute(self, db: AsyncSession, scheduled_task: ScheduledTask) -> bool:
        """
        执行定时任务

        Args:
            db: 数据库会话
            scheduled_task: 定时任务

        Returns:
            bool: 是否成功
        """
        logger.info(
            "scheduled_task_execute_start",
            task_id=str(scheduled_task.id),
            task_name=scheduled_task.name,
            task_type=scheduled_task.type.value,
        )

        try:
            if scheduled_task.type == ScheduledTaskType.GENERATE:
                result = await self._execute_generate(db, scheduled_task)
            elif scheduled_task.type == ScheduledTaskType.PUBLISH:
                result = await self._execute_publish(db, scheduled_task)
            elif scheduled_task.type == ScheduledTaskType.GENERATE_AND_PUBLISH:
                result = await self._execute_generate_and_publish(db, scheduled_task)
            else:
                raise ValueError(f"未知任务类型: {scheduled_task.type}")

            # 更新任务状态
            scheduled_task.last_run_at = datetime.utcnow()
            scheduled_task.run_count += 1
            scheduled_task.last_error = None
            await db.commit()

            logger.info(
                "scheduled_task_execute_success",
                task_id=str(scheduled_task.id),
                task_name=scheduled_task.name,
            )
            return True

        except Exception as e:
            scheduled_task.last_error = str(e)
            scheduled_task.last_run_at = datetime.utcnow()
            await db.commit()

            logger.error(
                "scheduled_task_execute_failed",
                task_id=str(scheduled_task.id),
                task_name=scheduled_task.name,
                error=str(e),
            )
            return False

    async def _execute_generate(
        self, db: AsyncSession, scheduled_task: ScheduledTask
    ) -> dict:
        """执行生成任务"""
        # 获取话题
        topic = self._get_topic(scheduled_task)

        # 创建执行记录
        task_log = Task(
            type=TaskType.SCHEDULED_GENERATE,
            status=TaskStatus.RUNNING,
            scheduled_task_id=scheduled_task.id,
            account_id=scheduled_task.account_id,
            started_at=datetime.utcnow(),
        )
        db.add(task_log)
        await db.flush()

        try:
            # 创建工作流会话
            session_result = await workflow_engine.create_session(
                db=db,
                mode=WorkflowMode.AUTO,
                content_type=scheduled_task.content_type,
                custom_topic=topic,
            )

            # 执行全自动流程
            result = await workflow_engine.execute_auto(
                db=db,
                session_id=UUID(session_result["session_id"]),
            )

            if result.get("success"):
                task_log.status = TaskStatus.COMPLETED
                task_log.article_id = UUID(result["article_id"])
            else:
                task_log.status = TaskStatus.FAILED
                task_log.error_message = result.get("error", "未知错误")

        except Exception as e:
            task_log.status = TaskStatus.FAILED
            task_log.error_message = str(e)
            raise
        finally:
            task_log.completed_at = datetime.utcnow()
            await db.commit()

        return {"article_id": str(task_log.article_id) if task_log.article_id else None}

    async def _execute_publish(
        self, db: AsyncSession, scheduled_task: ScheduledTask
    ) -> dict:
        """执行发布任务"""
        from app.services.publisher import publisher
        from app.services.docx_generator import docx_generator

        # 获取账号
        if not scheduled_task.account_id:
            raise ValueError("未配置发布账号")

        account = await db.get(Account, scheduled_task.account_id)
        if not account or account.status != AccountStatus.ACTIVE:
            raise ValueError("发布账号不可用")

        # 查询待发布文章
        query = select(Article).where(
            Article.status == ArticleStatus.DRAFT,
            Article.content_type == scheduled_task.content_type,
            Article.content != "",  # 有内容
        )

        # 排序
        if scheduled_task.publish_order == "oldest":
            query = query.order_by(Article.created_at.asc())
        elif scheduled_task.publish_order == "newest":
            query = query.order_by(Article.created_at.desc())
        else:  # random
            query = query.order_by(Article.created_at.asc())  # 先查出来再随机

        # 数量限制
        if scheduled_task.publish_mode == PublishMode.ONE:
            query = query.limit(1)
        elif scheduled_task.publish_mode == PublishMode.BATCH:
            query = query.limit(scheduled_task.publish_batch_size)
        # ALL 模式不限制

        result = await db.execute(query)
        articles = list(result.scalars().all())

        if not articles:
            logger.info(
                "scheduled_publish_no_articles",
                task_id=str(scheduled_task.id),
            )
            return {"published_count": 0}

        # 随机排序
        if scheduled_task.publish_order == "random":
            random.shuffle(articles)
            if scheduled_task.publish_mode == PublishMode.ONE:
                articles = articles[:1]
            elif scheduled_task.publish_mode == PublishMode.BATCH:
                articles = articles[:scheduled_task.publish_batch_size]

        published_count = 0
        cookies = json.loads(account.cookies) if isinstance(account.cookies, str) else account.cookies

        for article in articles:
            # 创建执行记录
            task_log = Task(
                type=TaskType.SCHEDULED_PUBLISH,
                status=TaskStatus.RUNNING,
                scheduled_task_id=scheduled_task.id,
                article_id=article.id,
                account_id=scheduled_task.account_id,
                started_at=datetime.utcnow(),
            )
            db.add(task_log)
            await db.flush()

            try:
                # 生成 DOCX
                docx_path = await docx_generator.generate(
                    title=article.title if scheduled_task.content_type.value == "article" else "",
                    content=article.content,
                    images=article.images or [],
                )

                # 发布
                if scheduled_task.content_type.value == "weitoutiao":
                    publish_result = await publisher.publish_weitoutiao(
                        content=article.content,
                        cookies=cookies,
                        images=[img.get("path") for img in (article.images or []) if img.get("path")],
                        docx_path=docx_path,
                        tags=article.tags if article.tags else None,
                    )
                else:
                    publish_result = await publisher.publish_to_toutiao(
                        title=article.title,
                        content=article.content,
                        cookies=cookies,
                        images=[img.get("path") for img in (article.images or []) if img.get("path")],
                        docx_path=docx_path,
                        tags=article.tags if article.tags else None,
                    )

                if publish_result.get("success"):
                    article.status = ArticleStatus.PUBLISHED
                    article.publish_url = publish_result.get("url", "")
                    article.published_at = datetime.utcnow()
                    task_log.status = TaskStatus.COMPLETED
                    published_count += 1
                else:
                    article.status = ArticleStatus.FAILED
                    article.error_message = publish_result.get("message", "发布失败")
                    task_log.status = TaskStatus.FAILED
                    task_log.error_message = publish_result.get("message", "发布失败")

            except Exception as e:
                article.status = ArticleStatus.FAILED
                article.error_message = str(e)
                task_log.status = TaskStatus.FAILED
                task_log.error_message = str(e)
                logger.error(
                    "scheduled_publish_article_failed",
                    article_id=str(article.id),
                    error=str(e),
                )
            finally:
                task_log.completed_at = datetime.utcnow()
                await db.commit()

        logger.info(
            "scheduled_publish_completed",
            task_id=str(scheduled_task.id),
            published_count=published_count,
            total_count=len(articles),
        )

        return {"published_count": published_count, "total_count": len(articles)}

    async def _execute_generate_and_publish(
        self, db: AsyncSession, scheduled_task: ScheduledTask
    ) -> dict:
        """执行生成并发布任务"""
        from app.services.publisher import publisher
        from app.services.docx_generator import docx_generator

        # 获取账号
        if not scheduled_task.account_id:
            raise ValueError("未配置发布账号")

        account = await db.get(Account, scheduled_task.account_id)
        if not account or account.status != AccountStatus.ACTIVE:
            raise ValueError("发布账号不可用")

        # 获取话题
        topic = self._get_topic(scheduled_task)

        # 创建执行记录
        task_log = Task(
            type=TaskType.SCHEDULED_GENERATE_PUBLISH,
            status=TaskStatus.RUNNING,
            scheduled_task_id=scheduled_task.id,
            account_id=scheduled_task.account_id,
            started_at=datetime.utcnow(),
        )
        db.add(task_log)
        await db.flush()

        try:
            # 1. 生成文章
            session_result = await workflow_engine.create_session(
                db=db,
                mode=WorkflowMode.AUTO,
                content_type=scheduled_task.content_type,
                custom_topic=topic,
            )

            result = await workflow_engine.execute_auto(
                db=db,
                session_id=UUID(session_result["session_id"]),
            )

            if not result.get("success"):
                raise Exception(result.get("error", "生成文章失败"))

            article_id = UUID(result["article_id"])
            task_log.article_id = article_id

            # 2. 发布文章
            article = await db.get(Article, article_id)
            if not article:
                raise Exception("文章不存在")

            # 生成 DOCX
            docx_path = await docx_generator.generate(
                title=article.title if scheduled_task.content_type.value == "article" else "",
                content=article.content,
                images=article.images or [],
            )

            # 发布
            cookies = json.loads(account.cookies) if isinstance(account.cookies, str) else account.cookies

            if scheduled_task.content_type.value == "weitoutiao":
                publish_result = await publisher.publish_weitoutiao(
                    content=article.content,
                    cookies=cookies,
                    images=[img.get("path") for img in (article.images or []) if img.get("path")],
                    docx_path=docx_path,
                    tags=article.tags if article.tags else None,
                )
            else:
                publish_result = await publisher.publish_to_toutiao(
                    title=article.title,
                    content=article.content,
                    cookies=cookies,
                    images=[img.get("path") for img in (article.images or []) if img.get("path")],
                    docx_path=docx_path,
                    tags=article.tags if article.tags else None,
                )

            if publish_result.get("success"):
                article.status = ArticleStatus.PUBLISHED
                article.publish_url = publish_result.get("url", "")
                article.published_at = datetime.utcnow()
                task_log.status = TaskStatus.COMPLETED
            else:
                article.status = ArticleStatus.FAILED
                article.error_message = publish_result.get("message", "发布失败")
                task_log.status = TaskStatus.FAILED
                task_log.error_message = publish_result.get("message", "发布失败")

        except Exception as e:
            task_log.status = TaskStatus.FAILED
            task_log.error_message = str(e)
            raise
        finally:
            task_log.completed_at = datetime.utcnow()
            await db.commit()

        return {
            "article_id": str(task_log.article_id) if task_log.article_id else None,
            "published": task_log.status == TaskStatus.COMPLETED,
        }

    def _get_topic(self, scheduled_task: ScheduledTask) -> str | None:
        """获取话题"""
        if scheduled_task.topic_mode == TopicMode.RANDOM:
            return None  # AI 自选

        if scheduled_task.topic_mode == TopicMode.FIXED:
            if scheduled_task.topics:
                return scheduled_task.topics[0]
            return None

        if scheduled_task.topic_mode == TopicMode.LIST:
            if not scheduled_task.topics:
                return None
            # 轮流使用
            index = scheduled_task.current_topic_index % len(scheduled_task.topics)
            topic = scheduled_task.topics[index]
            # 更新索引（下次使用下一个）
            scheduled_task.current_topic_index = index + 1
            return topic

        return None


task_executor = TaskExecutor()
