"""创作灵感服务"""

import json
from typing import Optional, List, Tuple
from uuid import UUID

import httpx
import structlog
from sqlalchemy import select, func, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Account, AccountStatus
from app.models.inspiration import InspirationTopic
from app.core.exceptions import AppException

logger = structlog.get_logger()


class InspirationService:
    """创作灵感服务"""

    TOUTIAO_FORUM_API = "https://mp.toutiao.com/forum/mp/suggest_forum/"
    BATCH_SIZE = 50  # 每次获取50个

    async def sync_topics(self, db: AsyncSession, account_id: UUID) -> dict:
        """
        从头条API同步话题

        Args:
            db: 数据库会话
            account_id: 账号ID（用于获取Cookie）

        Returns:
            dict: {"total_fetched": 获取总数, "new_added": 新增数量}
        """
        # 获取账号
        account = await db.get(Account, account_id)
        if not account:
            raise AppException("账号不存在")
        if account.status != AccountStatus.ACTIVE:
            raise AppException("账号已失效，请先更新Cookie")

        # 解析Cookie
        cookies = self._parse_cookies(account.cookies)
        if not cookies:
            raise AppException("账号Cookie无效")

        # 请求头条API
        try:
            topics_data = await self._fetch_topics(account.uid, cookies)
        except Exception as e:
            logger.error("fetch_topics_failed", error=str(e))
            raise AppException(f"获取话题失败: {str(e)}")

        # 解析并去重入库
        new_count = await self._save_topics(db, topics_data)

        logger.info(
            "topics_synced",
            account_id=str(account_id),
            total_fetched=len(topics_data),
            new_added=new_count,
        )

        return {
            "total_fetched": len(topics_data),
            "new_added": new_count,
        }

    async def sync_topics_auto(self, db: AsyncSession) -> dict:
        """
        自动同步话题（定时任务调用）
        使用第一个活跃账号的Cookie
        """
        # 获取任意一个活跃账号
        result = await db.execute(
            select(Account)
            .where(Account.status == AccountStatus.ACTIVE)
            .limit(1)
        )
        account = result.scalar_one_or_none()

        if not account:
            logger.warning("no_active_account_for_sync")
            return {"total_fetched": 0, "new_added": 0, "error": "没有可用的活跃账号"}

        return await self.sync_topics(db, account.id)

    async def _fetch_topics(self, user_id: str, cookies: dict, offset: int = 0) -> List[dict]:
        """从头条API获取话题"""
        params = {
            "user_id": user_id,
            "offset": offset,
            "count": self.BATCH_SIZE,
        }

        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(
                self.TOUTIAO_FORUM_API,
                params=params,
                cookies=cookies,
            )
            response.raise_for_status()
            data = response.json()

        if data.get("err_no") != 0:
            raise AppException(f"API错误: {data.get('err_tips', '未知错误')}")

        # 提取 hot 数组中的话题
        hot_topics = data.get("data", {}).get("hot", [])
        return [item.get("forum", {}) for item in hot_topics if item.get("forum")]

    async def _save_topics(self, db: AsyncSession, topics: List[dict]) -> int:
        """保存话题，返回新增数量"""
        new_count = 0

        for topic in topics:
            forum_id = str(topic.get("forum_id", ""))
            if not forum_id:
                continue

            # 检查是否已存在
            result = await db.execute(
                select(InspirationTopic).where(InspirationTopic.forum_id == forum_id)
            )
            existing = result.scalar_one_or_none()

            if existing:
                # 已存在：如果已删除则跳过，否则更新统计数据
                if existing.is_deleted:
                    continue
                existing.talk_count = topic.get("talk_count", 0)
                existing.read_count = topic.get("read_count", 0)
                existing.raw_data = topic
            else:
                # 新增
                new_topic = InspirationTopic(
                    forum_id=forum_id,
                    forum_name=topic.get("forum_name", ""),
                    avatar_url=topic.get("avatar_url", ""),
                    talk_count=topic.get("talk_count", 0),
                    read_count=topic.get("read_count", 0),
                    raw_data=topic,
                )
                db.add(new_topic)
                new_count += 1

        await db.commit()
        return new_count

    def _parse_cookies(self, cookies_str: Optional[str]) -> dict:
        """解析Cookie字符串为字典"""
        if not cookies_str:
            return {}

        try:
            cookies_list = json.loads(cookies_str)
            if isinstance(cookies_list, list):
                return {c.get("name"): c.get("value") for c in cookies_list if c.get("name")}
            elif isinstance(cookies_list, dict):
                return cookies_list
        except json.JSONDecodeError:
            pass

        return {}

    async def get_topics(
        self,
        db: AsyncSession,
        page: int = 1,
        page_size: int = 20,
        keyword: Optional[str] = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
    ) -> Tuple[List[InspirationTopic], int]:
        """
        获取话题列表

        Args:
            db: 数据库会话
            page: 页码
            page_size: 每页数量
            keyword: 搜索关键词
            sort_by: 排序字段 (usage_count, read_count, talk_count, created_at)
            sort_order: 排序方向 (asc, desc)

        Returns:
            Tuple[列表, 总数]
        """
        query = select(InspirationTopic).where(InspirationTopic.is_deleted == False)

        # 关键词搜索
        if keyword:
            query = query.where(InspirationTopic.forum_name.ilike(f"%{keyword}%"))

        # 排序
        sort_column = getattr(InspirationTopic, sort_by, InspirationTopic.created_at)
        if sort_order == "desc":
            query = query.order_by(sort_column.desc())
        else:
            query = query.order_by(sort_column.asc())

        # 总数
        count_query = select(func.count()).select_from(query.subquery())
        total = await db.scalar(count_query) or 0

        # 分页
        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)

        result = await db.execute(query)
        items = result.scalars().all()

        return list(items), total

    async def get_topic_options(
        self,
        db: AsyncSession,
        keyword: Optional[str] = None,
        limit: int = 20,
    ) -> List[InspirationTopic]:
        """
        获取话题选项（用于下拉选择）
        """
        query = select(InspirationTopic).where(InspirationTopic.is_deleted == False)

        if keyword:
            query = query.where(InspirationTopic.forum_name.ilike(f"%{keyword}%"))

        # 按使用次数和创建时间排序
        query = query.order_by(
            InspirationTopic.usage_count.desc(),
            InspirationTopic.created_at.desc(),
        ).limit(limit)

        result = await db.execute(query)
        return list(result.scalars().all())

    async def use_topic(self, db: AsyncSession, topic_id: UUID) -> InspirationTopic:
        """
        使用话题（增加使用次数）
        """
        topic = await db.get(InspirationTopic, topic_id)
        if not topic:
            raise AppException("话题不存在")

        topic.usage_count += 1
        await db.commit()
        await db.refresh(topic)

        logger.info("topic_used", topic_id=str(topic_id), usage_count=topic.usage_count)
        return topic

    async def delete_topic(self, db: AsyncSession, topic_id: UUID) -> bool:
        """
        删除话题（逻辑删除）
        """
        topic = await db.get(InspirationTopic, topic_id)
        if not topic:
            raise AppException("话题不存在")

        topic.is_deleted = True
        await db.commit()

        logger.info("topic_deleted", topic_id=str(topic_id), forum_name=topic.forum_name)
        return True

    async def fetch_topics(self, db: AsyncSession, account_id: UUID, offset: int = 0) -> dict:
        """
        实时获取话题（手动触发，支持 offset）

        Args:
            db: 数据库会话
            account_id: 账号ID（用于获取Cookie）
            offset: 偏移量

        Returns:
            dict: {"total_fetched": 获取总数, "new_added": 新增数量, "offset": 下次偏移量}
        """
        # 获取账号
        account = await db.get(Account, account_id)
        if not account:
            raise AppException("账号不存在")
        if account.status != AccountStatus.ACTIVE:
            raise AppException("账号已失效，请先更新Cookie")

        # 解析Cookie
        cookies = self._parse_cookies(account.cookies)
        if not cookies:
            raise AppException("账号Cookie无效")

        # 请求头条API
        try:
            topics_data = await self._fetch_topics(account.uid, cookies, offset)
        except Exception as e:
            logger.error("fetch_topics_failed", error=str(e))
            raise AppException(f"获取话题失败: {str(e)}")

        # 解析并去重入库
        new_count = await self._save_topics(db, topics_data)

        # 计算下次 offset
        next_offset = offset + len(topics_data)

        logger.info(
            "topics_fetched",
            account_id=str(account_id),
            offset=offset,
            total_fetched=len(topics_data),
            new_added=new_count,
        )

        return {
            "total_fetched": len(topics_data),
            "new_added": new_count,
            "offset": next_offset,
        }


# 全局实例
inspiration_service = InspirationService()
