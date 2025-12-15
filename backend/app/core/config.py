from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # App
    APP_NAME: str = "Toutiao Publisher"
    DEBUG: bool = False
    API_V1_PREFIX: str = "/api/v1"

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/toutiao"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # Security
    SECRET_KEY: str = "your-secret-key-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440

    # OpenAI
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4"
    OPENAI_BASE_URL: Optional[str] = None

    # Image Generation (预留)
    IMAGE_GEN_PROVIDER: str = "none"  # none/stable_diffusion/dalle
    IMAGE_GEN_API_KEY: str = ""
    IMAGE_GEN_API_URL: str = ""

    # Publish Settings
    PUBLISH_INTERVAL_MINUTES: int = 30
    MAX_RETRY_COUNT: int = 3

    # Encryption
    COOKIE_ENCRYPTION_KEY: str = "your-32-byte-key-for-aes-256!!"

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
