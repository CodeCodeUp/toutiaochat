"""文章生成阶段处理器"""

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


class GenerateStage(BaseStage):
    """
    文章生成阶段处理器

    负责处理文章生成相关的对话，支持：
    - 首次生成：根据话题生成完整文章
    - 追加修改：根据用户反馈修改文章
    """

    @property
    def name(self) -> str:
        return "generate"

    @property
    def default_suggestions(self) -> list[str]:
        return [
            "调整写作风格或语气",
            "增加具体案例或数据支撑",
            "修改文章结构或段落",
            "扩展或精简某个部分",
        ]

    async def _get_ai_config(self, db: AsyncSession) -> AIConfig:
        """获取 AI 配置"""
        result = await db.execute(
            select(AIConfig).where(AIConfig.type == AIConfigType.ARTICLE_GENERATE.value)
        )
        config = result.scalar_one_or_none()
        if not config or not config.api_key:
            raise AIServiceException("未配置文章生成的 API，请先在系统设置中配置")
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

        # 获取默认激活的生成提示词
        result = await db.execute(
            select(Prompt)
            .where(Prompt.type == PromptType.GENERATE, Prompt.is_active == "true")
            .order_by(Prompt.created_at.desc())
        )
        prompt = result.scalar_one_or_none()
        if not prompt:
            raise AIServiceException("未找到激活的生成提示词，请先在系统设置中配置")
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
                temperature=0.7,
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
        if not history:
            # 首次生成 - 用户直接描述需求
            messages = [
                {
                    "role": "user",
                    "content": user_message,
                }
            ]
        else:
            # 追加修改：包含当前文章内容
            messages = []
            for msg in history:
                if msg["role"] in ("user", "assistant"):
                    messages.append({"role": msg["role"], "content": msg["content"]})

            # 添加当前文章状态作为上下文
            context = f"\n\n当前文章：\n标题：{article.title}\n内容：{article.content[:2000]}..."
            messages.append({
                "role": "user",
                "content": f"{user_message}{context if article.content else ''}",
            })

        # 调用 AI
        result, token_usage = await self._call_openai(config, system_prompt, messages)

        # 更新文章
        article.title = result.get("title", article.title)
        article.content = result.get("content", article.content)
        if "image_prompts" in result:
            article.image_prompts = result["image_prompts"]
        article.token_usage = (article.token_usage or 0) + token_usage

        await db.commit()

        logger.info(
            "generate_stage_process",
            session_id=str(session.id),
            article_id=str(article.id),
            token_usage=token_usage,
        )

        return StageResult(
            reply=f"已{'生成' if not history else '修改'}文章《{article.title}》",
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

        # 全自动模式：使用默认提示生成热点文章
        messages = [
            {
                "role": "user",
                "content": "请撰写一篇适合头条号发布的热点文章，主题自选，要求内容有深度、观点鲜明、吸引读者。",
            }
        ]

        result, token_usage = await self._call_openai(config, system_prompt, messages)

        # 更新文章
        article.title = result.get("title", "")
        article.content = result.get("content", "")
        article.image_prompts = result.get("image_prompts", [])
        article.token_usage = (article.token_usage or 0) + token_usage

        await db.commit()

        logger.info(
            "generate_stage_auto",
            session_id=str(session.id),
            article_id=str(article.id),
            token_usage=token_usage,
        )

        return StageResult(
            reply=f"已自动生成文章《{article.title}》",
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

        return {
            "title": article.title,
            "content": article.content,
            "image_prompts": article.image_prompts,
            "token_usage": article.token_usage,
            "completed_at": session.updated_at.isoformat() if session.updated_at else None,
        }

    async def can_proceed(
        self,
        db: AsyncSession,
        session: WorkflowSession,
    ) -> bool:
        """检查是否可进入下一阶段"""
        article = await db.get(Article, session.article_id)
        if not article:
            return False
        # 必须有标题和内容才能进入下一阶段
        return bool(article.title and article.content)
