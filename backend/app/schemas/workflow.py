"""工作流 Pydantic Schema"""

from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field
from typing import Optional, Literal, Any


# ========== 图片相关 Schema ==========

class ImagePromptSchema(BaseModel):
    """图片提示词"""
    description: str = Field(..., description="图片描述/提示词")
    position: str = Field(default="end", description="图片位置: cover, after_paragraph:N, end")


class ImageSchema(BaseModel):
    """生成的图片"""
    url: str = Field(..., description="图片访问URL")
    path: str = Field(..., description="图片本地路径")
    position: str = Field(default="end", description="图片位置")
    prompt: str = Field(default="", description="生成该图片使用的提示词")
    index: Optional[int] = Field(default=None, description="图片索引")


# ========== 请求 Schema ==========

class WorkflowCreateRequest(BaseModel):
    """创建工作流请求"""
    mode: Literal["auto", "manual"] = Field(default="manual", description="工作流模式")
    content_type: Literal["article", "weitoutiao"] = Field(default="article", description="内容类型: article-文章, weitoutiao-微头条")


class WorkflowMessageRequest(BaseModel):
    """发送消息请求"""
    message: str = Field(..., min_length=1, max_length=5000, description="用户消息")
    use_prompt_id: Optional[UUID] = Field(default=None, description="使用的提示词ID")


# ========== 响应 Schema ==========

class WorkflowCreateResponse(BaseModel):
    """创建工作流响应"""
    session_id: str
    article_id: str
    stage: str
    mode: str
    content_type: str


class ArticlePreview(BaseModel):
    """文章预览"""
    title: str = ""
    content: str = ""
    full_content: Optional[str] = None
    image_prompts: Optional[list[Any]] = None  # [{description, position}]
    images: Optional[list[Any]] = None  # [{url, path, position, prompt}]
    docx_url: Optional[str] = None


class WorkflowMessageResponse(BaseModel):
    """消息处理响应"""
    assistant_reply: str
    stage: str
    can_proceed: bool
    article_preview: Optional[ArticlePreview] = None
    suggestions: list[str] = []


class WorkflowStageChangeResponse(BaseModel):
    """阶段切换响应"""
    previous_stage: str
    current_stage: str
    snapshot_saved: bool = True
    initial_reply: Optional[str] = None
    article_preview: Optional[ArticlePreview] = None
    suggestions: list[str] = []


class WorkflowAutoResponse(BaseModel):
    """自动执行响应"""
    success: bool
    article_id: Optional[str] = None
    title: Optional[str] = None
    stage: Optional[str] = None
    error: Optional[str] = None


class WorkflowStatusResponse(BaseModel):
    """会话状态响应"""
    session_id: str
    article_id: str
    stage: str
    mode: str
    progress: int
    status: Literal["processing", "completed", "failed"]
    error: Optional[str] = None
    result: Optional[dict] = None


class ConversationMessageSchema(BaseModel):
    """对话消息"""
    id: str
    stage: str
    role: str
    content: str
    created_at: str
    extra_data: Optional[dict] = None


class ArticleDetailSchema(BaseModel):
    """文章详情"""
    title: str
    content: str
    image_prompts: list[Any] = []  # [{description, position}]
    images: list[Any] = []  # [{url, path, position, prompt}]
    token_usage: int = 0


class WorkflowDetailResponse(BaseModel):
    """会话详情响应"""
    session_id: str
    article_id: str
    stage: str
    mode: str
    progress: int
    stage_data: Optional[dict] = None
    error: Optional[str] = None
    created_at: str
    updated_at: str
    article: Optional[ArticleDetailSchema] = None
    messages: list[ConversationMessageSchema] = []


class WorkflowMessagesResponse(BaseModel):
    """对话历史响应"""
    messages: list[ConversationMessageSchema]
    total: int
