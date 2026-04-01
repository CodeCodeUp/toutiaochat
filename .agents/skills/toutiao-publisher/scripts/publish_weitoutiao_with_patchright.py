#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

from patchright.sync_api import Page, sync_playwright


SCRIPT_DIR = Path(__file__).resolve().parent
WEITOUTIAO_PUBLISH_URL = "https://mp.toutiao.com/profile_v4/weitoutiao/publish?from=toutiao_pc"
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)
VIEWPORT = {"width": 1920, "height": 1080}
DEFAULT_TIMEOUT = 30000


class PublishError(RuntimeError):
    pass


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Publish a Toutiao weitoutiao payload with Patchright using the main-branch launch order."
    )
    parser.add_argument("payload", help="Path to the weitoutiao JSON file.")
    parser.add_argument(
        "--output-dir",
        help="Directory for publish screenshots and logs. Defaults to publish-results/<payload-stem>/",
    )
    parser.add_argument(
        "--docx-path",
        help="Optional DOCX path. When provided, the script tries document import first, then falls back to direct input.",
    )
    return parser.parse_args()


def now_stamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def parse_cookie_string(cookie_string: str) -> list[dict]:
    cookies = []
    for part in cookie_string.split(";"):
        item = part.strip()
        if not item or "=" not in item:
            continue
        name, value = item.split("=", 1)
        name = name.strip()
        value = value.strip()
        if not name or not value:
            continue
        cookies.append(
            {
                "name": name,
                "value": value,
                "domain": ".toutiao.com",
                "path": "/",
                "sameSite": "Lax",
            }
        )
    return cookies


def load_payload(path: Path) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise PublishError("Weitoutiao payload must be a JSON object.")
    if str(payload.get("content_type", "")).strip().lower() != "weitoutiao":
        raise PublishError("Payload content_type must be weitoutiao.")
    if not str(payload.get("content", "")).strip():
        raise PublishError("Weitoutiao content is required.")
    return payload


def resolve_output_dir(payload_path: Path, explicit: Optional[str]) -> Path:
    if explicit:
        output_dir = Path(explicit).resolve()
    else:
        output_dir = payload_path.parent / "publish-results" / payload_path.stem
    ensure_dir(output_dir)
    return output_dir


def resolve_docx_path(explicit: Optional[str], payload: dict) -> Optional[Path]:
    candidates: list[Path] = []
    if explicit:
        candidates.append(Path(explicit).resolve())

    raw_docx_path = str(payload.get("docx_path", "")).strip()
    if raw_docx_path:
        candidates.append(Path(raw_docx_path).resolve())

    for path in candidates:
        if path.exists():
            return path
    return None


def normalize_cookies(cookies: list[dict]) -> list[dict]:
    normalized = []
    for cookie in cookies:
        name = cookie.get("name")
        value = cookie.get("value")
        if not name or not value:
            continue
        normalized.append(
            {
                "name": name,
                "value": value,
                "domain": cookie.get("domain", ".toutiao.com"),
                "path": cookie.get("path", "/"),
                "sameSite": "Lax",
            }
        )
    return normalized


def take_screenshot(page: Page, output_dir: Path, name: str) -> Path:
    path = output_dir / f"{name}_{now_stamp()}.png"
    page.screenshot(path=str(path), full_page=True)
    return path


def collect_generated_images(payload: dict) -> list[str]:
    flattened: list[str] = []
    seen: set[str] = set()

    for raw_path in payload.get("generated_image_paths") or []:
        path = str(raw_path).strip()
        if path and path not in seen and os.path.exists(path):
            flattened.append(path)
            seen.add(path)

    for prompt in payload.get("image_prompts") or []:
        for item in prompt.get("generated_images") or []:
            path = str(item.get("file_path", "")).strip()
            if path and path not in seen and os.path.exists(path):
                flattened.append(path)
                seen.add(path)

    return flattened


def input_tags(page: Page, tags: list[str], output_dir: Path) -> None:
    if not tags:
        return

    editor = page.locator('[contenteditable="true"]').first
    if editor.count() <= 0:
        take_screenshot(page, output_dir, "editor_not_found_for_tags")
        return

    editor.click()
    time.sleep(0.3)
    page.keyboard.press("Control+End")
    time.sleep(0.3)
    page.keyboard.press("Enter")
    time.sleep(0.2)

    suggestion_selectors = [
        ".forum-list-item",
        "section.forum-list-item",
        ".forum-list-item-text",
        ".tag-suggest-item",
        ".tag-suggestion-item",
        ".suggest-item",
        ".mention-item",
        '[class*="suggest"] [class*="item"]',
        '[class*="dropdown"] [class*="item"]',
        '[role="option"]',
    ]

    for index, tag in enumerate(tags):
        page.keyboard.type("#", delay=50)
        time.sleep(0.8)
        page.keyboard.type(tag, delay=50)
        time.sleep(1.5)
        clicked = False
        for selector in suggestion_selectors:
            try:
                locator = page.locator(selector)
                if locator.count() > 0:
                    locator.first.click()
                    clicked = True
                    time.sleep(0.5)
                    break
            except Exception:
                continue
        if not clicked:
            page.keyboard.press("Space")
            time.sleep(0.3)
        take_screenshot(page, output_dir, f"tag_{index + 1}")

    page.keyboard.press("Enter")
    time.sleep(0.3)


