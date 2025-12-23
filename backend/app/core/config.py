from pathlib import Path
from typing import Literal
from pydantic_settings import BaseSettings

# 项目根目录
BASE_DIR = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    # App
    APP_NAME: str = "Toutiao Publisher"
    DEBUG: bool = False
    API_V1_PREFIX: str = "/api/v1"

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/toutiao"

    # Static files
    STATIC_DIR: str = str(BASE_DIR / "static")

    # Playwright/Patchright 配置
    # Patchright 推荐使用有头模式，headless="new" 可能不兼容
    BROWSER_HEADLESS: str = "false"  # "false" 有头模式，反检测效果最好
    BROWSER_SLOW_MO: int = 0  # 操作延迟(毫秒)，调试时可设置 100-500
    BROWSER_TIMEOUT: int = 30000  # 默认超时时间(毫秒)
    BROWSER_SCREENSHOT_ON_ERROR: bool = True  # 出错时是否截图
    BROWSER_SCREENSHOT_DIR: str = str(BASE_DIR / "static" / "screenshots")  # 截图保存目录
    BROWSER_VIEWPORT_WIDTH: int = 1920  # 浏览器视口宽度
    BROWSER_VIEWPORT_HEIGHT: int = 1080  # 浏览器视口高度

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
