#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

from patchright.sync_api import Page, sync_playwright


SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
ARTICLE_PUBLISH_URL = "https://mp.toutiao.com/profile_v4/graphic/publish"
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)
VIEWPORT = {"width": 1920, "height": 1080}
DEFAULT_TIMEOUT = 30000
DOCX_SCRIPT = SCRIPT_DIR / "export_docx.py"


class PublishError(RuntimeError):
    pass


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Publish a Toutiao article with Patchright using the main-branch launch order."
    )
    parser.add_argument("article", help="Path to the article JSON file.")
    parser.add_argument(
        "--output-dir",
        help="Directory for publish screenshots and logs. Defaults to publish-results/<article-stem>/",
    )
    parser.add_argument(
        "--docx-path",
        help="Optional prebuilt DOCX path. If omitted, the script will export one from the article JSON.",
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


def load_article(path: Path) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise PublishError("Article payload must be a JSON object.")
    if not str(payload.get("title", "")).strip():
        raise PublishError("Article title is required.")
    if not str(payload.get("content", "")).strip():
        raise PublishError("Article content is required.")
    return payload


def resolve_output_dir(article_path: Path, explicit: Optional[str]) -> Path:
    if explicit:
        output_dir = Path(explicit).resolve()
    else:
        output_dir = article_path.parent / "publish-results" / article_path.stem
    ensure_dir(output_dir)
    return output_dir


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


def export_docx(article_path: Path, output_dir: Path, explicit_docx_path: Optional[str]) -> Path:
    if explicit_docx_path:
        docx_path = Path(explicit_docx_path).resolve()
        if not docx_path.exists():
            raise PublishError(f"DOCX file not found: {docx_path}")
        return docx_path

    docx_path = output_dir / f"{article_path.stem}.docx"
    completed = subprocess.run(
        [sys.executable, str(DOCX_SCRIPT), str(article_path), "--output", str(docx_path)],
        cwd=str(SCRIPT_DIR),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if completed.returncode != 0 or not docx_path.exists():
        raise PublishError(completed.stderr.strip() or completed.stdout.strip() or "DOCX export failed.")
    return docx_path


def input_tags(page: Page, tags: list[str], output_dir: Path) -> None:
    if not tags:
        return

    editor_selectors = [
        '.ProseMirror[contenteditable="true"]',
        '.syl-editor [contenteditable="true"]',
        '[contenteditable="true"]',
    ]

    editor = None
    for selector in editor_selectors:
        try:
            locator = page.locator(selector)
            if locator.count() > 0:
                editor = locator.first
                break
        except Exception:
            continue

    if editor is None:
        take_screenshot(page, output_dir, "editor_not_found_for_tags")
        return

    editor.scroll_into_view_if_needed()
    time.sleep(0.3)
    editor.evaluate("el => el.focus()")
    time.sleep(0.2)
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

        suggestion_clicked = False
        for selector in suggestion_selectors:
            try:
                locator = page.locator(selector)
                if locator.count() > 0:
                    locator.first.click()
                    suggestion_clicked = True
                    time.sleep(0.5)
                    break
            except Exception:
                continue

        if not suggestion_clicked:
            page.keyboard.press("Space")
            time.sleep(0.3)

        take_screenshot(page, output_dir, f"tag_{index + 1}")

    page.keyboard.press("Enter")
    time.sleep(0.3)


def fill_title_if_needed(page: Page, title: str) -> None:
    if not title.strip():
        return

    title_selectors = [
        'textarea[placeholder*="标题"]',
        'textarea[placeholder*="文章标题"]',
        "textarea",
    ]
    for selector in title_selectors:
        try:
            locator = page.locator(selector)
            if locator.count() <= 0:
                continue
            target = locator.first
            target.wait_for(state="visible", timeout=5000)
            current_value = (target.input_value() or "").strip()
            if current_value != title.strip():
                target.fill(title)
                time.sleep(1)
            return
        except Exception:
            continue


def publish_via_docx(article: dict, docx_path: Path, cookies: list[dict], output_dir: Path) -> dict:
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

            page.goto(ARTICLE_PUBLISH_URL, wait_until="networkidle")
            time.sleep(3)

            current_url = page.url
            if "login" in current_url.lower():
                take_screenshot(page, output_dir, "login_required")
                raise PublishError("Cookie已过期，请重新登录")

            import_btn_selectors = [
                ".doc-import button",
                ".doc-import .syl-toolbar-button",
                ".syl-toolbar-tool.doc-import button",
            ]

            import_btn_clicked = False
            for selector in import_btn_selectors:
                try:
                    page.wait_for_selector(selector, timeout=5000)
                    page.evaluate(
                        f"""() => {{
                            const btn = document.querySelector('{selector}');
                            if (btn) {{ btn.click(); return true; }}
                            return false;
                        }}"""
                    )
                    import_btn_clicked = True
                    time.sleep(3)
                    break
                except Exception:
                    continue

            if not import_btn_clicked:
                take_screenshot(page, output_dir, "import_btn_not_found")
                raise PublishError("未找到导入文档按钮")

            time.sleep(2)
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
                take_screenshot(page, output_dir, "file_upload_failed")
                raise PublishError("文件上传失败")

            time.sleep(5)
            for selector in ['button:has-text("确认")', 'button:has-text("确定")', 'button:has-text("导入")']:
                try:
                    if page.locator(selector).count() > 0:
                        page.locator(selector).first.click()
                        time.sleep(2)
                        break
                except Exception:
                    continue

            time.sleep(3)
            fill_title_if_needed(page, str(article.get("title", "")))
            input_tags(page, list(article.get("tags") or []), output_dir)

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
                except Exception:
                    continue

            if not publish_clicked:
                take_screenshot(page, output_dir, "publish_btn_not_found")
                raise PublishError("未找到发布按钮")

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

            success_detected = False
            final_url = page.url
            success_text = ""
            for _ in range(20):
                time.sleep(0.5)
                for text in ["提交成功", "发布成功", "已发布", "审核中"]:
                    try:
                        if page.locator(f"text={text}").count() > 0:
                            success_detected = True
                            success_text = text
                            break
                    except Exception:
                        continue
                if success_detected:
                    break
                final_url = page.url
                if "success" in final_url.lower() or ("content" in final_url.lower() and "publish" not in final_url.lower()):
                    success_detected = True
                    success_text = "url_changed"
                    break

            after_path = take_screenshot(page, output_dir, "after_publish")
            result = {
                "success": success_detected,
                "success_signal": success_text,
                "clicked_confirm": confirm_clicked,
                "final_url": page.url,
                "final_title": page.title(),
                "body_text_snippet": page.locator("body").inner_text()[:8000],
                "docx_path": str(docx_path),
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
    article_path = Path(args.article).resolve()
    article = load_article(article_path)
    output_dir = resolve_output_dir(article_path, args.output_dir)

    cookie_string = os.environ.get("TOUTIAO_COOKIE_STRING", "").strip()
    if not cookie_string:
        raise SystemExit("Missing TOUTIAO_COOKIE_STRING environment variable.")

    cookies = parse_cookie_string(cookie_string)
    docx_path = export_docx(article_path, output_dir, args.docx_path)
    before_export = {
        "article_path": str(article_path),
        "docx_path": str(docx_path),
        "title": article.get("title", ""),
        "tag_count": len(article.get("tags") or []),
        "generated_image_paths": article.get("generated_image_paths", []),
        "prepared_at": datetime.now().astimezone().isoformat(timespec="seconds"),
    }
    (output_dir / "publish-prepared.json").write_text(
        json.dumps(before_export, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    try:
        result = publish_via_docx(article, docx_path, cookies, output_dir)
    except PublishError as exc:
        failure_path = output_dir / "publish-result.json"
        failure_path.write_text(str(exc), encoding="utf-8")
        raise SystemExit(str(exc))

    result_path = output_dir / "publish-result.json"
    result_path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(result_path)


if __name__ == "__main__":
    main()
