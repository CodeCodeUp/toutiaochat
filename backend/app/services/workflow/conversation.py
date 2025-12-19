"""对话上下文管理器"""

from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.conversation_message import ConversationMessage


class ConversationManager:
    """对话上下文管理器 - 管理工作流各阶段的对话历史"""

    async def add_message(
        self,
        db: AsyncSession,
        session_id: UUID,
        stage: str,
        role: str,
        content: str,
        extra_data: dict | None = None,
    ) -> ConversationMessage:
        """
        保存单条消息

        Args:
            db: 数据库会话
            session_id: 工作流会话ID
            stage: 阶段名称
            role: 消息角色 (user/assistant/system)
            content: 消息内容
            extra_data: 额外元数据

        Returns:
            保存的消息对象
        """
        message = ConversationMessage(
            session_id=session_id,
            stage=stage,
            role=role,
            content=content,
            extra_data=extra_data or {},
        )
        db.add(message)
        await db.flush()
        return message

    async def get_history(
        self,
        db: AsyncSession,
        session_id: UUID,
        stage: str,
        limit: int = 50,
    ) -> list[dict]:
        """
        获取指定阶段的对话历史

        Args:
            db: 数据库会话
            session_id: 工作流会话ID
            stage: 阶段名称
            limit: 返回消息数量限制

        Returns:
            消息列表
        """
        result = await db.execute(
            select(ConversationMessage)
            .where(
                ConversationMessage.session_id == session_id,
                ConversationMessage.stage == stage,
            )
            .order_by(ConversationMessage.created_at.asc())
            .limit(limit)
        )
        messages = result.scalars().all()

        return [
            {
                "id": str(msg.id),
                "role": msg.role,
                "content": msg.content,
                "created_at": msg.created_at.isoformat(),
                "extra_data": msg.extra_data,
            }
            for msg in messages
        ]

    async def get_all_messages(
        self,
        db: AsyncSession,
        session_id: UUID,
        limit: int = 100,
    ) -> list[dict]:
        """
        获取会话的所有对话历史

        Args:
            db: 数据库会话
            session_id: 工作流会话ID
            limit: 返回消息数量限制

        Returns:
            消息列表
        """
        result = await db.execute(
            select(ConversationMessage)
            .where(ConversationMessage.session_id == session_id)
            .order_by(ConversationMessage.created_at.asc())
            .limit(limit)
        )
        messages = result.scalars().all()

        return [
            {
                "id": str(msg.id),
                "stage": msg.stage,
                "role": msg.role,
                "content": msg.content,
                "created_at": msg.created_at.isoformat(),
                "extra_data": msg.extra_data,
            }
            for msg in messages
        ]

    async def build_openai_messages(
        self,
        db: AsyncSession,
        session_id: UUID,
        stage: str,
        system_prompt: str | None = None,
    ) -> list[dict]:
        """
        构建 OpenAI API 所需的 messages 格式

        Args:
            db: 数据库会话
            session_id: 工作流会话ID
            stage: 阶段名称
            system_prompt: 可选的系统提示词

        Returns:
            OpenAI messages 格式列表
        """
        history = await self.get_history(db, session_id, stage)

        messages = []

        # 添加系统提示词
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        # 添加历史消息
        for msg in history:
            if msg["role"] in ("user", "assistant"):
                messages.append({
                    "role": msg["role"],
                    "content": msg["content"]
                })

        return messages

    async def get_message_count(
        self,
        db: AsyncSession,
        session_id: UUID,
        stage: str | None = None,
    ) -> int:
        """
        获取消息数量

        Args:
            db: 数据库会话
            session_id: 工作流会话ID
            stage: 可选的阶段过滤

        Returns:
            消息数量
        """
        from sqlalchemy import func

        query = select(func.count(ConversationMessage.id)).where(
            ConversationMessage.session_id == session_id
        )
        if stage:
            query = query.where(ConversationMessage.stage == stage)

        result = await db.execute(query)
        return result.scalar() or 0


# 导出单例
conversation_mgr = ConversationManager()
