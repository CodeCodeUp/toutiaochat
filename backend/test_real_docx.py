#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
使用真实 DOCX 文档测试发布 - 有头模式
文档：2025年JavaWeb中级编程题.docx
"""

import asyncio
import sys
import os
from pathlib import Path
from playwright.async_api import async_playwright

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

# DOCX 文件路径
DOCX_FILE = "D:/Projects/toutiaochat/toutiaochat/backend/2025年JavaWeb中级编程题.docx"

# 真实的头条号 Cookie
TOUTIAO_COOKIES = [
    {"name": "_ga", "value": "GA1.1.1856891221.1758639891", "domain": ".toutiao.com", "path": "/"},
    {"name": "_ga_1Y7TBPV8DE", "value": "GS2.1.s1765971957$o1$g0$t1765971957$j60$l0$h0", "domain": ".toutiao.com", "path": "/"},
    {"name": "_ga_QEHZPBE5HH", "value": "GS2.1.s1765971901$o14$g0$t1765971901$j60$l0$h0", "domain": ".toutiao.com", "path": "/"},
    {"name": "csrf_session_id", "value": "7cb7f5bbe135b91285bd0616a9d7684d", "domain": "mp.toutiao.com", "path": "/"},
    {"name": "d_ticket", "value": "ab19e0bfa8d1ef65645a42d49147b0eb4be70", "domain": ".toutiao.com", "path": "/"},
    {"name": "gd_random", "value": "eyJtYXRjaCI6dHJ1ZSwicGVyY2VudCI6MC42Mzg3OTYxNDgxMDE3MTQ2fQ==.zF+randIzCJxiTsPnONdtLKJrKW9mnjKPVwW9jmEg2E=", "domain": "mp.toutiao.com", "path": "/profile_v4"},
    {"name": "gfkadpd", "value": "1231,25897", "domain": "mp.toutiao.com", "path": "/"},
    {"name": "is_staff_user", "value": "false", "domain": ".toutiao.com", "path": "/"},
    {"name": "n_mh", "value": "KkILF3dUFkVHzFL27vjlPKSgqCIOl3bDjt5NWNW-X7w", "domain": ".toutiao.com", "path": "/"},
    {"name": "odin_tt", "value": "b1ca8f12f433a06ddb54b965874f99cdb205eb5979ec9f543bfd6c91b273c51d42dba6d66eef52b39df197c511c6b0d3", "domain": ".toutiao.com", "path": "/"},
    {"name": "passport_auth_status", "value": "46f54133410f7a809c4df47bd4f572e7%2C", "domain": ".toutiao.com", "path": "/"},
    {"name": "passport_auth_status_ss", "value": "46f54133410f7a809c4df47bd4f572e7%2C", "domain": ".toutiao.com", "path": "/"},
    {"name": "passport_csrf_token", "value": "4a1384cd59b2e0644dc1da83b86eac4c", "domain": ".toutiao.com", "path": "/"},
    {"name": "passport_csrf_token_default", "value": "4a1384cd59b2e0644dc1da83b86eac4c", "domain": ".toutiao.com", "path": "/"},
    {"name": "s_v_web_id", "value": "verify_mj52u8gv_Q3N2fCYa_NRsL_4JQ4_BxJm_j1p87UzyY9X7", "domain": "mp.toutiao.com", "path": "/"},
    {"name": "session_tlb_tag", "value": "sttt%7C4%7C6lVJF6kiq43tb4xt5y1a2f________-km_osp5MXp9AR9wH7nfTuzfB0Ln5nX0EbcoIwp75N6hQ%3D", "domain": ".toutiao.com", "path": "/"},
    {"name": "session_tlb_tag_bk", "value": "sttt%7C4%7C6lVJF6kiq43tb4xt5y1a2f________-km_osp5MXp9AR9wH7nfTuzfB0Ln5nX0EbcoIwp75N6hQ%3D", "domain": ".toutiao.com", "path": "/"},
    {"name": "sessionid", "value": "ea554917a922ab8ded6f8c6de72d5ad9", "domain": ".toutiao.com", "path": "/"},
    {"name": "sessionid_ss", "value": "ea554917a922ab8ded6f8c6de72d5ad9", "domain": ".toutiao.com", "path": "/"},
    {"name": "sid_guard", "value": "ea554917a922ab8ded6f8c6de72d5ad9%7C1765591468%7C5184001%7CWed%2C+11-Feb-2026+02%3A04%3A29+GMT", "domain": ".toutiao.com", "path": "/"},
    {"name": "sid_tt", "value": "ea554917a922ab8ded6f8c6de72d5ad9", "domain": ".toutiao.com", "path": "/"},
    {"name": "sid_ucp_sso_v1", "value": "1.0.0-KDY1Zjg5NmM4MzJjOTdkNTM2MTQ4OTIyYjZlNGVjYzA4YTVkNTc2NjAKGwihr6GNOxCrk_PJBhgYIA4wkbjjuQU4BkD0BxoCaGwiIDk3NTQ3YWM5ZTViOTlkNjUwYWJlMzc2ZDdiNWI4M2Zh", "domain": ".toutiao.com", "path": "/"},
    {"name": "sid_ucp_v1", "value": "1.0.0-KGVmOTY2NjU4YzVjZTUyYjg3OWE5YmQ1ZjNiMmJlMjQzZTQwNjQ0NGMKFQihr6GNOxCsk_PJBhgYIA44BkD0BxoCbGYiIGVhNTU0OTE3YTkyMmFiOGRlZDZmOGM2ZGU3MmQ1YWQ5", "domain": ".toutiao.com", "path": "/"},
    {"name": "ssid_ucp_sso_v1", "value": "1.0.0-KDY1Zjg5NmM4MzJjOTdkNTM2MTQ4OTIyYjZlNGVjYzA4YTVkNTc2NjAKGwihr6GNOxCrk_PJBhgYIA4wkbjjuQU4BkD0BxoCaGwiIDk3NTQ3YWM5ZTViOTlkNjUwYWJlMzc2ZDdiNWI4M2Zh", "domain": ".toutiao.com", "path": "/"},
    {"name": "ssid_ucp_v1", "value": "1.0.0-KGVmOTY2NjU4YzVjZTUyYjg3OWE5YmQ1ZjNiMmJlMjQzZTQwNjQ0NGMKFQihr6GNOxCsk_PJBhgYIA44BkD0BxoCbGYiIGVhNTU0OTE3YTkyMmFiOGRlZDZmOGM2ZGU3MmQ1YWQ5", "domain": ".toutiao.com", "path": "/"},
    {"name": "sso_uid_tt", "value": "c2213a12b74acb10b946098f61edc165", "domain": ".toutiao.com", "path": "/"},
    {"name": "sso_uid_tt_ss", "value": "c2213a12b74acb10b946098f61edc165", "domain": ".toutiao.com", "path": "/"},
    {"name": "toutiao_sso_user", "value": "97547ac9e5b99d650abe376d7b5b83fa", "domain": ".toutiao.com", "path": "/"},
    {"name": "toutiao_sso_user_ss", "value": "97547ac9e5b99d650abe376d7b5b83fa", "domain": ".toutiao.com", "path": "/"},
    {"name": "tt_scid", "value": "AFjp3Y3Fn2gRywoiPQy25IBZJiL2bsGiCZ5WWwrMbZCLsEQxnvFVtSD-FgomjcYF3ba0", "domain": "mp.toutiao.com", "path": "/"},
    {"name": "tt_webid", "value": "7523157375402952207", "domain": ".toutiao.com", "path": "/"},
    {"name": "ttcid", "value": "2311459d5aca439c83be30b79dbf6a2025", "domain": "mp.toutiao.com", "path": "/"},
    {"name": "ttwid", "value": "1%7Czm3lbKl0qdLVvyuAsPt37k-SIttNQfGQsntM4dw65Ls%7C1765971914%7C4d857ccbe52c0c417eb8b8b860b0a50393a0b2807d028d5aa53c7209669eb94a", "domain": ".toutiao.com", "path": "/"},
    {"name": "uid_tt", "value": "d80f50e174880dd955fd85291b31d5dc", "domain": ".toutiao.com", "path": "/"},
    {"name": "uid_tt_ss", "value": "d80f50e174880dd955fd85291b31d5dc", "domain": ".toutiao.com", "path": "/"},
    {"name": "xg_p_tos_token", "value": "10a5f4876a0ecedce1dba2114b759c51", "domain": ".toutiao.com", "path": "/"},
    {"name": "xigua_csrf_token", "value": "l_egMFf0niNwBRwqQEfAvSVN", "domain": ".toutiao.com", "path": "/"},
]


async def test_real_docx_publish():
    """使用真实 DOCX 文档测试发布"""

    print("=" * 60)
    print("  REAL DOCX DOCUMENT PUBLISH TEST")
    print("=" * 60)
    print()
    print(f"Document: 2025年JavaWeb中级编程题.docx")
    print(f"Mode: VISIBLE BROWSER (slow_mo=1000ms)")
    print()

    # 检查文件是否存在
    if not os.path.exists(DOCX_FILE):
        print(f"[ERROR] File not found: {DOCX_FILE}")
        return

    file_size = os.path.getsize(DOCX_FILE)
    print(f"[OK] File exists: {file_size} bytes")
    print()

    print("[WARNING] This will ACTUALLY publish to Toutiao!")
    print("Press Ctrl+C within 5 seconds to cancel...")
    try:
        await asyncio.sleep(5)
    except KeyboardInterrupt:
        print("\n[CANCELLED] Test cancelled by user")
        return

    print("\n[INFO] Starting publish test...\n")

    # 启动浏览器（有头模式，慢速）
    playwright = await async_playwright().start()
    browser = await playwright.chromium.launch(
        headless=False,       # 可见模式
        slow_mo=1000,         # 放慢操作 1 秒，便于观察
        args=[
            "--no-sandbox",
            "--disable-setuid-sandbox",
            "--start-maximized",
        ]
    )

    context = await browser.new_context(
        viewport={"width": 1920, "height": 1080},
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    )

    try:
        # 注入 Cookie
        await context.add_cookies(TOUTIAO_COOKIES)
        page = await context.new_page()

        print("[Step 1/7] Visiting publish page...")
        await page.goto("https://mp.toutiao.com/profile_v4/graphic/publish",
                       wait_until="networkidle", timeout=30000)
        await asyncio.sleep(2)
        print("    [OK] Page loaded")

        print("\n[Step 2/7] Clicking import document button...")
        await page.evaluate("""() => {
            const btn = document.querySelector('.doc-import button');
            if (btn) {
                btn.click();
                console.log('Import button clicked');
            }
        }""")
        await asyncio.sleep(2)
        print("    [OK] Import button clicked")

        print("\n[Step 3/7] Uploading DOCX file...")
        file_input = await page.wait_for_selector('input[type="file"]', timeout=8000)
        await file_input.set_input_files(DOCX_FILE)
        print(f"    [OK] File uploaded: {os.path.basename(DOCX_FILE)}")
        await asyncio.sleep(3)

        print("\n[Step 4/7] Waiting for content to parse and load...")
        print("    (This may take 5-8 seconds)")
        await asyncio.sleep(8)
        print("    [OK] Content should be loaded now")

        print("\n[Step 5/7] Clicking 'Preview and Publish' button...")
        try:
            preview_btn = page.locator('button:has-text("预览并发布")').first
            await preview_btn.click(timeout=5000)
            print("    [OK] Preview button clicked")
        except Exception as e:
            print(f"    [ERROR] Failed to click preview button: {e}")
            # 尝试其他选择器
            try:
                await page.locator('button:has-text("发布")').first.click(timeout=5000)
                print("    [OK] Alternative publish button clicked")
            except:
                print("    [ERROR] Could not find publish button")

        await asyncio.sleep(3)

        print("\n[Step 6/7] Looking for confirm dialog...")
        try:
            # 检查是否有确认对话框
            confirm_btn = page.locator('button:has-text("确认")').first
            if await confirm_btn.count() > 0:
                print("    [OK] Confirm dialog found")
                await confirm_btn.click(timeout=5000)
                print("    [OK] Confirm button clicked")
            else:
                print("    [WARN] No confirm dialog (might not be needed)")
        except Exception as e:
            print(f"    [WARN] Confirm dialog handling: {e}")

        await asyncio.sleep(2)

        print("\n[Step 7/7] Waiting for publish to complete...")
        print("    (Waiting 10 seconds to see result)")
        await asyncio.sleep(10)

        final_url = page.url
        print(f"\n[RESULT] Final URL: {final_url}")

        # 检查结果
        if "publish" not in final_url.lower():
            print("    [OK] Page redirected (likely success)")
        else:
            print("    [WARN] Still on publish page")

        success_text = await page.locator('text=成功').count()
        error_text = await page.locator('text=失败').count()

        print(f"    Success indicators: {success_text}")
        print(f"    Error indicators: {error_text}")

        print("\n" + "=" * 60)
        print("MANUAL CHECK REQUIRED")
        print("=" * 60)
        print("Please check in the browser:")
        print("  1. Did the content import correctly?")
        print("  2. Was the publish button clicked?")
        print("  3. Are there any error messages?")
        print("  4. Is the article in your content list?")
        print()
        print("Browser will stay open for 120 seconds...")
        print("=" * 60)

        await asyncio.sleep(120)

    except Exception as e:
        print(f"\n[ERROR] Test failed: {e}")
        import traceback
        traceback.print_exc()

        print("\n[DEBUG] Browser will stay open for 60 seconds...")
        await asyncio.sleep(60)

    finally:
        await context.close()
        await browser.close()
        await playwright.stop()
        print("\n[DONE] Browser closed")


async def main():
    try:
        await test_real_docx_publish()
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")


if __name__ == "__main__":
    asyncio.run(main())
