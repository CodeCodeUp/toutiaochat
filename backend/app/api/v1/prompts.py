from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
from uuid import UUID

from app.core.database import get_db
from app.models.prompt import Prompt, PromptType, ContentType
from app.schemas.prompt import PromptCreate, PromptUpdate, PromptResponse

router = APIRouter(prefix="/prompts", tags=["提示词管理"])


@router.post("", response_model=PromptResponse, status_code=201)
async def create_prompt(
    prompt_data: PromptCreate,
    db: AsyncSession = Depends(get_db)
):
    """创建提示词"""
    prompt = Prompt(**prompt_data.model_dump())
    db.add(prompt)
    await db.commit()
    await db.refresh(prompt)
    return prompt


@router.get("", response_model=List[PromptResponse])
async def list_prompts(
    type: PromptType = None,
    content_type: ContentType = None,
    is_active: str = None,
    db: AsyncSession = Depends(get_db)
):
    """获取提示词列表"""
    query = select(Prompt)

    if type:
        query = query.where(Prompt.type == type)
    if content_type:
        query = query.where(Prompt.content_type == content_type)
    if is_active:
        query = query.where(Prompt.is_active == is_active)

    query = query.order_by(Prompt.created_at.desc())
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/{prompt_id}", response_model=PromptResponse)
async def get_prompt(
    prompt_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """获取提示词详情"""
    result = await db.execute(select(Prompt).where(Prompt.id == prompt_id))
    prompt = result.scalar_one_or_none()

    if not prompt:
        raise HTTPException(status_code=404, detail="提示词不存在")

    return prompt


@router.put("/{prompt_id}", response_model=PromptResponse)
async def update_prompt(
    prompt_id: UUID,
    prompt_data: PromptUpdate,
    db: AsyncSession = Depends(get_db)
):
    """更新提示词"""
    result = await db.execute(select(Prompt).where(Prompt.id == prompt_id))
    prompt = result.scalar_one_or_none()

    if not prompt:
        raise HTTPException(status_code=404, detail="提示词不存在")

    update_data = prompt_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(prompt, field, value)

    await db.commit()
    await db.refresh(prompt)
    return prompt


@router.delete("/{prompt_id}", status_code=204)
async def delete_prompt(
    prompt_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """删除提示词"""
    result = await db.execute(select(Prompt).where(Prompt.id == prompt_id))
    prompt = result.scalar_one_or_none()

    if not prompt:
        raise HTTPException(status_code=404, detail="提示词不存在")

    await db.delete(prompt)
    await db.commit()
    return None


@router.get("/active/{type}", response_model=PromptResponse)
async def get_active_prompt_by_type(
    type: PromptType,
    content_type: ContentType = ContentType.ARTICLE,
    db: AsyncSession = Depends(get_db)
):
    """获取指定类型的激活提示词"""
    result = await db.execute(
        select(Prompt)
        .where(Prompt.type == type, Prompt.content_type == content_type, Prompt.is_active == "true")
        .order_by(Prompt.created_at.desc())
    )
    prompt = result.scalar_one_or_none()

    if not prompt:
        raise HTTPException(status_code=404, detail=f"未找到类型为{type}、内容类型为{content_type}的激活提示词")

    return prompt
