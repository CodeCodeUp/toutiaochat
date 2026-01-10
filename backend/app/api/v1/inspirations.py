"""创作灵感 API"""

from typing import Optional, List
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.inspiration import (
    InspirationTopicResponse,
    InspirationTopicListResponse,
    InspirationTopicOption,
    SyncTopicsRequest,
    SyncTopicsResponse,
    FetchTopicsRequest,
    FetchTopicsResponse,
    UseTopicResponse,
)
from app.services.inspiration_service import inspiration_service

router = APIRouter(prefix="/inspirations", tags=["创作灵感"])


@router.post("/topics/sync", response_model=SyncTopicsResponse, summary="同步话题")
async def sync_topics(
    data: SyncTopicsRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    从头条API同步话题
    - 需要提供一个有效账号的ID，使用其Cookie进行请求
    - 每次获取50个话题，自动去重入库
    """
    result = await inspiration_service.sync_topics(db, data.account_id)

    return SyncTopicsResponse(
        success=True,
        total_fetched=result["total_fetched"],
        new_added=result["new_added"],
        message=f"成功同步 {result['new_added']} 个新话题",
    )


@router.get("/topics", response_model=InspirationTopicListResponse, summary="话题列表")
async def list_topics(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    keyword: Optional[str] = Query(None, description="搜索关键词"),
    sort_by: str = Query(
        "created_at",
        description="排序字段",
        regex="^(usage_count|read_count|talk_count|created_at)$",
    ),
    sort_order: str = Query("desc", description="排序方向", regex="^(asc|desc)$"),
    db: AsyncSession = Depends(get_db),
):
    """
    获取话题列表

    排序字段:
    - usage_count: 使用次数
    - read_count: 阅读数
    - talk_count: 讨论数
    - created_at: 创建时间
    """
    items, total = await inspiration_service.get_topics(
        db,
        page=page,
        page_size=page_size,
        keyword=keyword,
        sort_by=sort_by,
        sort_order=sort_order,
    )

    return InspirationTopicListResponse(items=items, total=total)


@router.get("/topics/options", response_model=List[InspirationTopicOption], summary="话题选项")
async def get_topic_options(
    keyword: Optional[str] = Query(None, description="搜索关键词"),
    limit: int = Query(20, ge=1, le=50, description="返回数量"),
    db: AsyncSession = Depends(get_db),
):
    """
    获取话题选项（用于下拉选择）
    - 按使用次数和创建时间排序
    - 返回简化的数据结构
    """
    items = await inspiration_service.get_topic_options(db, keyword=keyword, limit=limit)
    return items


@router.post("/topics/{topic_id}/use", response_model=UseTopicResponse, summary="使用话题")
async def use_topic(
    topic_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """
    使用话题
    - 增加使用次数
    - 返回话题名称供调用方使用
    """
    topic = await inspiration_service.use_topic(db, topic_id)

    return UseTopicResponse(
        forum_name=topic.forum_name,
        usage_count=topic.usage_count,
    )


@router.delete("/topics/{topic_id}", summary="删除话题")
async def delete_topic(
    topic_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """
    删除话题（逻辑删除）
    - 删除后不会真正删除，而是标记为已删除
    - 下次同步时遇到相同话题也不会恢复
    """
    await inspiration_service.delete_topic(db, topic_id)
    return {"success": True, "message": "话题已删除"}


@router.post("/topics/fetch", response_model=FetchTopicsResponse, summary="实时获取话题")
async def fetch_topics(
    data: FetchTopicsRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    实时获取话题（手动触发）
    - 需要提供一个有效账号的ID，使用其Cookie进行请求
    - 通过 offset 控制获取位置，每次获取50个
    - 返回下次请求的 offset 值
    """
    result = await inspiration_service.fetch_topics(db, data.account_id, data.offset)

    return FetchTopicsResponse(
        success=True,
        total_fetched=result["total_fetched"],
        new_added=result["new_added"],
        offset=result["offset"],
        message=f"成功获取 {result['total_fetched']} 个话题，新增 {result['new_added']} 个",
    )
