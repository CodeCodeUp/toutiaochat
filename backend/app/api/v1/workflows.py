"""工作流 API 路由"""

from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import AIServiceException
from app.models.workflow_session import WorkflowMode
from app.models.prompt import ContentType
from app.services.workflow import workflow_engine, conversation_mgr
from app.schemas.workflow import (
    WorkflowCreateRequest,
    WorkflowCreateResponse,
    WorkflowMessageRequest,
    WorkflowMessageResponse,
    WorkflowStageChangeResponse,
    WorkflowAutoResponse,
    WorkflowStatusResponse,
    WorkflowDetailResponse,
    WorkflowMessagesResponse,
    ArticlePreview,
    ConversationMessageSchema,
)

router = APIRouter(prefix="/workflows", tags=["workflows"])


@router.post("/sessions", response_model=WorkflowCreateResponse)
async def create_session(
    request: WorkflowCreateRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    创建工作流会话

    创建一个新的工作流会话，包括：
    - 创建关联的文章（草稿状态）
    - 初始化工作流状态（从生成阶段开始）
    """
    try:
        mode = WorkflowMode(request.mode)
        content_type = ContentType(request.content_type)
        result = await workflow_engine.create_session(
            db=db,
            mode=mode,
            content_type=content_type,
            custom_topic=request.custom_topic,
        )
        return WorkflowCreateResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/sessions/{session_id}/messages", response_model=WorkflowMessageResponse)
async def send_message(
    session_id: UUID,
    request: WorkflowMessageRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    发送消息（半自动模式）

    向当前阶段发送用户消息，AI 将根据消息内容进行处理。
    """
    try:
        result = await workflow_engine.process_message(
            db=db,
            session_id=session_id,
            user_message=request.message,
            prompt_id=request.use_prompt_id,
        )

        # 转换 article_preview
        article_preview = None
        if result.get("article_preview"):
            article_preview = ArticlePreview(**result["article_preview"])

        return WorkflowMessageResponse(
            assistant_reply=result["assistant_reply"],
            stage=result["stage"],
            can_proceed=result["can_proceed"],
            article_preview=article_preview,
            suggestions=result.get("suggestions", []),
        )
    except AIServiceException as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sessions/{session_id}/next-stage", response_model=WorkflowStageChangeResponse)
async def next_stage(
    session_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """
    进入下一阶段

    保存当前阶段快照并切换到下一阶段。
    自动返回新阶段的初始提示。
    """
    try:
        result = await workflow_engine.next_stage(db=db, session_id=session_id)

        # 转换 article_preview
        article_preview = None
        if result.get("article_preview"):
            article_preview = ArticlePreview(**result["article_preview"])

        return WorkflowStageChangeResponse(
            previous_stage=result["previous_stage"],
            current_stage=result["current_stage"],
            snapshot_saved=result.get("snapshot_saved", True),
            initial_reply=result.get("initial_reply"),
            article_preview=article_preview,
            suggestions=result.get("suggestions", []),
        )
    except AIServiceException as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sessions/{session_id}/execute-auto", response_model=WorkflowAutoResponse)
async def execute_auto(
    session_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """
    执行全自动流程

    按顺序执行所有阶段（生成 -> 优化 -> 图片 -> 完成）。
    """
    try:
        result = await workflow_engine.execute_auto(db=db, session_id=session_id)
        return WorkflowAutoResponse(**result)
    except AIServiceException as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sessions/{session_id}/status", response_model=WorkflowStatusResponse)
async def get_session_status(
    session_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """
    查询会话状态（用于轮询）

    返回当前会话的状态、进度和结果。
    """
    try:
        result = await workflow_engine.get_session_status(db=db, session_id=session_id)
        return WorkflowStatusResponse(**result)
    except AIServiceException as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sessions/{session_id}", response_model=WorkflowDetailResponse)
async def get_session_detail(
    session_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """
    获取会话详情

    返回完整的会话信息，包括文章内容和对话历史。
    """
    try:
        result = await workflow_engine.get_session_detail(db=db, session_id=session_id)
        return WorkflowDetailResponse(**result)
    except AIServiceException as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sessions/{session_id}/messages", response_model=WorkflowMessagesResponse)
async def get_session_messages(
    session_id: UUID,
    stage: str | None = Query(default=None, description="过滤阶段"),
    limit: int = Query(default=50, ge=1, le=200, description="返回数量限制"),
    db: AsyncSession = Depends(get_db),
):
    """
    获取对话历史

    返回指定会话的对话消息列表。
    """
    try:
        if stage:
            messages = await conversation_mgr.get_history(
                db=db, session_id=session_id, stage=stage, limit=limit
            )
        else:
            messages = await conversation_mgr.get_all_messages(
                db=db, session_id=session_id, limit=limit
            )

        return WorkflowMessagesResponse(
            messages=[ConversationMessageSchema(**msg) for msg in messages],
            total=len(messages),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
