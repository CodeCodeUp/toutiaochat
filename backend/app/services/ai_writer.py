import json
from typing import Optional
from openai import AsyncOpenAI
import structlog
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import settings
from app.core.exceptions import AIServiceException
from app.models.prompt import Prompt, PromptType

logger = structlog.get_logger()


class AIWriterService:
    def __init__(self):
        self.client = AsyncOpenAI(
            api_key=settings.OPENAI_API_KEY,
            base_url=settings.OPENAI_BASE_URL,
        )
        self.model = settings.OPENAI_MODEL

    async def _get_active_prompt(self, db: AsyncSession, prompt_type: PromptType) -> str:
        """从数据库获取激活的提示词"""
        result = await db.execute(
            select(Prompt)
            .where(Prompt.type == prompt_type, Prompt.is_active == "true")
            .order_by(Prompt.created_at.desc())
        )
        prompt = result.scalar_one_or_none()

        if not prompt:
            raise AIServiceException(f"未找到类型为{prompt_type}的激活提示词，请先在系统设置中配置")

        return prompt.content

    async def generate_article(
        self,
        topic: str,
        category: str = "其他",
        style: Optional[str] = None,
        db: Optional[AsyncSession] = None,
    ) -> dict:
        """
        生成文章
        返回: {"title": str, "content": str, "image_prompts": list, "token_usage": int}
        """
        if not db:
            raise AIServiceException("数据库会话不能为空")

        # 从数据库读取提示词
        system_prompt = await self._get_active_prompt(db, PromptType.GENERATE)

        user_prompt = f"请根据以下话题撰写一篇{category}类的头条文章：\n\n【主题】{topic}"

        if style:
            user_prompt += f"\n\n写作风格要求：{style}"

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.7,
                response_format={"type": "json_object"},
            )

            content = response.choices[0].message.content
            token_usage = response.usage.total_tokens if response.usage else 0

            result = json.loads(content)
            result["token_usage"] = token_usage

            logger.info("article_generated", topic=topic[:50], tokens=token_usage)
            return result

        except json.JSONDecodeError as e:
            logger.error("json_parse_error", error=str(e))
            raise AIServiceException(f"AI返回格式错误: {str(e)}")
        except Exception as e:
            logger.error("ai_service_error", error=str(e))
            raise AIServiceException(f"AI服务错误: {str(e)}")

    async def humanize_article(
        self,
        title: str,
        content: str,
        db: Optional[AsyncSession] = None,
    ) -> dict:
        """
        去AI化处理/优化文章
        """
        if not db:
            raise AIServiceException("数据库会话不能为空")

        # 从数据库读取提示词
        system_prompt = await self._get_active_prompt(db, PromptType.HUMANIZE)

        user_prompt = f"请改写以下文章：\n\n标题：{title}\n\n正文：{content}"

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.8,
                response_format={"type": "json_object"},
            )

            result = json.loads(response.choices[0].message.content)
            result["token_usage"] = response.usage.total_tokens if response.usage else 0

            logger.info("article_humanized", title=title[:30])
            return result

        except Exception as e:
            logger.error("humanize_error", error=str(e))
            raise AIServiceException(f"去AI化处理失败: {str(e)}")

    async def test_connection(self) -> bool:
        """测试AI服务连接"""
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": "Hello"}],
                max_tokens=10,
            )
            return True
        except Exception as e:
            logger.error("ai_connection_test_failed", error=str(e))
            return False


ai_writer = AIWriterService()