def fill_content(page: Page, content: str) -> None:
    editor = page.locator('[contenteditable="true"]').first
    if editor.count() <= 0:
        raise PublishError("未找到微头条正文编辑器。")
    editor.click()
    time.sleep(0.5)

    paragraphs = content.split("\n")
    for index, para in enumerate(paragraphs):
        if para.strip():
            page.keyboard.insert_text(para)
            if index < len(paragraphs) - 1:
                page.keyboard.press("Enter")
                time.sleep(0.1)


def upload_images(page: Page, images: list[str], output_dir: Path) -> list[str]:
    uploaded: list[str] = []

    for index, image_path in enumerate(images[:9], start=1):
        if not image_path or not os.path.exists(image_path):
            continue

        try:
            open_image_panel(page)
            file_input = page.locator('input[type="file"][accept*="image"]').first
            if file_input.count() <= 0:
                continue
            file_input.set_input_files(image_path)
            time.sleep(3)
            close_image_drawer_if_present(page)
            take_screenshot(page, output_dir, f"image_{index}")
            uploaded.append(image_path)
        except Exception:
            continue

    if images and not uploaded:
        take_screenshot(page, output_dir, "image_upload_failed")

    return uploaded


def open_image_panel(page: Page) -> None:
    trigger_selectors = [
        'button:has-text("图片")',
        'text=图片',
    ]
    for selector in trigger_selectors:
        try:
            locator = page.locator(selector).first
            if locator.count() > 0 and locator.is_visible():
                locator.click()
                time.sleep(1)
                return
        except Exception:
            continue


def close_image_drawer_if_present(page: Page) -> None:
    confirm_selectors = [
        ".byte-drawer-wrapper .byte-btn-primary",
        'button:has-text("确定")',
        'button:has-text("确认")',
        'button:has-text("完成")',
    ]
    for selector in confirm_selectors:
        try:
            locator = page.locator(selector).last
            if locator.count() > 0 and locator.is_visible():
                locator.click()
                time.sleep(2)
                return
        except Exception:
            continue


def try_docx_import(page: Page, docx_path: Optional[Path], output_dir: Path) -> bool:
    if not docx_path or not docx_path.exists():
        return False

    import_btn_selectors = [
        ".weitoutiao-import-plugin button",
        ".syl-toolbar-tool.weitoutiao-import-plugin button",
        ".doc-import-icon",
        'button:has-text("文档导入")',
    ]

    import_btn_clicked = False
    for selector in import_btn_selectors:
        try:
            page.wait_for_selector(selector, timeout=5000)
            page.locator(selector).first.click()
            import_btn_clicked = True
            time.sleep(3)
            break
        except Exception:
            continue

    if not import_btn_clicked:
        take_screenshot(page, output_dir, "weitoutiao_import_btn_not_found")
        return False

    file_input_selectors = [
        'input[type="file"]',
        'input[type="file"][accept*="docx"]',
    ]

    file_uploaded = False
    for selector in file_input_selectors:
        try:
            page.wait_for_selector(selector, timeout=5000, state="attached")
            file_inputs = page.locator(selector).all()
            for file_input in file_inputs:
                try:
                    file_input.set_input_files(str(docx_path))
                    file_uploaded = True
                    time.sleep(5)
                    break
                except Exception:
                    continue
            if file_uploaded:
                break
        except Exception:
            continue

    if not file_uploaded:
        take_screenshot(page, output_dir, "weitoutiao_docx_upload_failed")
        return False

    for selector in ['button:has-text("确认")', 'button:has-text("确定")', 'button:has-text("导入")']:
        try:
            if page.locator(selector).count() > 0:
                page.locator(selector).first.click()
                time.sleep(2)
                break
        except Exception:
            continue

    take_screenshot(page, output_dir, "after_docx_import")
    return True


def wait_for_publish_result(page: Page, content: str) -> tuple[bool, str]:
    content_snippet = next((line.strip() for line in content.splitlines() if line.strip()), "")[:28]
    toast_texts = ["提交成功", "发布成功"]

    for _ in range(30):
        time.sleep(0.5)

        for text in toast_texts:
            try:
                if page.locator(f"text={text}").count() > 0:
                    return True, text
            except Exception:
                continue

        current_url = page.url
        if "/profile_v4/weitoutiao" in current_url:
            try:
                body_text = page.locator("body").inner_text()[:12000]
            except Exception:
                body_text = ""
            if content_snippet and content_snippet in body_text:
                return True, f"list_contains:{content_snippet}"

    return False, ""


