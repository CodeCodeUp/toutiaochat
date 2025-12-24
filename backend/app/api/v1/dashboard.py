"""仪表盘统计 API"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.core.database import get_db
from app.models import Article, ArticleStatus, Account

router = APIRouter(prefix="/dashboard", tags=["仪表盘"])


@router.get("/stats", summary="获取仪表盘统计数据")
async def get_dashboard_stats(
    db: AsyncSession = Depends(get_db),
):
    """获取仪表盘统计数据"""
    # 文章总数
    total_articles = await db.scalar(select(func.count(Article.id)))

    # 已发布数
    published_count = await db.scalar(
        select(func.count(Article.id)).where(Article.status == ArticleStatus.PUBLISHED)
    )

    # 待发布数 (草稿)
    draft_count = await db.scalar(
        select(func.count(Article.id)).where(Article.status == ArticleStatus.DRAFT)
    )

    # 账号总数
    account_count = await db.scalar(select(func.count(Account.id)))

    return {
        "total_articles": total_articles or 0,
        "published_count": published_count or 0,
        "draft_count": draft_count or 0,
        "account_count": account_count or 0,
    }
