"""文章优化阶段处理器"""

import json
from openai import AsyncOpenAI
import structlog
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.services.workflow.stages.base import BaseStage, StageResult
from app.models.workflow_session import WorkflowSession
from app.models import Article
from app.models.prompt import Prompt, PromptType
from app.models.ai_config import AIConfig, AIConfigType
from app.core.exceptions import AIServiceException

logger = structlog.get_logger()


class OptimizeStage(BaseStage):
    """
    文章优化阶段处理器

    负责处理文章优化（去 AI 化）相关的对话，支持：
    - 自动优化：降低 AI 痕迹
    - 手动调整：根据用户要求修改风格
    """

    @property
    def name(self) -> str:
        return "optimize"

    @property
    def default_suggestions(self) -> list[str]:
        return [
            "降低 AI 痕迹，更口语化",
            "调整为更专业的语气",
            "增加个人观点或情感色彩",
            "简化句式，提高可读性",
        ]

    async def _get_ai_config(self, db: AsyncSession) -> AIConfig:
        """获取 AI 配置"""
        result = await db.execute(
            select(AIConfig).where(AIConfig.type == AIConfigType.ARTICLE_HUMANIZE.value)
        )
        config = result.scalar_one_or_none()
        if not config or not config.api_key:
            raise AIServiceException("未配置文章优化的 API，请先在系统设置中配置")
        return config

    async def _get_system_prompt(self, db: AsyncSession, prompt_id: str | None = None) -> str:
        """获取系统提示词"""
        if prompt_id:
            result = await db.execute(
                select(Prompt).where(Prompt.id == prompt_id)
            )
            prompt = result.scalar_one_or_none()
            if prompt:
                return prompt.content

        # 获取默认激活的优化提示词
        result = await db.execute(
            select(Prompt)
            .where(Prompt.type == PromptType.HUMANIZE, Prompt.is_active == "true")
            .order_by(Prompt.created_at.desc())
        )
        prompt = result.scalar_one_or_none()
        if not prompt:
            raise AIServiceException("未找到激活的优化提示词，请先在系统设置中配置")
        return prompt.content

    async def _call_openai(
        self,
        config: AIConfig,
        system_prompt: str,
        messages: list[dict],
    ) -> tuple[dict, int]:
        """调用 OpenAI API"""
        client = AsyncOpenAI(api_key=config.api_key, base_url=config.api_url or None)

        all_messages = [{"role": "system", "content": system_prompt}] + messages

        try:
            response = await client.chat.completions.create(
                model=config.model,
                messages=all_messages,
                temperature=0.8,
                response_format={"type": "json_object"},
            )

            content = response.choices[0].message.content
            # 清理 markdown 代码块
            if content.startswith("```"):
                content = content.split("\n", 1)[1] if "\n" in content else content[3:]
            if content.endswith("```"):
                content = content[:-3]
            content = content.strip()

            token_usage = response.usage.total_tokens if response.usage else 0
            result = json.loads(content)

            return result, token_usage

        except json.JSONDecodeError as e:
            logger.error("json_parse_error", error=str(e))
            raise AIServiceException(f"AI 返回格式错误: {str(e)}")
        except Exception as e:
            logger.error("ai_service_error", error=str(e))
            raise AIServiceException(f"AI 服务错误: {str(e)}")

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

        config = await self._get_ai_config(db)
        system_prompt = await self._get_system_prompt(db, prompt_id)

        # 构建消息
        user_content = f"请改写以下文章：\n\n标题：{article.title}\n\n正文：{article.content}"
        if user_message:
            user_content += f"\n\n用户要求：{user_message}"

        messages = [{"role": "user", "content": user_content}]

        # 调用 AI
        result, token_usage = await self._call_openai(config, system_prompt, messages)

        # 保存原始内容用于对比（如果是首次优化）
        if not history:
            stage_data = session.stage_data or {}
            stage_data["original_title"] = article.title
            stage_data["original_content"] = article.content
            session.stage_data = stage_data

        # 更新文章
        article.title = result.get("title", article.title)
        article.content = result.get("content", article.content)
        article.token_usage = (article.token_usage or 0) + token_usage

        await db.commit()

        logger.info(
            "optimize_stage_process",
            session_id=str(session.id),
            article_id=str(article.id),
            token_usage=token_usage,
        )

        return StageResult(
            reply="已完成文章优化",
            can_proceed=True,
            article_preview={
                "title": article.title,
                "content": article.content[:500] + "..." if len(article.content) > 500 else article.content,
                "full_content": article.content,
            },
            suggestions=self.default_suggestions,
            extra_data={"token_usage": token_usage},
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

        config = await self._get_ai_config(db)
        system_prompt = await self._get_system_prompt(db)

        messages = [
            {
                "role": "user",
                "content": f"请改写以下文章：\n\n标题：{article.title}\n\n正文：{article.content}",
            }
        ]

        result, token_usage = await self._call_openai(config, system_prompt, messages)

        # 保存原始内容
        stage_data = session.stage_data or {}
        stage_data["original_title"] = article.title
        stage_data["original_content"] = article.content
        session.stage_data = stage_data

        # 更新文章
        article.title = result.get("title", article.title)
        article.content = result.get("content", article.content)
        article.token_usage = (article.token_usage or 0) + token_usage

        await db.commit()

        logger.info(
            "optimize_stage_auto",
            session_id=str(session.id),
            article_id=str(article.id),
            token_usage=token_usage,
        )

        return StageResult(
            reply="已自动完成文章优化",
            can_proceed=True,
            article_preview={
                "title": article.title,
                "content": article.content[:500] + "...",
            },
            extra_data={"token_usage": token_usage},
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

        stage_data = session.stage_data or {}

        return {
            "optimized_title": article.title,
            "optimized_content": article.content,
            "original_title": stage_data.get("original_title"),
            "original_content": stage_data.get("original_content"),
            "token_usage": article.token_usage,
            "completed_at": session.updated_at.isoformat() if session.updated_at else None,
        }
