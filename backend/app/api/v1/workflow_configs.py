from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.models.workflow_config import WorkflowConfig
from app.models.prompt import ContentType
from app.schemas.workflow_config import (
    WorkflowConfigUpdate,
    WorkflowConfigResponse,
    WorkflowConfigListResponse,
)

router = APIRouter(prefix="/workflow-configs", tags=["工作流配置"])


async def get_or_create_config(db: AsyncSession, content_type: ContentType) -> WorkflowConfig:
    """获取或创建配置"""
    result = await db.execute(
        select(WorkflowConfig).where(WorkflowConfig.content_type == content_type)
    )
    config = result.scalar_one_or_none()
    if not config:
        config = WorkflowConfig(
            content_type=content_type,
            enable_custom_topic=False,
            enable_optimize=True,
            enable_image_gen=True,
            enable_auto_publish=False,
            custom_topic="",
        )
        db.add(config)
        await db.commit()
        await db.refresh(config)
    return config


@router.get("", response_model=WorkflowConfigListResponse)
async def get_all_configs(db: AsyncSession = Depends(get_db)):
    """获取所有工作流配置"""
    configs = {}
    for content_type in ContentType:
        config = await get_or_create_config(db, content_type)
        configs[content_type.value] = WorkflowConfigResponse.model_validate(config)
    return {"configs": configs}


@router.get("/{content_type}", response_model=WorkflowConfigResponse)
async def get_config(content_type: ContentType, db: AsyncSession = Depends(get_db)):
    """获取指定内容类型的工作流配置"""
    config = await get_or_create_config(db, content_type)
    return config


@router.put("/{content_type}", response_model=WorkflowConfigResponse)
async def update_config(
    content_type: ContentType,
    update_data: WorkflowConfigUpdate,
    db: AsyncSession = Depends(get_db)
):
    """更新工作流配置"""
    config = await get_or_create_config(db, content_type)

    update_dict = update_data.model_dump(exclude_unset=True)
    for key, value in update_dict.items():
        setattr(config, key, value)

    await db.commit()
    await db.refresh(config)
    return config
