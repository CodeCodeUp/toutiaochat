from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.models.ai_config import AIConfig, AIConfigType
from app.schemas.ai_config import AIConfigUpdate, AIConfigResponse

router = APIRouter(prefix="/ai-configs", tags=["AI配置"])


async def get_or_create_config(db: AsyncSession, config_type: AIConfigType) -> AIConfig:
    """获取或创建配置"""
    result = await db.execute(select(AIConfig).where(AIConfig.type == config_type.value))
    config = result.scalar_one_or_none()
    if not config:
        config = AIConfig(type=config_type.value, api_key="", api_url="", model="")
        db.add(config)
        await db.commit()
        await db.refresh(config)
    return config


@router.get("", response_model=dict)
async def get_all_configs(db: AsyncSession = Depends(get_db)):
    """获取所有 AI 配置"""
    configs = {}
    for config_type in AIConfigType:
        config = await get_or_create_config(db, config_type)
        configs[config_type.value] = AIConfigResponse.model_validate(config)
    return {"configs": configs}


@router.get("/{config_type}", response_model=AIConfigResponse)
async def get_config(config_type: AIConfigType, db: AsyncSession = Depends(get_db)):
    """获取指定类型的 AI 配置"""
    config = await get_or_create_config(db, config_type)
    return config


@router.put("/{config_type}", response_model=AIConfigResponse)
async def update_config(
    config_type: AIConfigType,
    update_data: AIConfigUpdate,
    db: AsyncSession = Depends(get_db)
):
    """更新 AI 配置"""
    config = await get_or_create_config(db, config_type)

    update_dict = update_data.model_dump(exclude_unset=True)
    for key, value in update_dict.items():
        setattr(config, key, value)

    await db.commit()
    await db.refresh(config)
    return config
