from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.core.database import get_db
from app.core.exceptions import NotFoundException, AppException
from app.models import Article, ArticleStatus
from app.schemas.article import (
    ArticleCreate,
    ArticleUpdate,
    ArticleResponse,
    ArticleListResponse,
)
from app.services.ai_writer import ai_writer

router = APIRouter(prefix="/articles", tags=["文章管理"])


@router.post("", response_model=ArticleResponse, summary="创建文章(AI生成)")
async def create_article(
    data: ArticleCreate,
    db: AsyncSession = Depends(get_db),
):
    """根据话题使用AI生成文章"""
    result = await ai_writer.generate_article(
        topic=data.topic,
        category=data.category.value,
    )

    if data.auto_humanize:
        humanized = await ai_writer.humanize_article(
            title=result["title"],
            content=result["content"],
        )
        result["title"] = humanized["title"]
        result["content"] = humanized["content"]
        result["token_usage"] += humanized.get("token_usage", 0)

    article = Article(
        title=result["title"],
        content=result["content"],
        original_topic=data.topic,
        image_prompts=result.get("image_prompts", []),
        category=data.category,
        account_id=data.account_id,
        ai_model=ai_writer.model,
        token_usage=result["token_usage"],
        status=ArticleStatus.DRAFT,
    )

    db.add(article)
    await db.commit()
    await db.refresh(article)

    return article


@router.get("", response_model=ArticleListResponse, summary="文章列表")
async def list_articles(
    status: Optional[ArticleStatus] = Query(None, description="状态筛选"),
    account_id: Optional[UUID] = Query(None, description="账号筛选"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """获取文章列表"""
    query = select(Article)

    if status:
        query = query.where(Article.status == status)
    if account_id:
        query = query.where(Article.account_id == account_id)

    query = query.order_by(Article.created_at.desc())

    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query)

    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    items = result.scalars().all()

    return ArticleListResponse(
        items=items,
        total=total or 0,
        page=page,
        page_size=page_size,
    )


@router.get("/{article_id}", response_model=ArticleResponse, summary="文章详情")
async def get_article(
    article_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """获取文章详情"""
    result = await db.execute(select(Article).where(Article.id == article_id))
    article = result.scalar_one_or_none()

    if not article:
        raise NotFoundException("Article")

    return article


@router.put("/{article_id}", response_model=ArticleResponse, summary="更新文章")
async def update_article(
    article_id: UUID,
    data: ArticleUpdate,
    db: AsyncSession = Depends(get_db),
):
    """更新文章(仅草稿状态可编辑)"""
    result = await db.execute(select(Article).where(Article.id == article_id))
    article = result.scalar_one_or_none()

    if not article:
        raise NotFoundException("Article")

    if article.status != ArticleStatus.DRAFT:
        raise AppException("只有草稿状态的文章可以编辑")

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(article, field, value)

    await db.commit()
    await db.refresh(article)

    return article


@router.delete("/{article_id}", summary="删除文章")
async def delete_article(
    article_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """删除文章"""
    result = await db.execute(select(Article).where(Article.id == article_id))
    article = result.scalar_one_or_none()

    if not article:
        raise NotFoundException("Article")

    await db.delete(article)
    await db.commit()

    return {"message": "删除成功"}


@router.post("/{article_id}/publish", response_model=ArticleResponse, summary="发布文章")
async def publish_article(
    article_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """发布文章到头条"""
    result = await db.execute(select(Article).where(Article.id == article_id))
    article = result.scalar_one_or_none()

    if not article:
        raise NotFoundException("Article")

    if article.status not in [ArticleStatus.DRAFT, ArticleStatus.FAILED]:
        raise AppException("只有草稿或失败状态的文章可以发布")

    if not article.account_id:
        raise AppException("请先选择发布账号")

    # 更新状态为发布中
    article.status = ArticleStatus.PUBLISHING
    await db.commit()
    await db.refresh(article)

    # TODO: 创建发布任务，异步执行发布
    # 这里先返回，实际发布由后台任务完成

    return article


@router.post("/{article_id}/regenerate", response_model=ArticleResponse, summary="重新生成")
async def regenerate_article(
    article_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """重新生成文章内容"""
    result = await db.execute(select(Article).where(Article.id == article_id))
    article = result.scalar_one_or_none()

    if not article:
        raise NotFoundException("Article")

    if not article.original_topic:
        raise AppException("原始话题不存在，无法重新生成")

    new_result = await ai_writer.generate_article(
        topic=article.original_topic,
        category=article.category.value,
    )

    article.title = new_result["title"]
    article.content = new_result["content"]
    article.image_prompts = new_result.get("image_prompts", [])
    article.token_usage += new_result["token_usage"]
    article.status = ArticleStatus.DRAFT

    await db.commit()
    await db.refresh(article)

    return article
