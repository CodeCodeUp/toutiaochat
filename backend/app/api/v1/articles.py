from typing import Optional
from uuid import UUID
import json
from datetime import datetime
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.core.database import get_db
from app.core.exceptions import NotFoundException, AppException
from app.models import Article, ArticleStatus, Account
from app.schemas.article import (
    ArticleCreate,
    ArticleUpdate,
    ArticleResponse,
    ArticleListResponse,
)
from app.services.publisher import publisher
from app.services.docx_generator import docx_generator

router = APIRouter(prefix="/articles", tags=["文章管理"])


@router.post("", response_model=ArticleResponse, summary="创建文章")
async def create_article(
    data: ArticleCreate,
    db: AsyncSession = Depends(get_db),
):
    """创建空白文章（通常通过工作流创建）"""
    article = Article(
        title=data.title,
        content=data.content,
        account_id=data.account_id,
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

    # 获取关联账号
    account_result = await db.execute(select(Account).where(Account.id == article.account_id))
    account = account_result.scalar_one_or_none()

    if not account:
        raise AppException("关联的账号不存在")

    if not account.cookies:
        raise AppException("账号 Cookie 未配置,请先配置账号 Cookie")

    # 更新状态为发布中
    article.status = ArticleStatus.PUBLISHING
    article.error_message = None
    await db.commit()
    await db.refresh(article)

    # 执行发布
    docx_path = None
    try:
        # 解析 Cookie (假设存储为 JSON 字符串)
        try:
            cookies = json.loads(account.cookies)
        except json.JSONDecodeError:
            raise AppException("账号 Cookie 格式错误")

        # 生成 DOCX 文件
        docx_path = docx_generator.create_article_docx(
            title=article.title,
            content=article.content,
            article_id=str(article.id),
        )

        # 调用 publisher 服务发布 (使用 DOCX 导入方式)
        publish_result = await publisher.publish_to_toutiao(
            title=article.title,
            content=article.content,
            cookies=cookies,
            images=article.images if article.images else None,
            docx_path=docx_path,  # 传递 DOCX 文件路径
        )

        # 发布成功
        if publish_result["success"]:
            article.status = ArticleStatus.PUBLISHED
            article.publish_url = publish_result.get("url", "")
            article.published_at = datetime.utcnow()
            article.error_message = None

            # 更新账号最后发布时间
            account.last_publish_at = datetime.utcnow()
        else:
            article.status = ArticleStatus.FAILED
            article.error_message = publish_result.get("message", "发布失败")

    except Exception as e:
        # 发布失败
        article.status = ArticleStatus.FAILED
        article.error_message = str(e)
    finally:
        # 清理临时 DOCX 文件
        if docx_path:
            try:
                import os
                if os.path.exists(docx_path):
                    os.remove(docx_path)
            except:
                pass  # 忽略清理错误

    await db.commit()
    await db.refresh(article)

    return article
