import asyncio
import os
from typing import Optional, List
from datetime import datetime
from playwright.async_api import async_playwright, Browser, Page, Playwright
import structlog
import httpx

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
        self.playwright: Optional[Playwright] = None

    async def _get_browser(self) -> Browser:
        """获取浏览器实例"""
        if self.browser is None:
            if self.playwright is None:
                self.playwright = await async_playwright().start()
            self.browser = await self.playwright.chromium.launch(
                headless=True,
                args=[
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-dev-shm-usage",
                ]
            )
        return self.browser

    async def _inject_cookies(self, context, cookies: List[dict]) -> None:
        """注入Cookie到浏览器上下文"""
        if cookies:
            await context.add_cookies(cookies)

    async def publish_to_toutiao_via_docx(
        self,
        docx_path: str,
        cookies: List[dict],
    ) -> dict:
        """
        通过 DOCX 文件导入方式发布到头条号

        Args:
            docx_path: DOCX 文件的完整路径（DOCX 中的一级标题会被自动识别）
            cookies: 登录 Cookie

        Returns:
            {"success": bool, "url": str, "message": str}
        """
        browser = await self._get_browser()
        context = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )
        page = await context.new_page()

        try:
            # 注入Cookie
            await self._inject_cookies(context, cookies)

            # 访问发布页面
            await page.goto(self.PLATFORM_URLS["头条号"], wait_until="networkidle")
            await asyncio.sleep(3)

            # 检查登录状态
            if "login" in page.url.lower():
                raise PublishException("Cookie已过期，请重新登录")

            logger.info("publish_start", method="docx_import", file=docx_path)

            # 查找并点击"导入文档"图标按钮
            # 使用 doc-import 类名精确定位
            try:
                # 等待导入按钮出现
                import_btn_selectors = [
                    '.doc-import button',
                    '.doc-import .syl-toolbar-button',
                    '.syl-toolbar-tool.doc-import button',
                ]

                import_btn_clicked = False
                for selector in import_btn_selectors:
                    try:
                        await page.wait_for_selector(selector, timeout=5000)
                        logger.info("import_button_found", selector=selector)

                        # 使用 JavaScript 点击（更可靠）
                        await page.evaluate(f"""() => {{
                            const btn = document.querySelector('{selector}');
                            if (btn) {{
                                btn.click();
                                return true;
                            }}
                            return false;
                        }}""")

                        logger.info("import_button_clicked", selector=selector)
                        import_btn_clicked = True
                        await asyncio.sleep(3)
                        break
                    except Exception as e:
                        logger.debug("selector_failed", selector=selector, error=str(e))
                        continue

                if not import_btn_clicked:
                    raise PublishException("未找到导入文档按钮")

            except Exception as e:
                logger.error("import_button_click_failed", error=str(e))
                raise PublishException(f"点击导入按钮失败: {str(e)}")

            # 查找文件上传输入框
            # 点击导入按钮后，需要等待文件输入框出现
            logger.info("waiting_for_file_input")
            await asyncio.sleep(2)  # 给弹窗/对话框时间加载

            file_input_selectors = [
                'input[type="file"]',  # 最宽松的选择器
                'input[type="file"][accept*="docx"]',
                'input[type="file"][accept*="word"]',
                'input[type="file"][accept*=".doc"]',
            ]

            file_uploaded = False
            for selector in file_input_selectors:
                try:
                    # 等待输入框出现
                    await page.wait_for_selector(selector, timeout=5000, state='attached')

                    file_inputs = await page.locator(selector).all()
                    logger.info("file_input_found", selector=selector, count=len(file_inputs))

                    if file_inputs:
                        # 尝试每个文件输入框
                        for i, file_input in enumerate(file_inputs):
                            try:
                                logger.info("trying_file_input", index=i)
                                await file_input.set_input_files(docx_path)
                                logger.info("file_set_success", index=i, file=docx_path)
                                file_uploaded = True
                                await asyncio.sleep(5)  # 等待文件上传和解析
                                break
                            except Exception as e:
                                logger.debug("file_input_set_failed", index=i, error=str(e))
                                continue

                        if file_uploaded:
                            break

                except Exception as e:
                    logger.debug("file_input_selector_failed", selector=selector, error=str(e))
                    continue

            if not file_uploaded:
                # 尝试截图帮助调试
                try:
                    screenshot_path = f"upload_failed_{datetime.now().strftime('%H%M%S')}.png"
                    await page.screenshot(path=screenshot_path)
                    logger.error("file_upload_failed_screenshot", path=screenshot_path)
                except:
                    pass
                raise PublishException("文件上传失败")

            logger.info("docx_uploaded", file=docx_path)

            # 等待内容加载
            await asyncio.sleep(5)

            # 检查是否有确认按钮
            confirm_selectors = [
                'button:has-text("确认")',
                'button:has-text("确定")',
                'button:has-text("导入")',
            ]

            for selector in confirm_selectors:
                try:
                    if await page.locator(selector).count() > 0:
                        await page.locator(selector).first.click()
                        await asyncio.sleep(2)
                        break
                except:
                    continue

            # 等待内容填充完成
            await asyncio.sleep(3)

            # 步骤1：点击"预览并发布"按钮
            publish_selectors = [
                'button:has-text("预览并发布")',
                'button:has-text("发布")',
                'button:has-text("立即发布")',
                '.publish-btn',
            ]

            publish_clicked = False
            for selector in publish_selectors:
                try:
                    if await page.locator(selector).count() > 0:
                        logger.info("preview_publish_button_found", selector=selector)
                        await page.locator(selector).first.click()
                        publish_clicked = True
                        await asyncio.sleep(3)  # 等待确认对话框出现
                        break
                except:
                    continue

            if not publish_clicked:
                raise PublishException("未找到预览并发布按钮")

            # 步骤2：在确认对话框中点击"确认发布"按钮
            logger.info("waiting_for_confirm_dialog")
            await asyncio.sleep(2)

            confirm_selectors = [
                'button:has-text("确认发布")',
                'button:has-text("确认")',
                'button:has-text("发布")',
                '[role="dialog"] button:has-text("确认")',
                '.dialog button:has-text("确认")',
            ]

            confirm_clicked = False
            for selector in confirm_selectors:
                try:
                    if await page.locator(selector).count() > 0:
                        logger.info("confirm_button_found", selector=selector)
                        await page.locator(selector).first.click()
                        confirm_clicked = True
                        logger.info("confirm_button_clicked")
                        await asyncio.sleep(3)
                        break
                except Exception as e:
                    logger.debug("confirm_selector_failed", selector=selector, error=str(e))
                    continue

            if not confirm_clicked:
                logger.warning("confirm_button_not_found_maybe_no_dialog")
                # 有可能不需要确认对话框，继续执行

            # 检查发布结果
            # 发布可能需要较长时间（审核、上传、跳转等）
            logger.info("waiting_for_publish_result")
            await asyncio.sleep(10)  # 增加到 10 秒，等待发布和页面跳转

            final_url = page.url
            logger.info("checking_publish_result", url=final_url)

            # 判断是否发布成功的多个指标
            success_indicators = [
                "success" in final_url.lower(),
                "content" in final_url.lower() and "publish" not in final_url.lower(),  # 跳转到内容列表页
                await page.locator('text=发布成功').count() > 0,
                await page.locator('text=已发布').count() > 0,
                await page.locator('text=发布中').count() > 0,  # 正在发布也算成功
                await page.locator('text=审核中').count() > 0,  # 审核中也算成功
            ]

            # 检查是否还在发布页面（可能表示有错误）
            still_on_publish_page = "publish" in final_url.lower()
            has_error_message = await page.locator('[class*="error"]').count() > 0

            # 检查是否有成功提示（即使还在发布页面）
            has_success_toast = await page.locator('[class*="toast"]').locator('text=成功').count() > 0
            has_success_message = await page.locator('[class*="success"]').count() > 0

            if any(success_indicators) and not has_error_message:
                logger.info("publish_success_docx", platform="头条号", url=final_url)
                return {
                    "success": True,
                    "url": final_url,
                    "message": "发布成功"
                }
            elif (still_on_publish_page and not has_error_message) or has_success_toast or has_success_message:
                # 仍在发布页面但：
                # 1. 没有错误消息
                # 2. 或有成功提示
                # 这说明发布可能成功但页面未跳转
                logger.info("publish_likely_success", url=final_url, has_success_toast=has_success_toast)
                return {
                    "success": True,
                    "url": final_url,
                    "message": "发布成功（文章已提交）"
                }
            else:
                # 尝试截图保存错误状态
                try:
                    screenshot_path = f"publish_error_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                    await page.screenshot(path=screenshot_path, full_page=True)
                    logger.error("publish_failed_screenshot", path=screenshot_path)
                except:
                    pass

                raise PublishException("发布失败，请检查内容或手动确认")

        except PublishException:
            raise
        except Exception as e:
            logger.error("publish_error_docx", error=str(e), platform="头条号")
            raise PublishException(f"发布过程出错: {str(e)}")
        finally:
            await context.close()

    async def publish_to_toutiao(
        self,
        title: str,
        content: str,
        cookies: List[dict],
        images: Optional[List[str]] = None,
        docx_path: Optional[str] = None,
    ) -> dict:
        """
        发布到头条号

        如果提供了 docx_path，使用文档导入方式（推荐）
        否则使用传统的表单填写方式

        返回: {"success": bool, "url": str, "message": str}
        """
        # 如果提供了 DOCX 文件，使用文档导入方式
        if docx_path and os.path.exists(docx_path):
            logger.info("using_docx_import_method", docx_path=docx_path)
            return await self.publish_to_toutiao_via_docx(docx_path, cookies)

        # 否则使用传统方式
        logger.info("using_traditional_form_method")
        browser = await self._get_browser()
        context = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )
        page = await context.new_page()

        try:
            # 注入Cookie
            await self._inject_cookies(context, cookies)

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
        """
        检查账号状态（使用 HTTP 请求，避免 Playwright 在 Windows 上的兼容问题）
        """
        try:
            # 将 cookie 列表转换为 httpx 可用的格式
            cookie_dict = {}
            for c in cookies:
                name = c.get("name")
                value = c.get("value")
                if name and value:
                    cookie_dict[name] = value

            # 头条号 API 检查地址（用户信息接口）
            check_urls = {
                "头条号": "https://mp.toutiao.com/profile_v4/index/info",
                "百家号": "https://baijiahao.baidu.com/builder/app/appinfo",
            }

            check_url = check_urls.get(platform, check_urls["头条号"])

            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "application/json, text/plain, */*",
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
                "Referer": self.PLATFORM_URLS.get(platform, self.PLATFORM_URLS["头条号"]),
            }

            async with httpx.AsyncClient(
                cookies=cookie_dict,
                headers=headers,
                follow_redirects=False,
                timeout=30.0
            ) as client:
                response = await client.get(check_url)

                logger.info(
                    "check_account_response",
                    platform=platform,
                    status_code=response.status_code,
                    url=str(response.url)
                )

                # 检查是否被重定向到登录页
                if response.status_code in (301, 302, 303, 307, 308):
                    location = response.headers.get("location", "")
                    if "login" in location.lower() or "passport" in location.lower():
                        return {"valid": False, "message": "Cookie已过期，请重新登录"}

                # 检查响应状态
                if response.status_code == 200:
                    try:
                        data = response.json()
                        # 头条号返回的数据格式检查
                        if platform == "头条号":
                            # 检查是否有用户信息
                            if data.get("data") or data.get("user_id") or data.get("screen_name"):
                                return {"valid": True, "message": "账号状态正常"}
                            # 检查是否有错误码表示未登录
                            if data.get("err_no") or data.get("error_code"):
                                return {"valid": False, "message": "Cookie已过期"}
                        # 默认 200 状态认为有效
                        return {"valid": True, "message": "账号状态正常"}
                    except Exception:
                        # 无法解析 JSON，但状态码 200，可能是 HTML 页面
                        text = response.text
                        if "login" in text.lower() or "登录" in text:
                            return {"valid": False, "message": "Cookie已过期"}
                        return {"valid": True, "message": "账号状态正常"}

                elif response.status_code == 401 or response.status_code == 403:
                    return {"valid": False, "message": "Cookie已过期或无权限"}

                else:
                    return {"valid": False, "message": f"检查失败，状态码: {response.status_code}"}

        except httpx.TimeoutException:
            return {"valid": False, "message": "请求超时，请检查网络连接"}
        except Exception as e:
            logger.error("check_account_error", error=str(e), platform=platform)
            return {"valid": False, "message": f"检查失败: {str(e)}"}

    async def close(self):
        """关闭浏览器"""
        if self.browser:
            await self.browser.close()
            self.browser = None
        if self.playwright:
            await self.playwright.stop()
            self.playwright = None


publisher = PublisherService()
