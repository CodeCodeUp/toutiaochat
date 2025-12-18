from pydantic import BaseModel
from typing import Optional
from uuid import UUID
from datetime import datetime
from app.models.ai_config import AIConfigType


class AIConfigBase(BaseModel):
    api_key: str = ""
    api_url: str = ""
    model: str = ""


class AIConfigCreate(AIConfigBase):
    type: AIConfigType


class AIConfigUpdate(BaseModel):
    api_key: Optional[str] = None
    api_url: Optional[str] = None
    model: Optional[str] = None


class AIConfigResponse(AIConfigBase):
    id: UUID
    type: AIConfigType
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class AIConfigListResponse(BaseModel):
    configs: dict[str, AIConfigResponse | None]
