from typing import Optional, List, Tuple
from abc import ABC, abstractmethod
import structlog
import httpx
import base64
from pathlib import Path
from datetime import datetime

from app.core.config import settings

logger = structlog.get_logger()


class ImageGeneratorBase(ABC):
    """图片生成器基类"""

    @abstractmethod
    async def generate(self, prompt: str, **kwargs) -> str:
        """生成图片，返回图片URL或路径"""
        pass

    @abstractmethod
    async def test_connection(self) -> bool:
        """测试连接"""
        pass


class NoopImageGenerator(ImageGeneratorBase):
    """空实现，不生成图片"""

    async def generate(self, prompt: str, **kwargs) -> str:
        logger.info("image_gen_skipped", prompt=prompt[:50])
        return ""

    async def test_connection(self) -> bool:
        return True


class StableDiffusionGenerator(ImageGeneratorBase):
    """Stable Diffusion API 实现 (预留)"""

    def __init__(self, api_url: str, api_key: str):
        self.api_url = api_url
        self.api_key = api_key

    async def generate(self, prompt: str, **kwargs) -> str:
        # TODO: 实现 Stable Diffusion API 调用
        raise NotImplementedError("Stable Diffusion generator not implemented yet")

    async def test_connection(self) -> bool:
        # TODO: 实现连接测试
        return False


class DalleGenerator(ImageGeneratorBase):
    """DALL-E API 实现 (预留)"""

    def __init__(self, api_key: str):
        self.api_key = api_key

    async def generate(self, prompt: str, **kwargs) -> str:
        # TODO: 实现 DALL-E API 调用
        raise NotImplementedError("DALL-E generator not implemented yet")

    async def test_connection(self) -> bool:
        # TODO: 实现连接测试
        return False


