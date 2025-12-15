import json
from typing import Optional
from openai import AsyncOpenAI
import structlog

from app.core.config import settings
from app.core.exceptions import AIServiceException

logger = structlog.get_logger()


class AIWriterService:
    def __init__(self):
        self.client = AsyncOpenAI(
            api_key=settings.OPENAI_API_KEY,
            base_url=settings.OPENAI_BASE_URL,
        )
        self.model = settings.OPENAI_MODEL

    async def generate_article(
        self,
        topic: str,
        category: str = "其他",
        style: Optional[str] = None,
    ) -> dict:
        """
        生成文章
        返回: {"title": str, "content": str, "image_prompts": list, "token_usage": int}
        """
        system_prompt = """你是一名资深的自媒体写作专家，擅长撰写吸引读者的头条文章。

写作要求：
1. 标题：采用三段式标题，总字数不超过25个字，要有吸引力
2. 正文：1200-1500字，分3-5个自然段，不要小标题
3. 风格：口语化、接地气，像在和朋友聊天
4. 避免：
   - 不要用"首先、其次、最后"等排序词
   - 不要用"总之、综上所述"等总结词
   - 不要用"值得注意的是"等套话
   - 不要过度使用成语和书面语
5. 图片提示词：生成3-4个适合配图的英文提示词，用于AI生图

输出格式（JSON）：
{
    "title": "文章标题",
    "content": "文章正文内容",
    "image_prompts": ["prompt1", "prompt2", "prompt3"]
}"""

        user_prompt = f"请根据以下话题撰写一篇{category}类的头条文章：\n\n{topic}"

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

    async def humanize_article(self, title: str, content: str) -> dict:
        """
        去AI化处理
        """
        system_prompt = """你是一名文章润色专家，任务是将AI生成的文章改写得更像人类写的。

改写要求：
1. 保持原意不变
2. 增加口语化表达
3. 适当加入个人观点和情感
4. 打乱句式结构，增加变化
5. 减少书面语和成语的使用
6. 标题可以微调但保持吸引力

输出格式（JSON）：
{
    "title": "改写后的标题",
    "content": "改写后的正文"
}"""

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
