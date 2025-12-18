from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # App
    APP_NAME: str = "Toutiao Publisher"
    DEBUG: bool = False
    API_V1_PREFIX: str = "/api/v1"

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/toutiao"

    # Security
    SECRET_KEY: str = "your-secret-key-change-in-production"

    # OpenAI
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4"
    OPENAI_BASE_URL: Optional[str] = None

    # Image Generation (Gemini)
    IMAGE_GEN_PROVIDER: str = "gemini"  # none/gemini/stable_diffusion/dalle
    IMAGE_GEN_API_KEY: str = "123456"
    IMAGE_GEN_API_URL: str = "http://116.205.244.106:9006"

    # Publish Settings
    PUBLISH_INTERVAL_MINUTES: int = 30
    MAX_RETRY_COUNT: int = 3

    # Encryption
    COOKIE_ENCRYPTION_KEY: str = "your-32-byte-key-for-aes-256!!"

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