class GeminiImageGenerator(ImageGeneratorBase):
    """Gemini 图片生成器"""

    def __init__(self, api_base: str, api_key: str):
        """
        初始化 Gemini 图片生成器

        Args:
            api_base: API 基础地址,如 http://116.205.244.106:9006
            api_key: API 密钥
        """
        self.api_base = api_base
        self.api_key = api_key
        self.api_url = f"{api_base}/v1/responses"
        self.timeout = 300.0  # 图片生成可能需要较长时间

    async def generate(self, prompt: str, **kwargs) -> str:
        """
        生成图片并返回本地保存路径

        Args:
            prompt: 图片描述文本
            **kwargs:
                - model: 使用的模型,默认 gemini-3.0-pro
                - save_path: 保存路径,默认自动生成

        Returns:
            生成的图片本地路径
        """
        model = kwargs.get("model", "gemini-3.0-pro")
        save_path = kwargs.get("save_path", None)

        try:
            logger.info("gemini_image_gen_start", prompt=prompt[:100], model=model)

            # 调用 API 生成图片
            response_data = await self._text_to_image(prompt, model)

            # 只有 error 存在且不为空/None 时才报错
            if response_data.get("error"):
                logger.error("gemini_image_gen_failed", error=response_data["error"])
                return ""

            # 提取 base64 图片数据
            base64_data, img_format = self._extract_image_data(response_data)

            if not base64_data:
                logger.error("gemini_image_extract_failed", response_keys=list(response_data.keys()))
                return ""

            # 保存图片
            saved_path = await self._save_image(base64_data, img_format, save_path)

            logger.info("gemini_image_gen_success", path=saved_path, size_kb=Path(saved_path).stat().st_size / 1024)
            return saved_path

        except Exception as e:
            logger.error("gemini_image_gen_exception", error=str(e), prompt=prompt[:50])
            return ""

    async def _text_to_image(self, prompt: str, model: str = "gemini-3.0-pro") -> dict:
        """
        纯文本生成图片(内部方法)

        Args:
            prompt: 图片描述文本
            model: 使用的模型

        Returns:
            API 响应字典
        """
        payload = {
            "model": model,
            "input": [
                {
                    "type": "message",
                    "role": "user",
                    "content": [
                        {
                            "type": "input_text",
                            "text": prompt
                        }
                    ]
                }
            ],
            "stream": False,
            "tool_choice": {
                "type": "image_generation"
            },
            "tools": [
                {
                    "type": "image_generation"
                }
            ]
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    self.api_url,
                    json=payload,
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": f"Bearer {self.api_key}"
                    }
                )

                if response.status_code != 200:
                    return {
                        "error": f"HTTP {response.status_code}: {response.text[:500]}"
                    }

                return response.json()

        except httpx.TimeoutException:
            return {"error": "请求超时,图片生成可能需要较长时间"}
        except httpx.ConnectError:
            return {"error": f"无法连接到服务器 {self.api_base}"}
        except Exception as e:
            return {"error": f"请求异常: {str(e)}"}

    def _extract_image_data(self, response: dict) -> Tuple[Optional[str], str]:
        """
        从响应中提取 base64 图片数据

        Returns:
            (base64_data, format) 如 ("iVBORw0...", "png")
        """
        # 格式: output[] 中查找 image_generation_call
        if "output" in response:
            for item in response.get("output", []):
                if item.get("type") == "image_generation_call":
                    if item.get("status") == "completed" and item.get("result"):
                        img_format = item.get("output_format", "png")
                        return (item["result"], img_format)

        # 备用: 查找其他可能的格式
        if "choices" in response:
            for choice in response.get("choices", []):
                content = choice.get("message", {}).get("content", "")
                if content and "base64" in content:
                    return (content, "png")

        if "data" in response:
            data = response["data"]
            if isinstance(data, list) and len(data) > 0:
                b64 = data[0].get("b64_json", "")
                if b64:
                    return (b64, "png")

        return (None, "png")

    async def _save_image(
        self,
        base64_data: str,
        img_format: str = "png",
        output_path: Optional[str] = None
    ) -> str:
        """
        保存 base64 图片数据到文件

        Args:
            base64_data: base64 编码的图片数据
            img_format: 图片格式 (png/jpg/webp)
            output_path: 输出路径,None 则自动生成

        Returns:
            保存的文件路径
        """
        # 生成输出文件名
        if output_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = f"generated_{timestamp}.{img_format}"

        # 处理可能带前缀的 base64
        if "base64," in base64_data:
            base64_data = base64_data.split("base64,")[1]

        # 解码并保存
        img_bytes = base64.b64decode(base64_data)

        # 确保目录存在
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        with open(output_file, "wb") as f:
            f.write(img_bytes)

        return str(output_file.absolute())

    async def test_connection(self) -> bool:
        """测试 API 连接"""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                # 简单的健康检查请求
                response = await client.get(
                    f"{self.api_base}/health",
                    headers={"Authorization": f"Bearer {self.api_key}"}
                )
                # 如果没有 health 端点,尝试调用主接口
                if response.status_code == 404:
                    test_result = await self._text_to_image("test", "gemini-3.0-pro")
                    return "error" not in test_result or "Timeout" not in test_result.get("error", "")

                return response.status_code == 200
        except Exception as e:
            logger.warning("gemini_connection_test_failed", error=str(e))
            return False


class ImageGeneratorService:
    """图片生成服务"""

    def __init__(self):
        self.generator = self._create_generator()

    def _create_generator(self) -> ImageGeneratorBase:
        """根据配置创建生成器"""
        provider = settings.IMAGE_GEN_PROVIDER.lower()

        if provider == "gemini":
            return GeminiImageGenerator(
                api_base=settings.IMAGE_GEN_API_URL,
                api_key=settings.IMAGE_GEN_API_KEY,
            )
        elif provider == "stable_diffusion":
            return StableDiffusionGenerator(
                api_url=settings.IMAGE_GEN_API_URL,
                api_key=settings.IMAGE_GEN_API_KEY,
            )
        elif provider == "dalle":
            return DalleGenerator(api_key=settings.IMAGE_GEN_API_KEY)
        else:
            logger.info("image_gen_disabled", provider=provider)
            return NoopImageGenerator()

    async def generate_images(self, prompts: List[str]) -> List[str]:
        """批量生成图片"""
        results = []
        for prompt in prompts:
            try:
                url = await self.generator.generate(prompt)
                if url:
                    results.append(url)
            except Exception as e:
                logger.error("image_gen_error", prompt=prompt[:50], error=str(e))
        return results

    async def test_connection(self) -> bool:
        """测试连接"""
        return await self.generator.test_connection()


image_generator = ImageGeneratorService()
