"""
发布服务 - 使用同步 Patchright 在线程中运行（反检测版 Playwright）
"""
import asyncio
import os
from typing import Optional, List
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from patchright.sync_api import sync_playwright, Browser, Page
import structlog
import httpx

from app.core.config import settings
from app.core.exceptions import PublishException

logger = structlog.get_logger()

# 线程池用于运行同步 Patchright
_executor = ThreadPoolExecutor(max_workers=2)


def _parse_headless(value: str) -> str | bool:
    """解析 headless 配置值"""
    if value == "new":
        return "new"
    elif value == "true":
        return True
    elif value == "false":
        return False
    return "new"  # 默认新版无头模式


class PublisherService:
    """头条发布服务（使用 Patchright 反检测浏览器）"""

    # 发布页面 URL
    ARTICLE_PUBLISH_URL = "https://mp.toutiao.com/profile_v4/graphic/publish"
    WEITOUTIAO_PUBLISH_URL = "https://mp.toutiao.com/profile_v4/weitoutiao/publish?from=toutiao_pc"

    def _take_screenshot(self, page: Page, name: str) -> Optional[str]:
        """截图并保存，返回截图路径"""
        if not settings.BROWSER_SCREENSHOT_ON_ERROR:
            return None
        try:
            os.makedirs(settings.BROWSER_SCREENSHOT_DIR, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{name}_{timestamp}.png"
            filepath = os.path.join(settings.BROWSER_SCREENSHOT_DIR, filename)
            page.screenshot(path=filepath, full_page=True)
            logger.info("screenshot_saved", path=filepath)
            return filepath
        except Exception as e:
            logger.warning("screenshot_failed", error=str(e))
            return None

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
    ) -> dict:
        """同步发布方法（在线程中运行）"""
        import time

        headless = _parse_headless(settings.BROWSER_HEADLESS)
        logger.info(
            "browser_launch_start",
            method="docx_import",
            headless=settings.BROWSER_HEADLESS,
            slow_mo=settings.BROWSER_SLOW_MO,
            timeout=settings.BROWSER_TIMEOUT,
        )

        with sync_playwright() as p:
            browser = p.chromium.launch(
                channel="chrome",
                headless=headless,
                slow_mo=settings.BROWSER_SLOW_MO,
                args=[
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-blink-features=AutomationControlled",
                    "--disable-infobars",
                ]
            )
            context = browser.new_context(
                viewport={
                    "width": settings.BROWSER_VIEWPORT_WIDTH,
                    "height": settings.BROWSER_VIEWPORT_HEIGHT,
                },
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                locale="zh-CN",
                timezone_id="Asia/Shanghai",
            )
            context.set_default_timeout(settings.BROWSER_TIMEOUT)
            # 移除 webdriver 标记
            context.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            """)
            page = context.new_page()

            try:
                # 注入 Cookie
                if cookies:
                    normalized_cookies = self._normalize_cookies(cookies)
                    logger.info("cookies_inject", count=len(normalized_cookies))
                    context.add_cookies(normalized_cookies)

                # 访问发布页面
                logger.info("navigate_to_publish_page", url=self.ARTICLE_PUBLISH_URL)
                page.goto(self.ARTICLE_PUBLISH_URL, wait_until="networkidle")
                time.sleep(3)

                # 检查登录状态
                current_url = page.url
                logger.info("page_loaded", url=current_url)
                if "login" in current_url.lower():
                    self._take_screenshot(page, "login_required")
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
                        logger.debug("try_selector", selector=selector, action="import_btn")
                        page.wait_for_selector(selector, timeout=5000)
                        page.evaluate(f"""() => {{
                            const btn = document.querySelector('{selector}');
                            if (btn) {{ btn.click(); return true; }}
                            return false;
                        }}""")
                        import_btn_clicked = True
                        logger.info("import_btn_clicked", selector=selector)
                        time.sleep(3)
                        break
                    except Exception as e:
                        logger.debug("selector_not_found", selector=selector, error=str(e))
                        continue

                if not import_btn_clicked:
                    self._take_screenshot(page, "import_btn_not_found")
                    # 记录页面上所有按钮，帮助调试
                    try:
                        buttons = page.evaluate("""() => {
                            return Array.from(document.querySelectorAll('button')).map(b => ({
                                text: b.innerText,
                                class: b.className
                            }));
                        }""")
                        logger.error("import_btn_not_found", available_buttons=buttons)
                    except Exception as e:
                        logger.error("import_btn_not_found", debug_error=str(e))
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
                        logger.debug("try_file_input", selector=selector)
                        page.wait_for_selector(selector, timeout=5000, state='attached')
                        file_inputs = page.locator(selector).all()
                        logger.debug("file_inputs_found", count=len(file_inputs))
                        for idx, file_input in enumerate(file_inputs):
                            try:
                                file_input.set_input_files(docx_path)
                                file_uploaded = True
                                logger.info("file_uploaded", selector=selector, input_index=idx, file=docx_path)
                                time.sleep(5)
                                break
                            except Exception as e:
                                logger.debug("file_input_failed", index=idx, error=str(e))
                                continue
                        if file_uploaded:
                            break
                    except Exception as e:
                        logger.debug("file_selector_not_found", selector=selector, error=str(e))
                        continue

                if not file_uploaded:
                    self._take_screenshot(page, "file_upload_failed")
                    raise PublishException("文件上传失败")

                logger.info("docx_uploaded", file=docx_path)
                time.sleep(5)

                # 检查确认按钮
                for selector in ['button:has-text("确认")', 'button:has-text("确定")', 'button:has-text("导入")']:
                    try:
                        if page.locator(selector).count() > 0:
                            page.locator(selector).first.click()
                            logger.info("confirm_btn_clicked", selector=selector)
                            time.sleep(2)
                            break
                    except Exception as e:
                        logger.debug("confirm_btn_not_found", selector=selector, error=str(e))
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
                            logger.info("publish_btn_clicked", selector=selector)
                            time.sleep(3)
                            break
                    except Exception as e:
                        logger.debug("publish_btn_not_found", selector=selector, error=str(e))
                        continue

                if not publish_clicked:
                    self._take_screenshot(page, "publish_btn_not_found")
                    raise PublishException("未找到发布按钮")

                # 确认发布
                time.sleep(2)
                for selector in ['button:has-text("确认发布")', 'button:has-text("确认")']:
                    try:
                        if page.locator(selector).count() > 0:
                            page.locator(selector).first.click()
                            logger.info("final_confirm_clicked", selector=selector)
                            break
                    except Exception as e:
                        logger.debug("final_confirm_not_found", selector=selector, error=str(e))
                        continue

                # 立即轮询检查 toast 消息（显示时间很短）
                success_detected = False
                logger.info("checking_publish_result")
                for i in range(20):  # 最多检查10秒
                    time.sleep(0.5)
                    # 检查 toast 提示
                    toast_texts = ['提交成功', '发布成功', '已发布', '审核中']
                    for text in toast_texts:
                        try:
                            if page.locator(f'text={text}').count() > 0:
                                success_detected = True
                                logger.info("publish_success_toast", text=text, check_round=i)
                                break
                        except Exception as e:
                            logger.debug("toast_check_error", text=text, error=str(e))
                    if success_detected:
                        break
                    # 检查 URL 变化
                    current_url = page.url
                    if "success" in current_url.lower() or ("content" in current_url.lower() and "publish" not in current_url.lower()):
                        success_detected = True
                        logger.info("publish_success_url", url=current_url, check_round=i)
                        break

                final_url = page.url
                logger.info("publish_check_complete", success=success_detected, final_url=final_url)

                if success_detected:
                    return {"success": True, "url": final_url, "message": "发布成功"}
                else:
                    self._take_screenshot(page, "publish_no_success_toast")
                    # 检查是否有错误提示
                    try:
                        error_texts = page.evaluate("""() => {
                            const errors = document.querySelectorAll('.error, .toast-error, [class*="error"], [class*="fail"]');
                            return Array.from(errors).map(e => e.innerText).filter(t => t);
                        }""")
                        if error_texts:
                            logger.error("publish_error_detected", errors=error_texts)
                    except Exception as e:
                        logger.debug("error_check_failed", error=str(e))
                    raise PublishException("发布失败，未检测到成功提示")

            except PublishException:
                raise
            except Exception as e:
                self._take_screenshot(page, "publish_exception")
                logger.error("publish_error", error=str(e), error_type=type(e).__name__)
                raise PublishException(f"发布过程出错: {str(e)}")
            finally:
                context.close()
                browser.close()
                logger.info("browser_closed")

    def _run_sync_publish_form(
        self,
        title: str,
        content: str,
        cookies: List[dict],
        images: Optional[List[str]] = None,
    ) -> dict:
        """同步表单发布（在线程中运行）"""
        import time

        headless = _parse_headless(settings.BROWSER_HEADLESS)
        logger.info(
            "browser_launch_start",
            method="form_publish",
            headless=settings.BROWSER_HEADLESS,
            slow_mo=settings.BROWSER_SLOW_MO,
        )

        with sync_playwright() as p:
            browser = p.chromium.launch(
                channel="chrome",
                headless=headless,
                slow_mo=settings.BROWSER_SLOW_MO,
                args=[
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-blink-features=AutomationControlled",
                    "--disable-infobars",
                ]
            )
            context = browser.new_context(
                viewport={
                    "width": settings.BROWSER_VIEWPORT_WIDTH,
                    "height": settings.BROWSER_VIEWPORT_HEIGHT,
                },
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                locale="zh-CN",
                timezone_id="Asia/Shanghai",
            )
            context.set_default_timeout(settings.BROWSER_TIMEOUT)
            # 移除 webdriver 标记
            context.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            """)
            page = context.new_page()

            try:
                if cookies:
                    normalized_cookies = self._normalize_cookies(cookies)
                    logger.info("cookies_inject", count=len(normalized_cookies))
                    context.add_cookies(normalized_cookies)

                logger.info("navigate_to_publish_page", url=self.ARTICLE_PUBLISH_URL)
                page.goto(self.ARTICLE_PUBLISH_URL, wait_until="networkidle")
                time.sleep(3)

                current_url = page.url
                logger.info("page_loaded", url=current_url)
                if "login" in current_url.lower():
                    self._take_screenshot(page, "form_login_required")
                    raise PublishException("Cookie已过期，请重新登录")

                # 填写标题
                logger.info("filling_title", title_length=len(title))
                title_input = page.locator('textarea[placeholder*="标题"]').first
                title_input.fill(title)
                time.sleep(1)

                # 填写正文
                logger.info("filling_content", content_length=len(content))
                editor = page.locator('[contenteditable="true"]').first
                editor.click()
                paragraphs = content.split("\n")
                for i, para in enumerate(paragraphs):
                    if para.strip():
                        page.keyboard.insert_text(para)
                        if i < len(paragraphs) - 1:
                            page.keyboard.press("Enter")
                            time.sleep(0.1)

                time.sleep(2)

                # 上传图片
                if images:
                    logger.info("uploading_images", count=len(images))
                    for idx, img_path in enumerate(images[:3]):
                        if os.path.exists(img_path):
                            try:
                                file_input = page.locator('input[type="file"]').first
                                file_input.set_input_files(img_path)
                                logger.info("image_uploaded", index=idx, path=img_path)
                                time.sleep(2)
                            except Exception as e:
                                logger.warning("image_upload_failed", index=idx, path=img_path, error=str(e))

                # 点击发布
                logger.info("clicking_publish_btn")
                page.locator('button:has-text("发布")').first.click()

                # 立即轮询检查 toast 消息
                success_detected = False
                logger.info("checking_publish_result")
                for i in range(20):  # 最多检查10秒
                    time.sleep(0.5)
                    toast_texts = ['提交成功', '发布成功', '已发布', '审核中']
                    for text in toast_texts:
                        try:
                            if page.locator(f'text={text}').count() > 0:
                                success_detected = True
                                logger.info("publish_success_toast", text=text, check_round=i)
                                break
                        except Exception as e:
                            logger.debug("toast_check_error", text=text, error=str(e))
                    if success_detected:
                        break
                    if "success" in page.url.lower():
                        success_detected = True
                        logger.info("publish_success_url", url=page.url, check_round=i)
                        break

                final_url = page.url
                logger.info("publish_check_complete", success=success_detected, final_url=final_url)

                if success_detected:
                    return {"success": True, "url": final_url, "message": "发布成功"}
                else:
                    self._take_screenshot(page, "form_publish_no_success")
                    raise PublishException("发布失败，未检测到成功提示")

            except PublishException:
                raise
            except Exception as e:
                self._take_screenshot(page, "form_publish_exception")
                logger.error("form_publish_error", error=str(e), error_type=type(e).__name__)
                raise PublishException(f"发布出错: {str(e)}")
            finally:
                context.close()
                browser.close()
                logger.info("browser_closed")

    async def publish_to_toutiao_via_docx(
        self,
        docx_path: str,
        cookies: List[dict],
    ) -> dict:
        """通过 DOCX 发布（异步包装）"""
        logger.info("publish_to_toutiao_via_docx_start", docx_path=docx_path)
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            _executor,
            self._run_sync_publish,
            docx_path,
            cookies,
        )

    async def publish_to_toutiao(
        self,
        title: str,
        content: str,
        cookies: List[dict],
        images: Optional[List[str]] = None,
        docx_path: Optional[str] = None,
    ) -> dict:
        """发布到头条号（文章）"""
        logger.info(
            "publish_to_toutiao_start",
            title_length=len(title) if title else 0,
            content_length=len(content) if content else 0,
            has_docx=bool(docx_path and os.path.exists(docx_path)),
            image_count=len(images) if images else 0,
        )
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
        )

    def _run_sync_publish_weitoutiao(
        self,
        content: str,
        cookies: List[dict],
        images: Optional[List[str]] = None,
        docx_path: Optional[str] = None,
    ) -> dict:
        """同步发布微头条（在线程中运行）"""
        import time

        headless = _parse_headless(settings.BROWSER_HEADLESS)
        logger.info(
            "browser_launch_start",
            method="weitoutiao",
            headless=settings.BROWSER_HEADLESS,
            slow_mo=settings.BROWSER_SLOW_MO,
            has_docx=bool(docx_path),
        )

        with sync_playwright() as p:
            browser = p.chromium.launch(
                channel="chrome",
                headless=headless,
                slow_mo=settings.BROWSER_SLOW_MO,
                args=[
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-blink-features=AutomationControlled",
                    "--disable-infobars",
                ]
            )
            context = browser.new_context(
                viewport={
                    "width": settings.BROWSER_VIEWPORT_WIDTH,
                    "height": settings.BROWSER_VIEWPORT_HEIGHT,
                },
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                locale="zh-CN",
                timezone_id="Asia/Shanghai",
            )
            context.set_default_timeout(settings.BROWSER_TIMEOUT)
            # 移除 webdriver 标记
            context.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            """)
            page = context.new_page()

            try:
                if cookies:
                    normalized_cookies = self._normalize_cookies(cookies)
                    logger.info("cookies_inject", count=len(normalized_cookies))
                    context.add_cookies(normalized_cookies)

                # 访问微头条发布页面
                logger.info("navigate_to_weitoutiao_page", url=self.WEITOUTIAO_PUBLISH_URL)
                page.goto(self.WEITOUTIAO_PUBLISH_URL, wait_until="networkidle")
                time.sleep(3)

                current_url = page.url
                logger.info("page_loaded", url=current_url)
                if "login" in current_url.lower():
                    self._take_screenshot(page, "weitoutiao_login_required")
                    raise PublishException("Cookie已过期，请重新登录")

                logger.info("weitoutiao_publish_start", has_docx=bool(docx_path), content_length=len(content))

                # 如果有 DOCX 文件，使用文档导入方式
                if docx_path and os.path.exists(docx_path):
                    # 查找并点击"文档导入"按钮
                    import_btn_selectors = [
                        '.weitoutiao-import-plugin button',
                        '.syl-toolbar-tool.weitoutiao-import-plugin button',
                        '.doc-import-icon',
                        'button:has-text("文档导入")',
                    ]

                    import_btn_clicked = False
                    for selector in import_btn_selectors:
                        try:
                            logger.debug("try_selector", selector=selector, action="weitoutiao_import_btn")
                            page.wait_for_selector(selector, timeout=5000)
                            page.locator(selector).first.click()
                            import_btn_clicked = True
                            logger.info("weitoutiao_import_btn_clicked", selector=selector)
                            time.sleep(3)
                            break
                        except Exception as e:
                            logger.debug("selector_not_found", selector=selector, error=str(e))
                            continue

                    if not import_btn_clicked:
                        logger.warning("weitoutiao_import_btn_not_found", fallback="direct_input")
                        self._take_screenshot(page, "weitoutiao_import_btn_not_found")
                        # 回退到直接输入方式
                    else:
                        # 上传文件
                        time.sleep(2)
                        file_input_selectors = [
                            'input[type="file"]',
                            'input[type="file"][accept*="docx"]',
                        ]

                        file_uploaded = False
                        for selector in file_input_selectors:
                            try:
                                logger.debug("try_file_input", selector=selector)
                                page.wait_for_selector(selector, timeout=5000, state='attached')
                                file_inputs = page.locator(selector).all()
                                logger.debug("file_inputs_found", count=len(file_inputs))
                                for idx, file_input in enumerate(file_inputs):
                                    try:
                                        file_input.set_input_files(docx_path)
                                        file_uploaded = True
                                        logger.info("weitoutiao_file_uploaded", selector=selector, index=idx, file=docx_path)
                                        time.sleep(5)
                                        break
                                    except Exception as e:
                                        logger.debug("file_input_failed", index=idx, error=str(e))
                                        continue
                                if file_uploaded:
                                    break
                            except Exception as e:
                                logger.debug("file_selector_not_found", selector=selector, error=str(e))
                                continue

                        if file_uploaded:
                            logger.info("weitoutiao_docx_uploaded", file=docx_path)
                            time.sleep(3)

                            # 检查确认按钮
                            for selector in ['button:has-text("确认")', 'button:has-text("确定")', 'button:has-text("导入")']:
                                try:
                                    if page.locator(selector).count() > 0:
                                        page.locator(selector).first.click()
                                        logger.info("weitoutiao_confirm_btn_clicked", selector=selector)
                                        time.sleep(2)
                                        break
                                except Exception as e:
                                    logger.debug("confirm_btn_not_found", selector=selector, error=str(e))
                                    continue
                        else:
                            logger.warning("weitoutiao_file_upload_failed", fallback="direct_input")
                            self._take_screenshot(page, "weitoutiao_file_upload_failed")
                else:
                    # 直接输入内容
                    logger.info("weitoutiao_direct_input_start", content_length=len(content))
                    editor = page.locator('[contenteditable="true"]').first
                    editor.click()
                    time.sleep(0.5)

                    paragraphs = content.split("\n")
                    for i, para in enumerate(paragraphs):
                        if para.strip():
                            page.keyboard.insert_text(para)
                            if i < len(paragraphs) - 1:
                                page.keyboard.press("Enter")
                                time.sleep(0.1)

                    logger.info("weitoutiao_content_filled")
                    time.sleep(2)

                    # 上传图片
                    if images:
                        logger.info("weitoutiao_uploading_images", count=len(images))
                        for idx, img_path in enumerate(images[:9]):  # 微头条最多9张图
                            if os.path.exists(img_path):
                                try:
                                    file_input = page.locator('input[type="file"][accept*="image"]').first
                                    file_input.set_input_files(img_path)
                                    logger.info("weitoutiao_image_uploaded", index=idx, path=img_path)
                                    time.sleep(2)
                                except Exception as e:
                                    logger.warning("weitoutiao_image_upload_failed", index=idx, path=img_path, error=str(e))

                time.sleep(2)

                # 点击发布按钮
                publish_selectors = [
                    'button:has-text("发布")',
                    'button:has-text("立即发布")',
                    '.publish-btn',
                ]

                publish_clicked = False
                for selector in publish_selectors:
                    try:
                        if page.locator(selector).count() > 0:
                            page.locator(selector).first.click()
                            publish_clicked = True
                            logger.info("weitoutiao_publish_btn_clicked", selector=selector)
                            time.sleep(3)
                            break
                    except Exception as e:
                        logger.debug("publish_btn_not_found", selector=selector, error=str(e))
                        continue

                if not publish_clicked:
                    self._take_screenshot(page, "weitoutiao_publish_btn_not_found")
                    raise PublishException("未找到发布按钮")

                # 确认发布
                time.sleep(2)
                for selector in ['button:has-text("确认发布")', 'button:has-text("确认")']:
                    try:
                        if page.locator(selector).count() > 0:
                            page.locator(selector).first.click()
                            logger.info("weitoutiao_final_confirm_clicked", selector=selector)
                            break
                    except Exception as e:
                        logger.debug("final_confirm_not_found", selector=selector, error=str(e))
                        continue

                # 轮询检查发布结果
                success_detected = False
                logger.info("weitoutiao_checking_publish_result")
                for i in range(20):
                    time.sleep(0.5)
                    toast_texts = ['提交成功', '发布成功', '已发布', '审核中']
                    for text in toast_texts:
                        try:
                            if page.locator(f'text={text}').count() > 0:
                                success_detected = True
                                logger.info("weitoutiao_publish_success_toast", text=text, check_round=i)
                                break
                        except Exception as e:
                            logger.debug("toast_check_error", text=text, error=str(e))
                    if success_detected:
                        break
                    if "success" in page.url.lower():
                        success_detected = True
                        logger.info("weitoutiao_publish_success_url", url=page.url, check_round=i)
                        break

                final_url = page.url
                logger.info("weitoutiao_publish_check_complete", success=success_detected, final_url=final_url)

                if success_detected:
                    return {"success": True, "url": final_url, "message": "微头条发布成功"}
                else:
                    self._take_screenshot(page, "weitoutiao_no_success_toast")
                    # 检查是否有错误提示
                    try:
                        error_texts = page.evaluate("""() => {
                            const errors = document.querySelectorAll('.error, .toast-error, [class*="error"], [class*="fail"]');
                            return Array.from(errors).map(e => e.innerText).filter(t => t);
                        }""")
                        if error_texts:
                            logger.error("weitoutiao_error_detected", errors=error_texts)
                    except Exception as e:
                        logger.debug("error_check_failed", error=str(e))
                    raise PublishException("微头条发布失败，未检测到成功提示")

            except PublishException:
                raise
            except Exception as e:
                self._take_screenshot(page, "weitoutiao_exception")
                logger.error("weitoutiao_publish_error", error=str(e), error_type=type(e).__name__)
                raise PublishException(f"微头条发布出错: {str(e)}")
            finally:
                context.close()
                browser.close()
                logger.info("browser_closed")

    async def publish_weitoutiao(
        self,
        content: str,
        cookies: List[dict],
        images: Optional[List[str]] = None,
        docx_path: Optional[str] = None,
    ) -> dict:
        """发布微头条（异步包装）"""
        logger.info(
            "publish_weitoutiao_start",
            content_length=len(content) if content else 0,
            has_docx=bool(docx_path),
            image_count=len(images) if images else 0,
        )
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            _executor,
            self._run_sync_publish_weitoutiao,
            content,
            cookies,
            images,
            docx_path,
        )

    async def check_account_status(self, cookies: List[dict]) -> dict:
        """检查账号状态（使用 HTTP 请求）"""
        logger.info("check_account_status_start", cookie_count=len(cookies) if cookies else 0)
        try:
            cookie_dict = {c.get("name"): c.get("value") for c in cookies if c.get("name") and c.get("value")}

            check_url = "https://mp.toutiao.com/profile_v4/index/info"

            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept": "application/json, text/plain, */*",
                "Referer": self.ARTICLE_PUBLISH_URL,
            }

            async with httpx.AsyncClient(cookies=cookie_dict, headers=headers, follow_redirects=False, timeout=30.0) as client:
                response = await client.get(check_url)
                logger.info("check_account_response", status_code=response.status_code)

                if response.status_code in (301, 302, 303, 307, 308):
                    location = response.headers.get("location", "")
                    logger.info("check_account_redirect", location=location)
                    if "login" in location.lower():
                        return {"valid": False, "message": "Cookie已过期"}

                if response.status_code == 200:
                    try:
                        data = response.json()
                        if data.get("data") or data.get("user_id"):
                            logger.info("check_account_valid")
                            return {"valid": True, "message": "账号状态正常"}
                        if data.get("err_no"):
                            logger.info("check_account_expired", err_no=data.get("err_no"))
                            return {"valid": False, "message": "Cookie已过期"}
                    except ValueError as e:
                        logger.warning("check_account_json_parse_error", error=str(e))
                    return {"valid": True, "message": "账号状态正常"}

                logger.warning("check_account_unexpected_status", status_code=response.status_code)
                return {"valid": False, "message": f"状态码: {response.status_code}"}

        except Exception as e:
            logger.error("check_account_status_error", error=str(e), error_type=type(e).__name__)
            return {"valid": False, "message": f"检查失败: {str(e)}"}

    async def close(self):
        """关闭资源"""
        pass  # 同步 API 每次都会自动关闭


publisher = PublisherService()
