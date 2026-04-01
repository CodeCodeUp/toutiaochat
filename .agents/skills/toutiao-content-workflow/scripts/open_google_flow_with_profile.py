#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service


FLOW_URL = "https://labs.google/fx/zh/tools/flow/project/354a1f5c-6935-4e53-9cde-8efe14b8349b"
SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
PROFILE_DIR = SKILL_DIR / "browser-profile" / "chrome"


def build_driver() -> webdriver.Chrome:
    PROFILE_DIR.mkdir(parents=True, exist_ok=True)

    options = Options()
    options.binary_location = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
    options.add_argument(f"--user-data-dir={PROFILE_DIR}")
    options.add_argument("--window-size=1440,960")
    options.add_argument("--disable-blink-features=AutomationControlled")

    service = Service()
    return webdriver.Chrome(service=service, options=options)


def main() -> None:
    driver = build_driver()
    driver.set_page_load_timeout(120)
    driver.get(FLOW_URL)
    print("Persistent profile opened.")
    print(f"Profile dir: {PROFILE_DIR}")
    print(f"Current URL: {driver.current_url}")
    print("Log in with this browser once, then close it when finished.")
    input("Press Enter after you are done with the browser session...")
    driver.quit()


if __name__ == "__main__":
    main()
