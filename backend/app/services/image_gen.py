"""图片生成服务"""

import asyncio
import base64
import uuid
from pathlib import Path
from typing import List, Tuple
import structlog
import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.ai_config import AIConfig, AIConfigType
from app.core.config import settings

logger = structlog.get_logger()

# 图片存储根目录
IMAGES_DIR = Path(settings.STATIC_DIR) / "images"


async def _get_image_config(db: AsyncSession) -> AIConfig | None:
    """从数据库获取图片生成配置"""
    result = await db.execute(
        select(AIConfig).where(AIConfig.type == AIConfigType.IMAGE_GENERATE.value)
    )
    config = result.scalar_one_or_none()
    if not config or not config.api_url:
        return None
    return config


async def generate_image(
    db: AsyncSession,
    prompt: str,
    article_id: str,
    index: int = 0,
) -> dict:
    """
    生成单张图片

    Args:
        db: 数据库会话
        prompt: 图片描述
        article_id: 文章ID（用于目录组织）
        index: 图片序号

    Returns:
        dict: {"success": bool, "path": str, "url": str, "error": str}
    """
    config = await _get_image_config(db)
    if not config:
        logger.info("image_gen_skipped_no_config", prompt=prompt[:50])
        return {"success": False, "error": "未配置图片生成 API"}

    try:
        logger.info("image_gen_start", prompt=prompt[:100], model=config.model)

        response_data = await _call_api(config, prompt)

        if response_data.get("error"):
            logger.error("image_gen_api_error", error=response_data["error"])
            return {"success": False, "error": response_data["error"]}

        base64_data, img_format = _extract_image_data(response_data)
        if not base64_data:
            logger.error("image_extract_failed", response_keys=list(response_data.keys()))
            return {"success": False, "error": "无法从响应中提取图片数据"}

        # 保存图片
        saved_path, url = _save_image(base64_data, article_id, index, img_format)
        logger.info("image_gen_success", path=saved_path, url=url)

        return {"success": True, "path": saved_path, "url": url}

    except Exception as e:
        logger.error("image_gen_exception", error=str(e), prompt=prompt[:50])
        return {"success": False, "error": str(e)}


async def generate_images(
    db: AsyncSession,
    prompts: List[str],
    article_id: str,
    max_concurrent: int = 3,
) -> dict:
    """
    批量生成图片（支持并发）

    Args:
        db: 数据库会话
        prompts: 图片描述列表
        article_id: 文章ID
        max_concurrent: 最大并发数

    Returns:
        dict: {"success_count": int, "images": list, "errors": list}
    """
    results = {"success_count": 0, "images": [], "errors": []}

    # 限制并发数
    semaphore = asyncio.Semaphore(max_concurrent)

    async def gen_with_semaphore(prompt: str, index: int):
        async with semaphore:
            return await generate_image(db, prompt, article_id, index)

    # 并发生成
    tasks = [
        gen_with_semaphore(prompt, i)
        for i, prompt in enumerate(prompts)
    ]
    gen_results = await asyncio.gather(*tasks, return_exceptions=True)

    for i, result in enumerate(gen_results):
        if isinstance(result, Exception):
            results["errors"].append({"index": i, "error": str(result)})
        elif result.get("success"):
            results["success_count"] += 1
            results["images"].append({
                "index": i,
                "url": result["url"],
                "path": result["path"],
            })
        else:
            results["errors"].append({"index": i, "error": result.get("error", "未知错误")})

    return results


async def _call_api(config: AIConfig, prompt: str) -> dict:
    """调用图片生成 API"""
    api_url = f"{config.api_url.rstrip('/')}/v1/responses"
    payload = {
        "model": config.model or "gemini-3.0-pro",
        "input": [
            {
                "type": "message",
                "role": "user",
                "content": [{"type": "input_text", "text": prompt}]
            }
        ],
        "stream": False,
        "tool_choice": {"type": "image_generation"},
        "tools": [{"type": "image_generation"}]
    }

    try:
        async with httpx.AsyncClient(timeout=300.0) as client:
            response = await client.post(
                api_url,
                json=payload,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {config.api_key}"
                }
            )
            if response.status_code != 200:
                return {"error": f"HTTP {response.status_code}: {response.text[:500]}"}
            return response.json()
    except httpx.TimeoutException:
        return {"error": "请求超时（300秒）"}
    except httpx.ConnectError:
        return {"error": f"无法连接到服务器 {config.api_url}"}
    except Exception as e:
        return {"error": str(e)}


def _extract_image_data(response: dict) -> Tuple[str | None, str]:
    """从响应中提取 base64 图片数据"""
    # 格式1: output 数组
    if "output" in response:
        for item in response.get("output", []):
            if item.get("type") == "image_generation_call":
                if item.get("status") == "completed" and item.get("result"):
                    return (item["result"], item.get("output_format", "png"))

    # 格式2: data 数组 (OpenAI DALL-E 格式)
    if "data" in response:
        data = response["data"]
        if isinstance(data, list) and len(data) > 0:
            b64 = data[0].get("b64_json", "")
            if b64:
                return (b64, "png")

    return (None, "png")


def _save_image(
    base64_data: str,
    article_id: str,
    index: int,
    img_format: str = "png",
) -> Tuple[str, str]:
    """
    保存 base64 图片到文件

    Returns:
        Tuple[str, str]: (文件绝对路径, 访问URL)
    """
    # 创建文章专属目录
    article_dir = IMAGES_DIR / article_id
    article_dir.mkdir(parents=True, exist_ok=True)

    # 生成文件名
    filename = f"{index}_{uuid.uuid4().hex[:8]}.{img_format}"
    file_path = article_dir / filename

    # 清理 base64 前缀
    if "base64," in base64_data:
        base64_data = base64_data.split("base64,")[1]

    # 写入文件
    img_bytes = base64.b64decode(base64_data)
    with open(file_path, "wb") as f:
        f.write(img_bytes)

    # 返回路径和 URL
    url = f"/static/images/{article_id}/{filename}"
    return str(file_path.absolute()), url
