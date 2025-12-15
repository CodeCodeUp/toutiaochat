import json
from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.core.database import get_db
from app.core.exceptions import NotFoundException
from app.models import Account, AccountStatus
from app.schemas.account import (
    AccountCreate,
    AccountUpdate,
    AccountResponse,
    AccountListResponse,
    AccountStatusCheck,
)
from app.services.publisher import publisher

router = APIRouter(prefix="/accounts", tags=["账号管理"])


@router.post("", response_model=AccountResponse, summary="添加账号")
async def create_account(
    data: AccountCreate,
    db: AsyncSession = Depends(get_db),
):
    """添加头条账号"""
    # TODO: 加密Cookie存储
    account = Account(
        nickname=data.nickname,
        uid=data.uid,
        platform=data.platform,
        cookies=data.cookies,  # 应该加密
        status=AccountStatus.ACTIVE,
    )

    db.add(account)
    await db.commit()
    await db.refresh(account)

    return account


@router.get("", response_model=AccountListResponse, summary="账号列表")
async def list_accounts(
    status: Optional[AccountStatus] = Query(None, description="状态筛选"),
    db: AsyncSession = Depends(get_db),
):
    """获取账号列表"""
    query = select(Account)

    if status:
        query = query.where(Account.status == status)

    query = query.order_by(Account.created_at.desc())

    # 总数
    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query)

    result = await db.execute(query)
    items = result.scalars().all()

    return AccountListResponse(items=items, total=total or 0)


@router.get("/{account_id}", response_model=AccountResponse, summary="账号详情")
async def get_account(
    account_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """获取账号详情"""
    result = await db.execute(select(Account).where(Account.id == account_id))
    account = result.scalar_one_or_none()

    if not account:
        raise NotFoundException("Account")

    return account


@router.put("/{account_id}", response_model=AccountResponse, summary="更新账号")
async def update_account(
    account_id: UUID,
    data: AccountUpdate,
    db: AsyncSession = Depends(get_db),
):
    """更新账号信息"""
    result = await db.execute(select(Account).where(Account.id == account_id))
    account = result.scalar_one_or_none()

    if not account:
        raise NotFoundException("Account")

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(account, field, value)

    await db.commit()
    await db.refresh(account)

    return account


@router.delete("/{account_id}", summary="删除账号")
async def delete_account(
    account_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """删除账号"""
    result = await db.execute(select(Account).where(Account.id == account_id))
    account = result.scalar_one_or_none()

    if not account:
        raise NotFoundException("Account")

    await db.delete(account)
    await db.commit()

    return {"message": "删除成功"}


@router.get("/{account_id}/status", response_model=AccountStatusCheck, summary="检查账号状态")
async def check_account_status(
    account_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """检查账号Cookie是否有效"""
    result = await db.execute(select(Account).where(Account.id == account_id))
    account = result.scalar_one_or_none()

    if not account:
        raise NotFoundException("Account")

    # 解析Cookie并检查
    try:
        cookies = json.loads(account.cookies) if account.cookies else []
        check_result = await publisher.check_account_status(
            cookies=cookies,
            platform=account.platform.value,
        )

        # 更新账号状态
        if check_result["valid"]:
            account.status = AccountStatus.ACTIVE
        else:
            account.status = AccountStatus.EXPIRED

        await db.commit()

        return AccountStatusCheck(
            id=account.id,
            status=account.status,
            is_valid=check_result["valid"],
            message=check_result["message"],
        )

    except Exception as e:
        return AccountStatusCheck(
            id=account.id,
            status=AccountStatus.EXPIRED,
            is_valid=False,
            message=str(e),
        )


@router.post("/{account_id}/refresh", response_model=AccountResponse, summary="刷新Cookie")
async def refresh_account_cookie(
    account_id: UUID,
    cookies: str,
    db: AsyncSession = Depends(get_db),
):
    """刷新账号Cookie"""
    result = await db.execute(select(Account).where(Account.id == account_id))
    account = result.scalar_one_or_none()

    if not account:
        raise NotFoundException("Account")

    account.cookies = cookies
    account.status = AccountStatus.ACTIVE

    await db.commit()
    await db.refresh(account)

    return account
