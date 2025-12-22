from sqlalchemy import Column, String, Text, Enum, DateTime
from sqlalchemy.orm import relationship
import enum

from app.models.base import Base, UUIDMixin, TimestampMixin


class AccountStatus(str, enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    EXPIRED = "expired"


class Platform(str, enum.Enum):
    TOUTIAO = "头条号"


class Account(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "accounts"

    nickname = Column(String(100), nullable=False, comment="账号昵称")
    uid = Column(String(50), nullable=False, unique=True, comment="平台UID")
    platform = Column(Enum(Platform), default=Platform.TOUTIAO, comment="平台")
    cookies = Column(Text, nullable=True, comment="登录Cookie(加密)")
    status = Column(Enum(AccountStatus), default=AccountStatus.ACTIVE, comment="状态")
    last_publish_at = Column(DateTime, nullable=True, comment="最后发布时间")
    avatar_url = Column(String(500), nullable=True, comment="头像URL")

    # Relationships
    articles = relationship("Article", back_populates="account")
    tasks = relationship("Task", back_populates="account")
