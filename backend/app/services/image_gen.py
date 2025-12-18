from typing import List, Tuple
import structlog
import httpx
import base64
from pathlib import Path
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.ai_config import AIConfig, AIConfigType

logger = structlog.get_logger()


async def _get_image_config(db: AsyncSession) -> AIConfig:
    """从数据库获取图片生成配置"""
    result = await db.execute(select(AIConfig).where(AIConfig.type == AIConfigType.IMAGE_GENERATE.value))
    config = result.scalar_one_or_none()
    if not config or not config.api_url:
        return None
    return config


async def generate_image(db: AsyncSession, prompt: str) -> str:
    """
    生成单张图片
    返回图片本地路径，失败返回空字符串
    """
    config = await _get_image_config(db)
    if not config:
        logger.info("image_gen_skipped_no_config", prompt=prompt[:50])
        return ""

    try:
        logger.info("image_gen_start", prompt=prompt[:100], model=config.model)

        response_data = await _call_api(config, prompt)

        if response_data.get("error"):
            logger.error("image_gen_failed", error=response_data["error"])
            return ""

        base64_data, img_format = _extract_image_data(response_data)
        if not base64_data:
            logger.error("image_extract_failed", response_keys=list(response_data.keys()))
            return ""

        saved_path = _save_image(base64_data, img_format)
        logger.info("image_gen_success", path=saved_path)
        return saved_path

    except Exception as e:
        logger.error("image_gen_exception", error=str(e), prompt=prompt[:50])
        return ""


async def generate_images(db: AsyncSession, prompts: List[str]) -> List[str]:
    """批量生成图片"""
    results = []
    for prompt in prompts:
        path = await generate_image(db, prompt)
        if path:
            results.append(path)
    return results


async def _call_api(config: AIConfig, prompt: str) -> dict:
    """调用图片生成 API"""
    api_url = f"{config.api_url}/v1/responses"
    payload = {
        "model": config.model or "gemini-3.0-pro",
        "input": [{"type": "message", "role": "user", "content": [{"type": "input_text", "text": prompt}]}],
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
        return {"error": "请求超时"}
    except httpx.ConnectError:
        return {"error": f"无法连接到服务器 {config.api_url}"}
    except Exception as e:
        return {"error": str(e)}


def _extract_image_data(response: dict) -> Tuple[str | None, str]:
    """从响应中提取 base64 图片数据"""
    if "output" in response:
        for item in response.get("output", []):
            if item.get("type") == "image_generation_call":
                if item.get("status") == "completed" and item.get("result"):
                    return (item["result"], item.get("output_format", "png"))

    if "data" in response:
        data = response["data"]
        if isinstance(data, list) and len(data) > 0:
            b64 = data[0].get("b64_json", "")
            if b64:
                return (b64, "png")

    return (None, "png")


def _save_image(base64_data: str, img_format: str = "png") -> str:
    """保存 base64 图片到文件"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = f"generated_{timestamp}.{img_format}"

    if "base64," in base64_data:
        base64_data = base64_data.split("base64,")[1]

    img_bytes = base64.b64decode(base64_data)
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, "wb") as f:
        f.write(img_bytes)

    return str(output_file.absolute())