def publish_weitoutiao(payload: dict, cookies: list[dict], output_dir: Path, docx_path: Optional[Path]) -> dict:
    content = str(payload.get("content", "")).strip()
    tags = list(payload.get("tags") or [])
    images = collect_generated_images(payload)

    with sync_playwright() as p:
        browser = p.chromium.launch(
            channel="chrome",
            headless=False,
            slow_mo=0,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--disable-blink-features=AutomationControlled",
                "--disable-infobars",
            ],
        )
        context = browser.new_context(
            viewport=VIEWPORT,
            user_agent=DEFAULT_USER_AGENT,
            locale="zh-CN",
            timezone_id="Asia/Shanghai",
        )
        context.set_default_timeout(DEFAULT_TIMEOUT)
        context.add_init_script(
            """
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            """
        )
        page = context.new_page()

        try:
            if cookies:
                context.add_cookies(normalize_cookies(cookies))

            page.goto(WEITOUTIAO_PUBLISH_URL, wait_until="networkidle")
            time.sleep(3)

            current_url = page.url
            if "login" in current_url.lower():
                take_screenshot(page, output_dir, "weitoutiao_login_required")
                raise PublishError("Cookie已过期，请重新登录。")

            docx_imported = try_docx_import(page, docx_path, output_dir)
            uploaded_images: list[str] = []

            if not docx_imported:
                fill_content(page, content)
                time.sleep(2)
                uploaded_images = upload_images(page, images, output_dir)

            time.sleep(2)
            if tags:
                input_tags(page, tags, output_dir)

            publish_selectors = [
                'button:has-text("发布")',
                'button:has-text("立即发布")',
                ".publish-btn",
            ]
            publish_clicked = False
            for selector in publish_selectors:
                try:
                    if page.locator(selector).count() > 0:
                        page.locator(selector).first.click()
                        publish_clicked = True
                        time.sleep(3)
                        break
                except Exception:
                    continue

            if not publish_clicked:
                take_screenshot(page, output_dir, "weitoutiao_publish_btn_not_found")
                raise PublishError("未找到微头条发布按钮。")

            confirm_clicked = False
            time.sleep(2)
            for selector in ['button:has-text("确认发布")', 'button:has-text("确认")']:
                try:
                    if page.locator(selector).count() > 0:
                        page.locator(selector).first.click()
                        confirm_clicked = True
                        break
                except Exception:
                    continue

            success_detected, success_signal = wait_for_publish_result(page, content)
            after_path = take_screenshot(page, output_dir, "after_publish")
            result = {
                "success": success_detected,
                "success_signal": success_signal,
                "clicked_confirm": confirm_clicked,
                "used_docx_import": docx_imported,
                "docx_path": str(docx_path) if docx_path else "",
                "final_url": page.url,
                "final_title": page.title(),
                "generated_image_paths": images,
                "uploaded_image_paths": uploaded_images,
                "body_text_snippet": page.locator("body").inner_text()[:12000],
                "after_screenshot": str(after_path),
                "published_at": datetime.now().astimezone().isoformat(timespec="seconds"),
            }
            if not success_detected:
                raise PublishError(json.dumps(result, ensure_ascii=False, indent=2))
            return result
        finally:
            context.close()
            browser.close()


def main() -> None:
    args = parse_args()
    payload_path = Path(args.payload).resolve()
    payload = load_payload(payload_path)
    output_dir = resolve_output_dir(payload_path, args.output_dir)

    cookie_string = os.environ.get("TOUTIAO_COOKIE_STRING", "").strip()
    if not cookie_string:
        raise SystemExit("Missing TOUTIAO_COOKIE_STRING environment variable.")

    cookies = parse_cookie_string(cookie_string)
    docx_path = resolve_docx_path(args.docx_path, payload)

    prepared = {
        "payload_path": str(payload_path),
        "content_type": payload.get("content_type", ""),
        "title": payload.get("title", ""),
        "generated_image_paths": collect_generated_images(payload),
        "docx_path": str(docx_path) if docx_path else "",
        "prepared_at": datetime.now().astimezone().isoformat(timespec="seconds"),
    }
    (output_dir / "publish-prepared.json").write_text(
        json.dumps(prepared, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    try:
        result = publish_weitoutiao(payload, cookies, output_dir, docx_path)
    except PublishError as exc:
        (output_dir / "publish-result.json").write_text(str(exc), encoding="utf-8")
        raise SystemExit(str(exc))

    result_path = output_dir / "publish-result.json"
    result_path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(result_path)


if __name__ == "__main__":
    main()
