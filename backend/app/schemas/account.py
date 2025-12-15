from datetime import datetime
from typing import Optional, List
from uuid import UUID
from pydantic import BaseModel, Field

from app.models.account import AccountStatus, Platform


class AccountBase(BaseModel):
    nickname: str = Field(..., max_length=100, description="账号昵称")
    platform: Platform = Field(default=Platform.TOUTIAO, description="平台")


class AccountCreate(AccountBase):
    uid: str = Field(..., max_length=50, description="平台UID")
    cookies: str = Field(..., description="登录Cookie")


class AccountUpdate(BaseModel):
    nickname: Optional[str] = Field(None, max_length=100)
    cookies: Optional[str] = None
    status: Optional[AccountStatus] = None


class AccountResponse(AccountBase):
    id: UUID
    uid: str
    status: AccountStatus
    last_publish_at: Optional[datetime]
    avatar_url: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class AccountListResponse(BaseModel):
    items: List[AccountResponse]
    total: int


class AccountStatusCheck(BaseModel):
    id: UUID
    status: AccountStatus
    is_valid: bool
    message: str
