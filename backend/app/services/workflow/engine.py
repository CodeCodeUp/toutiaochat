"""工作流引擎 - 状态机核心"""

from uuid import UUID
import structlog
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models import Article, ArticleStatus
from app.models.workflow_session import WorkflowSession, WorkflowMode, WorkflowStage
from app.models.prompt import ContentType
from app.models.workflow_config import WorkflowConfig
from app.services.workflow.conversation import conversation_mgr
from app.services.workflow.stages import GenerateStage, OptimizeStage, ImageStage, EditStage
from app.services.workflow.stages.base import BaseStage, StageResult
from app.core.exceptions import AIServiceException

logger = structlog.get_logger()


class WorkflowEngine:
    """
    工作流引擎

    负责工作流的创建、状态管理和阶段编排。
    支持半自动（手动）和全自动两种模式。
    """

    # 阶段处理器映射
    STAGE_HANDLERS: dict[WorkflowStage, BaseStage] = {
        WorkflowStage.GENERATE: GenerateStage(),
        WorkflowStage.OPTIMIZE: OptimizeStage(),
        WorkflowStage.IMAGE: ImageStage(),
        WorkflowStage.EDIT: EditStage(),
    }

    # 阶段转移映射
    STAGE_TRANSITIONS: dict[WorkflowStage, WorkflowStage] = {
        WorkflowStage.GENERATE: WorkflowStage.OPTIMIZE,
        WorkflowStage.OPTIMIZE: WorkflowStage.IMAGE,
        WorkflowStage.IMAGE: WorkflowStage.EDIT,
        WorkflowStage.EDIT: WorkflowStage.COMPLETED,
    }

    # 阶段进度映射
    STAGE_PROGRESS: dict[WorkflowStage, int] = {
        WorkflowStage.GENERATE: 25,
        WorkflowStage.OPTIMIZE: 50,
        WorkflowStage.IMAGE: 75,
        WorkflowStage.EDIT: 90,
        WorkflowStage.COMPLETED: 100,
    }

    async def create_session(
        self,
        db: AsyncSession,
        mode: WorkflowMode,
        content_type: ContentType = ContentType.ARTICLE,
        custom_topic: str | None = None,
    ) -> dict:
        """
        创建工作流会话

        Args:
            db: 数据库会话
            mode: 工作流模式
            content_type: 内容类型
            custom_topic: 自定义话题（全自动模式）

        Returns:
            dict: 包含 session_id, article_id, stage, mode, content_type
        """
        # 1. 创建文章
        article = Article(
            title="",
            content="",
            content_type=content_type,
            status=ArticleStatus.DRAFT,
        )
        db.add(article)
        await db.flush()

        # 2. 创建工作流会话
        # 如果有自定义话题，存入 stage_data
        stage_data = {}
        if custom_topic:
            stage_data["custom_topic"] = custom_topic

        session = WorkflowSession(
            article_id=article.id,
            mode=mode,
            content_type=content_type,
            current_stage=WorkflowStage.GENERATE,
            stage_data=stage_data,
            progress="0",
        )
        db.add(session)
        await db.commit()

        logger.info(
            "workflow_session_created",
            session_id=str(session.id),
            article_id=str(article.id),
            mode=mode.value,
            content_type=content_type.value,
            has_custom_topic=bool(custom_topic),
        )

        return {
            "session_id": str(session.id),
            "article_id": str(article.id),
            "stage": session.current_stage.value,
            "mode": session.mode.value,
            "content_type": session.content_type.value,
        }

    async def process_message(
        self,
        db: AsyncSession,
        session_id: UUID,
        user_message: str,
        prompt_id: UUID | None = None,
    ) -> dict:
        """
        处理用户消息（半自动模式）

        Args:
            db: 数据库会话
            session_id: 工作流会话ID
            user_message: 用户消息
            prompt_id: 可选的提示词ID

        Returns:
            dict: 处理结果
        """
        logger.info(
            "workflow_process_message_start",
            session_id=str(session_id),
            message_preview=user_message[:50] if user_message else "(empty)",
            has_prompt_id=bool(prompt_id),
        )

        session = await self._get_session(db, session_id)

        # 检查是否已完成
        if session.current_stage == WorkflowStage.COMPLETED:
            logger.warning("workflow_already_completed", session_id=str(session_id))
            raise AIServiceException("工作流已完成，无法继续处理消息")

        # 获取阶段处理器
        handler = self.STAGE_HANDLERS.get(session.current_stage)
        if not handler:
            raise AIServiceException(f"阶段 {session.current_stage.value} 无法处理消息")

        logger.info(
            "workflow_process_message_handler",
            session_id=str(session_id),
            stage=session.current_stage.value,
            handler=handler.name,
        )

        # 获取对话历史
        history = await conversation_mgr.get_history(
            db, session_id, session.current_stage.value
        )
        logger.info(
            "workflow_process_message_history",
            session_id=str(session_id),
            history_count=len(history),
        )

        # 处理消息
        result = await handler.process(
            db, session, user_message, history, str(prompt_id) if prompt_id else None
        )

        logger.info(
            "workflow_process_message_result",
            session_id=str(session_id),
            can_proceed=result.can_proceed,
            reply_length=len(result.reply),
            has_preview=bool(result.article_preview),
        )

        # 保存对话
        await conversation_mgr.add_message(
            db, session_id, session.current_stage.value, "user", user_message
        )
        await conversation_mgr.add_message(
            db, session_id, session.current_stage.value, "assistant", result.reply,
            extra_data=result.extra_data,
        )

        await db.commit()

        return {
            "assistant_reply": result.reply,
            "stage": session.current_stage.value,
            "can_proceed": result.can_proceed,
            "article_preview": result.article_preview,
            "suggestions": result.suggestions,
        }

    async def next_stage(
        self,
        db: AsyncSession,
        session_id: UUID,
    ) -> dict:
        """
        进入下一阶段

        Args:
            db: 数据库会话
            session_id: 工作流会话ID

        Returns:
            dict: 包含 previous_stage, current_stage, initial_reply, article_preview, suggestions
        """
        logger.info("workflow_next_stage_start", session_id=str(session_id))

        session = await self._get_session(db, session_id)
        previous_stage = session.current_stage

        logger.info(
            "workflow_next_stage_current",
            session_id=str(session_id),
            current_stage=previous_stage.value,
        )

        # 检查是否可进入下一阶段
        handler = self.STAGE_HANDLERS.get(session.current_stage)
        if handler:
            can_proceed = await handler.can_proceed(db, session)
            logger.info(
                "workflow_next_stage_check",
                session_id=str(session_id),
                can_proceed=can_proceed,
            )
            if not can_proceed:
                raise AIServiceException("当前阶段尚未完成，无法进入下一阶段")

            # 保存当前阶段快照
            snapshot = await handler.snapshot(db, session)
            if session.stage_data is None:
                session.stage_data = {}
            session.stage_data[session.current_stage.value] = snapshot
            logger.info(
                "workflow_next_stage_snapshot_saved",
                session_id=str(session_id),
                stage=session.current_stage.value,
            )

        # 状态机转移
        next_stage = self.STAGE_TRANSITIONS.get(session.current_stage)
        if not next_stage:
            raise AIServiceException("已经是最终阶段")

        session.current_stage = next_stage
        session.progress = str(self.STAGE_PROGRESS.get(next_stage, 0))

        await db.commit()

        logger.info(
            "workflow_stage_changed",
            session_id=str(session_id),
            previous_stage=previous_stage.value,
            current_stage=next_stage.value,
            progress=session.progress,
        )

        result = {
            "previous_stage": previous_stage.value,
            "current_stage": next_stage.value,
            "snapshot_saved": True,
        }

        # 如果新阶段不是完成阶段，获取初始提示
        if next_stage != WorkflowStage.COMPLETED:
            new_handler = self.STAGE_HANDLERS.get(next_stage)
            if new_handler:
                logger.info(
                    "workflow_next_stage_get_initial",
                    session_id=str(session_id),
                    new_stage=next_stage.value,
                    handler=new_handler.name,
                )
                try:
                    # 调用新阶段处理器，传入空历史触发初始提示
                    stage_result = await new_handler.process(
                        db, session, "", [], None  # 空消息、空历史
                    )

                    logger.info(
                        "workflow_next_stage_initial_result",
                        session_id=str(session_id),
                        reply_length=len(stage_result.reply),
                        has_preview=bool(stage_result.article_preview),
                    )

                    # 保存初始对话
                    await conversation_mgr.add_message(
                        db, session_id, next_stage.value, "assistant", stage_result.reply,
                        extra_data=stage_result.extra_data,
                    )
                    await db.commit()

                    result["initial_reply"] = stage_result.reply
                    result["article_preview"] = stage_result.article_preview
                    result["suggestions"] = stage_result.suggestions or []
                except Exception as e:
                    logger.warning(
                        "workflow_next_stage_initial_failed",
                        session_id=str(session_id),
                        error=str(e),
                    )

        return result

    async def _get_workflow_config(self, db: AsyncSession, content_type: ContentType) -> WorkflowConfig | None:
        """获取工作流配置"""
        result = await db.execute(
            select(WorkflowConfig).where(WorkflowConfig.content_type == content_type)
        )
        return result.scalar_one_or_none()

    async def execute_auto(
        self,
        db: AsyncSession,
        session_id: UUID,
    ) -> dict:
        """
        执行全自动流程

        Args:
            db: 数据库会话
            session_id: 工作流会话ID

        Returns:
            dict: 执行结果
        """
        logger.info("workflow_auto_start", session_id=str(session_id))

        session = await self._get_session(db, session_id)
        article = await db.get(Article, session.article_id)

        if not article:
            logger.error("workflow_auto_article_not_found", session_id=str(session_id))
            raise AIServiceException("关联文章不存在")

        # 获取工作流配置
        config = await self._get_workflow_config(db, session.content_type)
        enable_optimize = config.enable_optimize if config else True
        enable_image_gen = config.enable_image_gen if config else True
        enable_auto_publish = config.enable_auto_publish if config else False

        logger.info(
            "workflow_auto_config",
            session_id=str(session_id),
            enable_optimize=enable_optimize,
            enable_image_gen=enable_image_gen,
            enable_auto_publish=enable_auto_publish,
        )

        try:
            # 阶段1: 生成文章 (25%)
            logger.info("workflow_auto_stage_generate_start", session_id=str(session_id))
            session.current_stage = WorkflowStage.GENERATE
            session.progress = "10"
            await db.commit()

            generate_handler = self.STAGE_HANDLERS[WorkflowStage.GENERATE]
            gen_result = await generate_handler.auto_execute(db, session)

            snapshot = await generate_handler.snapshot(db, session)
            session.stage_data = session.stage_data or {}
            session.stage_data["generate"] = snapshot
            session.progress = "25"
            await db.commit()
            logger.info(
                "workflow_auto_stage_generate_done",
                session_id=str(session_id),
                article_title=article.title[:50] if article.title else "(empty)",
            )

            # 阶段2: 优化文章 (50%) - 根据配置决定是否执行
            if enable_optimize:
                logger.info("workflow_auto_stage_optimize_start", session_id=str(session_id))
                session.current_stage = WorkflowStage.OPTIMIZE
                session.progress = "30"
                await db.commit()

                optimize_handler = self.STAGE_HANDLERS[WorkflowStage.OPTIMIZE]
                opt_result = await optimize_handler.auto_execute(db, session)

                snapshot = await optimize_handler.snapshot(db, session)
                session.stage_data["optimize"] = snapshot
                session.progress = "50"
                await db.commit()
                logger.info("workflow_auto_stage_optimize_done", session_id=str(session_id))
            else:
                logger.info("workflow_auto_stage_optimize_skipped", session_id=str(session_id))
                session.progress = "50"
                await db.commit()

            # 阶段3: 图片生成 (75%) - 根据配置决定是否执行
            if enable_image_gen:
                logger.info("workflow_auto_stage_image_start", session_id=str(session_id))
                session.current_stage = WorkflowStage.IMAGE
                session.progress = "60"
                await db.commit()

                image_handler = self.STAGE_HANDLERS[WorkflowStage.IMAGE]
                img_result = await image_handler.auto_execute(db, session)

                snapshot = await image_handler.snapshot(db, session)
                session.stage_data["image"] = snapshot
                session.progress = "75"
                await db.commit()
                logger.info(
                    "workflow_auto_stage_image_done",
                    session_id=str(session_id),
                    image_count=len(article.images or []),
                )
            else:
                logger.info("workflow_auto_stage_image_skipped", session_id=str(session_id))
                session.progress = "75"
                await db.commit()

            # 阶段4: 编辑阶段 (90%)
            logger.info("workflow_auto_stage_edit_start", session_id=str(session_id))
            session.current_stage = WorkflowStage.EDIT
            session.progress = "80"
            await db.commit()

            edit_handler = self.STAGE_HANDLERS[WorkflowStage.EDIT]
            edit_result = await edit_handler.auto_execute(db, session)

            snapshot = await edit_handler.snapshot(db, session)
            session.stage_data["edit"] = snapshot
            session.progress = "90"
            await db.commit()
            logger.info("workflow_auto_stage_edit_done", session_id=str(session_id))

            # 阶段5: 自动发布 - 根据配置决定是否执行
            if enable_auto_publish:
                logger.info("workflow_auto_stage_publish_start", session_id=str(session_id))
                session.progress = "95"
                await db.commit()

                try:
                    from app.services.publisher import publisher
                    from app.services.docx_generator import docx_generator
                    from app.models.account import Account, AccountStatus

                    # 获取活跃账号
                    result = await db.execute(
                        select(Account).where(Account.status == AccountStatus.ACTIVE).limit(1)
                    )
                    account = result.scalar_one_or_none()

                    if account and account.cookies:
                        # 生成 DOCX
                        docx_path = await docx_generator.generate(
                            title=article.title if session.content_type == ContentType.ARTICLE else "",
                            content=article.content,
                            images=article.images or [],
                        )

                        # 发布
                        import json
                        cookies = json.loads(account.cookies) if isinstance(account.cookies, str) else account.cookies

                        if session.content_type == ContentType.WEITOUTIAO:
                            publish_result = await publisher.publish_weitoutiao(
                                content=article.content,
                                cookies=cookies,
                                images=[img.get("path") for img in (article.images or []) if img.get("path")],
                                docx_path=docx_path,
                            )
                        else:
                            publish_result = await publisher.publish_to_toutiao(
                                title=article.title,
                                content=article.content,
                                cookies=cookies,
                                images=[img.get("path") for img in (article.images or []) if img.get("path")],
                                docx_path=docx_path,
                            )

                        if publish_result.get("success"):
                            article.status = ArticleStatus.PUBLISHED
                            article.publish_url = publish_result.get("url", "")
                            logger.info(
                                "workflow_auto_publish_success",
                                session_id=str(session_id),
                                article_id=str(article.id),
                            )
                        else:
                            logger.warning(
                                "workflow_auto_publish_failed",
                                session_id=str(session_id),
                                error=publish_result.get("message"),
                            )
                    else:
                        logger.warning(
                            "workflow_auto_publish_no_account",
                            session_id=str(session_id),
                        )
                except Exception as pub_error:
                    logger.error(
                        "workflow_auto_publish_error",
                        session_id=str(session_id),
                        error=str(pub_error),
                    )
                    # 发布失败不影响整体流程
            else:
                logger.info("workflow_auto_stage_publish_skipped", session_id=str(session_id))

            # 完成
            session.current_stage = WorkflowStage.COMPLETED
            session.progress = "100"
            await db.commit()

            logger.info(
                "workflow_auto_completed",
                session_id=str(session_id),
                article_id=str(article.id),
                article_title=article.title,
                image_count=len(article.images or []),
                auto_published=enable_auto_publish,
            )

            return {
                "success": True,
                "article_id": str(article.id),
                "title": article.title,
                "stage": "completed",
            }

        except Exception as e:
            session.error_message = str(e)
            await db.commit()

            logger.error(
                "workflow_auto_failed",
                session_id=str(session_id),
                current_stage=session.current_stage.value,
                error=str(e),
            )

            return {
                "success": False,
                "error": str(e),
            }

    async def get_session_status(
        self,
        db: AsyncSession,
        session_id: UUID,
    ) -> dict:
        """
        查询会话状态（用于轮询）

        Args:
            db: 数据库会话
            session_id: 工作流会话ID

        Returns:
            dict: 会话状态
        """
        session = await self._get_session(db, session_id)
        article = await db.get(Article, session.article_id)

        status = "processing"
        if session.current_stage == WorkflowStage.COMPLETED:
            status = "completed"
        elif session.error_message:
            status = "failed"

        result = {
            "session_id": str(session.id),
            "article_id": str(session.article_id),
            "stage": session.current_stage.value,
            "mode": session.mode.value,
            "progress": int(session.progress or 0),
            "status": status,
            "error": session.error_message,
        }

        if article and status == "completed":
            result["result"] = {
                "title": article.title,
                "content_preview": article.content[:200] + "..." if article.content else "",
            }

        return result

    async def get_session_detail(
        self,
        db: AsyncSession,
        session_id: UUID,
    ) -> dict:
        """
        获取会话详情

        Args:
            db: 数据库会话
            session_id: 工作流会话ID

        Returns:
            dict: 会话详情
        """
        session = await self._get_session(db, session_id)
        article = await db.get(Article, session.article_id)

        messages = await conversation_mgr.get_all_messages(db, session_id)

        return {
            "session_id": str(session.id),
            "article_id": str(session.article_id),
            "stage": session.current_stage.value,
            "mode": session.mode.value,
            "progress": int(session.progress or 0),
            "stage_data": session.stage_data,
            "error": session.error_message,
            "created_at": session.created_at.isoformat(),
            "updated_at": session.updated_at.isoformat(),
            "article": {
                "title": article.title if article else "",
                "content": article.content if article else "",
                "image_prompts": article.image_prompts if article else [],
                "images": article.images if article else [],
                "token_usage": article.token_usage if article else 0,
            } if article else None,
            "messages": messages,
        }

    async def _get_session(
        self,
        db: AsyncSession,
        session_id: UUID,
    ) -> WorkflowSession:
        """获取工作流会话"""
        result = await db.execute(
            select(WorkflowSession).where(WorkflowSession.id == session_id)
        )
        session = result.scalar_one_or_none()
        if not session:
            raise AIServiceException(f"工作流会话 {session_id} 不存在")
        return session


# 导出单例
workflow_engine = WorkflowEngine()
