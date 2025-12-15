import asyncio
import os
from typing import Optional, List
from datetime import datetime
from playwright.async_api import async_playwright, Browser, Page
import structlog

from app.core.config import settings
from app.core.exceptions import PublishException

logger = structlog.get_logger()


class PublisherService:
    """头条发布服务"""

    PLATFORM_URLS = {
        "头条号": "https://mp.toutiao.com/profile_v4/graphic/publish",
        "百家号": "https://baijiahao.baidu.com/builder/rc/edit?type=news",
    }

    def __init__(self):
        self.browser: Optional[Browser] = None

    async def _get_browser(self) -> Browser:
        """获取浏览器实例"""
        if self.browser is None:
            playwright = await async_playwright().start()
            self.browser = await playwright.chromium.launch(
                headless=True,
                args=[
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-dev-shm-usage",
                ]
            )
        return self.browser

    async def _inject_cookies(self, page: Page, cookies: List[dict]) -> None:
        """注入Cookie"""
        for cookie in cookies:
            await page.context.add_cookies([cookie])

    async def publish_to_toutiao(
        self,
        title: str,
        content: str,
        cookies: List[dict],
        images: Optional[List[str]] = None,
    ) -> dict:
        """
        发布到头条号
        返回: {"success": bool, "url": str, "message": str}
        """
        browser = await self._get_browser()
        context = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )
        page = await context.new_page()

        try:
            # 注入Cookie
            await self._inject_cookies(page, cookies)

            # 访问发布页面
            await page.goto(self.PLATFORM_URLS["头条号"], wait_until="networkidle")
            await asyncio.sleep(3)

            # 检查登录状态
            if "login" in page.url.lower():
                raise PublishException("Cookie已过期，请重新登录")

            # 填写标题
            title_input = page.locator('textarea[placeholder*="标题"]').first
            await title_input.fill(title)
            await asyncio.sleep(1)

            # 填写正文
            editor = page.locator('[contenteditable="true"]').first
            await editor.click()

            # 使用keyboard.insert_text绕过剪贴板
            paragraphs = content.split("\n")
            for i, para in enumerate(paragraphs):
                if para.strip():
                    await page.keyboard.insert_text(para)
                    if i < len(paragraphs) - 1:
                        await page.keyboard.press("Enter")
                        await asyncio.sleep(0.1)

            await asyncio.sleep(2)

            # 上传图片 (如果有)
            if images:
                for img_path in images[:3]:  # 最多3张
                    if os.path.exists(img_path):
                        file_input = page.locator('input[type="file"]').first
                        await file_input.set_input_files(img_path)
                        await asyncio.sleep(2)

            # 勾选必要选项
            # 个人观点
            try:
                personal_opinion = page.locator('text=个人观点，仅供参考')
                if await personal_opinion.count() > 0:
                    await personal_opinion.click()
            except Exception:
                pass

            # 点击发布
            publish_btn = page.locator('button:has-text("发布")').first
            await publish_btn.click()
            await asyncio.sleep(5)

            # 检查发布结果
            if "success" in page.url.lower() or await page.locator('text=发布成功').count() > 0:
                logger.info("publish_success", platform="头条号", title=title[:30])
                return {
                    "success": True,
                    "url": page.url,
                    "message": "发布成功"
                }
            else:
                raise PublishException("发布失败，请检查内容")

        except PublishException:
            raise
        except Exception as e:
            logger.error("publish_error", error=str(e), platform="头条号")
            raise PublishException(f"发布过程出错: {str(e)}")
        finally:
            await context.close()

    async def check_account_status(self, cookies: List[dict], platform: str = "头条号") -> dict:
        """检查账号状态"""
        browser = await self._get_browser()
        context = await browser.new_context()
        page = await context.new_page()

        try:
            await self._inject_cookies(page, cookies)
            await page.goto(self.PLATFORM_URLS.get(platform, self.PLATFORM_URLS["头条号"]))
            await asyncio.sleep(3)

            if "login" in page.url.lower():
                return {"valid": False, "message": "Cookie已过期"}

            return {"valid": True, "message": "账号状态正常"}

        except Exception as e:
            return {"valid": False, "message": str(e)}
        finally:
            await context.close()

    async def close(self):
        """关闭浏览器"""
        if self.browser:
            await self.browser.close()
            self.browser = None


publisher = PublisherService()
