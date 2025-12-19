"""图片生成阶段处理器"""

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.workflow.stages.base import BaseStage, StageResult
from app.models.workflow_session import WorkflowSession
from app.models import Article
from app.core.exceptions import AIServiceException

logger = structlog.get_logger()


class ImageStage(BaseStage):
    """
    图片生成阶段处理器

    负责处理图片生成相关的对话，支持：
    - 根据文章内容生成配图
    - 根据用户描述生成特定图片
    """

    @property
    def name(self) -> str:
        return "image"

    @property
    def default_suggestions(self) -> list[str]:
        return [
            "生成封面配图",
            "生成文章内容插图",
            "修改图片风格",
            "跳过图片生成",
        ]

    async def process(
        self,
        db: AsyncSession,
        session: WorkflowSession,
        user_message: str,
        history: list[dict],
        prompt_id: str | None = None,
    ) -> StageResult:
        """处理用户消息"""
        article = await db.get(Article, session.article_id)
        if not article:
            raise AIServiceException("关联文章不存在")

        # 解析用户意图
        if "跳过" in user_message or "不需要" in user_message:
            return StageResult(
                reply="好的，已跳过图片生成阶段",
                can_proceed=True,
                article_preview={
                    "title": article.title,
                    "images": article.images or [],
                },
                suggestions=["进入下一阶段"],
            )

        # TODO: 实际的图片生成逻辑
        # 目前使用占位符实现
        image_prompts = article.image_prompts or []

        if not image_prompts and article.content:
            # 如果没有图片提示词，根据文章内容生成建议
            return StageResult(
                reply="文章暂无图片生成提示词。您可以：\n1. 手动描述想要的图片\n2. 跳过图片生成",
                can_proceed=True,
                article_preview={
                    "title": article.title,
                    "image_prompts": image_prompts,
                },
                suggestions=self.default_suggestions,
            )

        logger.info(
            "image_stage_process",
            session_id=str(session.id),
            article_id=str(article.id),
            prompt_count=len(image_prompts),
        )

        return StageResult(
            reply=f"检测到 {len(image_prompts)} 个图片提示词。图片生成功能正在开发中，您可以选择跳过此阶段。",
            can_proceed=True,
            article_preview={
                "title": article.title,
                "image_prompts": image_prompts,
                "images": article.images or [],
            },
            suggestions=self.default_suggestions,
        )

    async def auto_execute(
        self,
        db: AsyncSession,
        session: WorkflowSession,
    ) -> StageResult:
        """自动模式执行"""
        article = await db.get(Article, session.article_id)
        if not article:
            raise AIServiceException("关联文章不存在")

        image_prompts = article.image_prompts or []

        # TODO: 调用图片生成服务
        # 目前自动模式下跳过图片生成
        images = []

        logger.info(
            "image_stage_auto",
            session_id=str(session.id),
            article_id=str(article.id),
            image_count=len(images),
        )

        return StageResult(
            reply="图片生成阶段已完成（跳过）",
            can_proceed=True,
            article_preview={
                "title": article.title,
                "images": images,
            },
            extra_data={"image_count": len(images)},
        )

    async def snapshot(
        self,
        db: AsyncSession,
        session: WorkflowSession,
    ) -> dict:
        """保存阶段快照"""
        article = await db.get(Article, session.article_id)
        if not article:
            return {}

        return {
            "image_prompts": article.image_prompts or [],
            "images": article.images or [],
            "image_count": len(article.images or []),
            "completed_at": session.updated_at.isoformat() if session.updated_at else None,
        }
