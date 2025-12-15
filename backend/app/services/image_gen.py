from typing import Optional, List
from abc import ABC, abstractmethod
import structlog

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


class ImageGeneratorService:
    """图片生成服务"""

    def __init__(self):
        self.generator = self._create_generator()

    def _create_generator(self) -> ImageGeneratorBase:
        """根据配置创建生成器"""
        provider = settings.IMAGE_GEN_PROVIDER.lower()

        if provider == "stable_diffusion":
            return StableDiffusionGenerator(
                api_url=settings.IMAGE_GEN_API_URL,
                api_key=settings.IMAGE_GEN_API_KEY,
            )
        elif provider == "dalle":
            return DalleGenerator(api_key=settings.IMAGE_GEN_API_KEY)
        else:
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
