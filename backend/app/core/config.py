from pathlib import Path
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

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
