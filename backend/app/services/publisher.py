"""
发布服务 - 使用同步 Playwright 在线程中运行（解决 Windows + uvicorn 兼容问题）
"""
import asyncio
import os
from typing import Optional, List
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from playwright.sync_api import sync_playwright, Browser, Page
import structlog
import httpx

from app.core.config import settings
from app.core.exceptions import PublishException

logger = structlog.get_logger()

# 线程池用于运行同步 Playwright
_executor = ThreadPoolExecutor(max_workers=2)


class PublisherService:
    """头条发布服务（使用同步 API 在线程中运行）"""

    PLATFORM_URLS = {
        "头条号": "https://mp.toutiao.com/profile_v4/graphic/publish",
        "百家号": "https://baijiahao.baidu.com/builder/rc/edit?type=news",
    }

    def _normalize_cookies(self, cookies: List[dict]) -> List[dict]:
        """规范化 Cookie 格式"""
        normalized = []
        for c in cookies:
            cookie = {
                "name": c.get("name"),
                "value": c.get("value"),
                "domain": c.get("domain", ""),
                "path": c.get("path", "/"),
            }
            # 规范化 sameSite
            same_site = c.get("sameSite") or ""
            if isinstance(same_site, str):
                same_site = same_site.capitalize()
            if same_site in ("Strict", "Lax", "None"):
                cookie["sameSite"] = same_site
            else:
                cookie["sameSite"] = "Lax"  # 默认值

            # 只添加有效的 cookie
            if cookie["name"] and cookie["value"]:
                normalized.append(cookie)
        return normalized

    def _run_sync_publish(
        self,
        docx_path: str,
        cookies: List[dict],
        headless: bool = True,
    ) -> dict:
        """同步发布方法（在线程中运行）"""
        import time

        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=headless,
                args=[
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-dev-shm-usage",
                ]
            )
            context = browser.new_context(
                viewport={"width": 1920, "height": 1080},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            )
            page = context.new_page()

            try:
                # 注入 Cookie
                if cookies:
                    context.add_cookies(self._normalize_cookies(cookies))

                # 访问发布页面
                page.goto(self.PLATFORM_URLS["头条号"], wait_until="networkidle")
                time.sleep(3)

                # 检查登录状态
                if "login" in page.url.lower():
                    raise PublishException("Cookie已过期，请重新登录")

                logger.info("publish_start", method="docx_import", file=docx_path)

                # 查找并点击"导入文档"按钮
                import_btn_selectors = [
                    '.doc-import button',
                    '.doc-import .syl-toolbar-button',
                    '.syl-toolbar-tool.doc-import button',
                ]

                import_btn_clicked = False
                for selector in import_btn_selectors:
                    try:
                        page.wait_for_selector(selector, timeout=5000)
                        page.evaluate(f"""() => {{
                            const btn = document.querySelector('{selector}');
                            if (btn) {{ btn.click(); return true; }}
                            return false;
                        }}""")
                        import_btn_clicked = True
                        time.sleep(3)
                        break
                    except:
                        continue

                if not import_btn_clicked:
                    raise PublishException("未找到导入文档按钮")

                # 上传文件
                time.sleep(2)
                file_input_selectors = [
                    'input[type="file"]',
                    'input[type="file"][accept*="docx"]',
                ]

                file_uploaded = False
                for selector in file_input_selectors:
                    try:
                        page.wait_for_selector(selector, timeout=5000, state='attached')
                        file_inputs = page.locator(selector).all()
                        for file_input in file_inputs:
                            try:
                                file_input.set_input_files(docx_path)
                                file_uploaded = True
                                time.sleep(5)
                                break
                            except:
                                continue
                        if file_uploaded:
                            break
                    except:
                        continue

                if not file_uploaded:
                    raise PublishException("文件上传失败")

                logger.info("docx_uploaded", file=docx_path)
                time.sleep(5)

                # 检查确认按钮
                for selector in ['button:has-text("确认")', 'button:has-text("确定")', 'button:has-text("导入")']:
                    try:
                        if page.locator(selector).count() > 0:
                            page.locator(selector).first.click()
                            time.sleep(2)
                            break
                    except:
                        continue

                time.sleep(3)

                # 点击"预览并发布"
                publish_selectors = [
                    'button:has-text("预览并发布")',
                    'button:has-text("发布")',
                    'button:has-text("立即发布")',
                ]

                publish_clicked = False
                for selector in publish_selectors:
                    try:
                        if page.locator(selector).count() > 0:
                            page.locator(selector).first.click()
                            publish_clicked = True
                            time.sleep(3)
                            break
                    except:
                        continue

                if not publish_clicked:
                    raise PublishException("未找到发布按钮")

                # 确认发布
                time.sleep(2)
                for selector in ['button:has-text("确认发布")', 'button:has-text("确认")']:
                    try:
                        if page.locator(selector).count() > 0:
                            page.locator(selector).first.click()
                            break
                    except:
                        continue

                # 立即轮询检查 toast 消息（显示时间很短）
                success_detected = False
                for _ in range(20):  # 最多检查10秒
                    time.sleep(0.5)
                    # 检查 toast 提示
                    toast_texts = ['提交成功', '发布成功', '已发布', '审核中']
                    for text in toast_texts:
                        try:
                            if page.locator(f'text={text}').count() > 0:
                                success_detected = True
                                logger.info("publish_success_toast", text=text)
                                break
                        except:
                            pass
                    if success_detected:
                        break
                    # 检查 URL 变化
                    current_url = page.url
                    if "success" in current_url.lower() or ("content" in current_url.lower() and "publish" not in current_url.lower()):
                        success_detected = True
                        logger.info("publish_success_url", url=current_url)
                        break

                final_url = page.url

                if success_detected:
                    return {"success": True, "url": final_url, "message": "发布成功"}
                else:
                    raise PublishException("发布失败，未检测到成功提示")

            except PublishException:
                raise
            except Exception as e:
                logger.error("publish_error", error=str(e))
                raise PublishException(f"发布过程出错: {str(e)}")
            finally:
                context.close()
                browser.close()

    def _run_sync_publish_form(
        self,
        title: str,
        content: str,
        cookies: List[dict],
        images: Optional[List[str]] = None,
        headless: bool = True,
    ) -> dict:
        """同步表单发布（在线程中运行）"""
        import time

        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=headless,
                args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage"]
            )
            context = browser.new_context(
                viewport={"width": 1920, "height": 1080},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            )
            page = context.new_page()

            try:
                if cookies:
                    context.add_cookies(self._normalize_cookies(cookies))

                page.goto(self.PLATFORM_URLS["头条号"], wait_until="networkidle")
                time.sleep(3)

                if "login" in page.url.lower():
                    raise PublishException("Cookie已过期，请重新登录")

                # 填写标题
                title_input = page.locator('textarea[placeholder*="标题"]').first
                title_input.fill(title)
                time.sleep(1)

                # 填写正文
                editor = page.locator('[contenteditable="true"]').first
                editor.click()
                for i, para in enumerate(content.split("\n")):
                    if para.strip():
                        page.keyboard.insert_text(para)
                        if i < len(content.split("\n")) - 1:
                            page.keyboard.press("Enter")
                            time.sleep(0.1)

                time.sleep(2)

                # 上传图片
                if images:
                    for img_path in images[:3]:
                        if os.path.exists(img_path):
                            file_input = page.locator('input[type="file"]').first
                            file_input.set_input_files(img_path)
                            time.sleep(2)

                # 点击发布
                page.locator('button:has-text("发布")').first.click()

                # 立即轮询检查 toast 消息
                success_detected = False
                for _ in range(20):  # 最多检查10秒
                    time.sleep(0.5)
                    toast_texts = ['提交成功', '发布成功', '已发布', '审核中']
                    for text in toast_texts:
                        try:
                            if page.locator(f'text={text}').count() > 0:
                                success_detected = True
                                break
                        except:
                            pass
                    if success_detected:
                        break
                    if "success" in page.url.lower():
                        success_detected = True
                        break

                if success_detected:
                    return {"success": True, "url": page.url, "message": "发布成功"}
                else:
                    raise PublishException("发布失败，未检测到成功提示")

            except PublishException:
                raise
            except Exception as e:
                raise PublishException(f"发布出错: {str(e)}")
            finally:
                context.close()
                browser.close()

    async def publish_to_toutiao_via_docx(
        self,
        docx_path: str,
        cookies: List[dict],
    ) -> dict:
        """通过 DOCX 发布（异步包装）"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            _executor,
            self._run_sync_publish,
            docx_path,
            cookies,
            False,  # headless
        )

    async def publish_to_toutiao(
        self,
        title: str,
        content: str,
        cookies: List[dict],
        images: Optional[List[str]] = None,
        docx_path: Optional[str] = None,
    ) -> dict:
        """发布到头条号"""
        if docx_path and os.path.exists(docx_path):
            return await self.publish_to_toutiao_via_docx(docx_path, cookies)

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            _executor,
            self._run_sync_publish_form,
            title,
            content,
            cookies,
            images,
            False,  # headless
        )

    async def check_account_status(self, cookies: List[dict], platform: str = "头条号") -> dict:
        """检查账号状态（使用 HTTP 请求）"""
        try:
            cookie_dict = {c.get("name"): c.get("value") for c in cookies if c.get("name") and c.get("value")}

            check_urls = {
                "头条号": "https://mp.toutiao.com/profile_v4/index/info",
                "百家号": "https://baijiahao.baidu.com/builder/app/appinfo",
            }

            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept": "application/json, text/plain, */*",
                "Referer": self.PLATFORM_URLS.get(platform, self.PLATFORM_URLS["头条号"]),
            }

            async with httpx.AsyncClient(cookies=cookie_dict, headers=headers, follow_redirects=False, timeout=30.0) as client:
                response = await client.get(check_urls.get(platform, check_urls["头条号"]))

                if response.status_code in (301, 302, 303, 307, 308):
                    location = response.headers.get("location", "")
                    if "login" in location.lower():
                        return {"valid": False, "message": "Cookie已过期"}

                if response.status_code == 200:
                    try:
                        data = response.json()
                        if data.get("data") or data.get("user_id"):
                            return {"valid": True, "message": "账号状态正常"}
                        if data.get("err_no"):
                            return {"valid": False, "message": "Cookie已过期"}
                    except:
                        pass
                    return {"valid": True, "message": "账号状态正常"}

                return {"valid": False, "message": f"状态码: {response.status_code}"}

        except Exception as e:
            return {"valid": False, "message": f"检查失败: {str(e)}"}

    async def close(self):
        """关闭资源"""
        pass  # 同步 API 每次都会自动关闭


publisher = PublisherService()
