import json
from openai import AsyncOpenAI
import structlog
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.exceptions import AIServiceException
from app.models.prompt import Prompt, PromptType
from app.models.ai_config import AIConfig, AIConfigType

logger = structlog.get_logger()


async def _get_ai_config(db: AsyncSession, config_type: AIConfigType) -> AIConfig:
    """从数据库获取 AI 配置"""
    result = await db.execute(select(AIConfig).where(AIConfig.type == config_type.value))
    config = result.scalar_one_or_none()
    if not config or not config.api_key:
        raise AIServiceException(f"未配置{config_type.value}的 API，请先在系统设置中配置")
    return config


async def _get_active_prompt(db: AsyncSession, prompt_type: PromptType) -> str:
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
    db: AsyncSession,
    topic: str,
    category: str = "其他",
    style: str | None = None,
) -> dict:
    """
    生成文章
    返回: {"title": str, "content": str, "image_prompts": list, "token_usage": int}
    """
    config = await _get_ai_config(db, AIConfigType.ARTICLE_GENERATE)
    system_prompt = await _get_active_prompt(db, PromptType.GENERATE)

    client = AsyncOpenAI(api_key=config.api_key, base_url=config.api_url or None)

    user_prompt = f"请根据以下话题撰写一篇{category}类的头条文章：\n\n【主题】{topic}"
    if style:
        user_prompt += f"\n\n写作风格要求：{style}"

    try:
        print(f"[DEBUG] model={config.model}, api_url={config.api_url}")
        response = await client.chat.completions.create(
            model=config.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.7,
            response_format={"type": "json_object"},
        )
        print(f"[DEBUG] response type={type(response)}, response={str(response)[:200]}")

        content = response.choices[0].message.content
        # 清理 markdown 代码块
        if content.startswith("```"):
            content = content.split("\n", 1)[1] if "\n" in content else content[3:]
        if content.endswith("```"):
            content = content[:-3]
        content = content.strip()

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


async def humanize_article(db: AsyncSession, title: str, content: str) -> dict:
    """去AI化处理/优化文章"""
    config = await _get_ai_config(db, AIConfigType.ARTICLE_HUMANIZE)
    system_prompt = await _get_active_prompt(db, PromptType.HUMANIZE)

    client = AsyncOpenAI(api_key=config.api_key, base_url=config.api_url or None)

    user_prompt = f"请改写以下文章：\n\n标题：{title}\n\n正文：{content}"

    try:
        response = await client.chat.completions.create(
            model=config.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
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

        result = json.loads(content)
        result["token_usage"] = response.usage.total_tokens if response.usage else 0

        logger.info("article_humanized", title=title[:30])
        return result

    except Exception as e:
        logger.error("humanize_error", error=str(e))
        raise AIServiceException(f"去AI化处理失败: {str(e)}")


async def test_connection(db: AsyncSession, config_type: AIConfigType) -> bool:
    """测试 AI 服务连接"""
    try:
        config = await _get_ai_config(db, config_type)
        client = AsyncOpenAI(api_key=config.api_key, base_url=config.api_url or None)
        await client.chat.completions.create(
            model=config.model,
            messages=[{"role": "user", "content": "Hello"}],
            max_tokens=10,
        )
        return True
    except Exception as e:
        logger.error("ai_connection_test_failed", error=str(e))
        return False
