"""阶段处理器基类"""

from abc import ABC, abstractmethod
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.workflow_session import WorkflowSession


class StageResult:
    """阶段处理结果"""

    def __init__(
        self,
        reply: str,
        can_proceed: bool = True,
        article_preview: dict | None = None,
        suggestions: list[str] | None = None,
        extra_data: dict | None = None,
    ):
        self.reply = reply
        self.can_proceed = can_proceed
        self.article_preview = article_preview or {}
        self.suggestions = suggestions or []
        self.extra_data = extra_data or {}

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "reply": self.reply,
            "can_proceed": self.can_proceed,
            "article_preview": self.article_preview,
            "suggestions": self.suggestions,
        }


class BaseStage(ABC):
    """
    阶段处理器抽象基类

    每个阶段（生成、优化、生图）都需要实现这个基类，
    负责处理该阶段的用户消息和自动执行逻辑。
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """阶段名称"""
        raise NotImplementedError

    @property
    def default_suggestions(self) -> list[str]:
        """默认的操作建议"""
        return []

    @abstractmethod
    async def process(
        self,
        db: AsyncSession,
        session: WorkflowSession,
        user_message: str,
        history: list[dict],
        prompt_id: str | None = None,
    ) -> StageResult:
        """
        处理用户消息

        Args:
            db: 数据库会话
            session: 工作流会话
            user_message: 用户消息
            history: 历史对话记录
            prompt_id: 可选的提示词ID

        Returns:
            StageResult: 包含 AI 回复和处理结果
        """
        raise NotImplementedError

    @abstractmethod
    async def auto_execute(
        self,
        db: AsyncSession,
        session: WorkflowSession,
    ) -> StageResult:
        """
        自动模式下的执行逻辑

        Args:
            db: 数据库会话
            session: 工作流会话

        Returns:
            StageResult: 执行结果
        """
        raise NotImplementedError

    @abstractmethod
    async def snapshot(
        self,
        db: AsyncSession,
        session: WorkflowSession,
    ) -> dict:
        """
        保存当前阶段的快照数据

        Args:
            db: 数据库会话
            session: 工作流会话

        Returns:
            dict: 快照数据
        """
        raise NotImplementedError

    async def can_proceed(
        self,
        db: AsyncSession,
        session: WorkflowSession,
    ) -> bool:
        """
        判断是否可进入下一阶段

        Args:
            db: 数据库会话
            session: 工作流会话

        Returns:
            bool: 是否可以进入下一阶段
        """
        return True

    async def validate(
        self,
        db: AsyncSession,
        session: WorkflowSession,
    ) -> tuple[bool, str | None]:
        """
        验证阶段状态是否有效

        Args:
            db: 数据库会话
            session: 工作流会话

        Returns:
            tuple: (是否有效, 错误消息)
        """
        return True, None
