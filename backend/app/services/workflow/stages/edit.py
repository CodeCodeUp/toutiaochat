"""编辑预览阶段处理器"""

import re
from openai import AsyncOpenAI
import structlog
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.services.workflow.stages.base import BaseStage, StageResult
from app.models.workflow_session import WorkflowSession
from app.models import Article
from app.models.ai_config import AIConfig, AIConfigType
from app.core.exceptions import AIServiceException
from app.services.docx_generator import docx_generator

logger = structlog.get_logger()


class EditStage(BaseStage):
    """
    编辑预览阶段处理器

    负责处理最终编辑预览相关的对话，支持：
    - 生成完整的 DOCX 预览文件
    - 支持文本微调
    - 确认后保存最终版本
    """

    @property
    def name(self) -> str:
        return "edit"

    @property
    def default_suggestions(self) -> list[str]:
        return [
            "下载预览文档",
            "修改标题",
            "修改某段内容",
            "确认完成",
        ]

    async def _get_ai_config(self, db: AsyncSession) -> AIConfig | None:
        """获取 AI 配置（用于文本微调）"""
        result = await db.execute(
            select(AIConfig).where(AIConfig.type == AIConfigType.ARTICLE_GENERATE.value)
        )
        return result.scalar_one_or_none()

    def _generate_docx(self, article: Article) -> str:
        """生成 DOCX 预览文件"""
        return docx_generator.create_preview_docx(
            title=article.title,
            content=article.content,
            images=article.images if article.images else None,
            article_id=str(article.id),
        )

    def _parse_user_intent(self, message: str) -> dict:
        """解析用户意图"""
        message_lower = message.lower()

        # 下载/预览
        if any(kw in message_lower for kw in ["下载", "预览", "docx", "文档"]):
            return {"action": "download"}

        # 确认完成
        if any(kw in message_lower for kw in ["确认", "完成", "没问题", "可以了", "确定"]):
            return {"action": "confirm"}

        # 修改标题
        if any(kw in message_lower for kw in ["标题", "题目"]):
            # 尝试提取新标题
            patterns = [
                r"标题[改为成换到：:]+[「『""]?(.+?)[」』""]?$",
                r"改[为成][:：]?[「『""]?(.+?)[」』""]?$",
            ]
            for pattern in patterns:
                match = re.search(pattern, message)
                if match:
                    return {"action": "edit_title", "new_title": match.group(1).strip()}
            return {"action": "edit_title", "new_title": None}

        # 修改段落
        if any(kw in message_lower for kw in ["修改", "调整", "改一下"]):
            match = re.search(r"第\s*(\d+)\s*段", message)
            if match:
                para_num = int(match.group(1))
                return {"action": "edit_paragraph", "paragraph": para_num, "request": message}
            return {"action": "edit_content", "request": message}

        # 直接输入新标题（较短的输入）
        if len(message) < 50 and not any(c in message for c in ["\n", "。", "，"]):
            return {"action": "maybe_title", "text": message}

        return {"action": "unknown"}

    async def _edit_paragraph(
        self,
        db: AsyncSession,
        content: str,
        para_num: int,
        request: str,
    ) -> str:
        """使用 AI 修改指定段落"""
        config = await self._get_ai_config(db)
        if not config or not config.api_key:
            return content

        paragraphs = content.split('\n')
        if para_num < 1 or para_num > len(paragraphs):
            return content

        target_para = paragraphs[para_num - 1]

        client = AsyncOpenAI(api_key=config.api_key, base_url=config.api_url or None)

        try:
            response = await client.chat.completions.create(
                model=config.model,
                messages=[
                    {
                        "role": "system",
                        "content": "你是文章编辑专家。根据用户要求修改指定段落，只返回修改后的段落文本，不要返回其他内容。"
                    },
                    {
                        "role": "user",
                        "content": f"原段落：\n{target_para}\n\n用户要求：{request}\n\n请返回修改后的段落："
                    },
                ],
                temperature=0.7,
            )

            new_para = response.choices[0].message.content.strip()
            paragraphs[para_num - 1] = new_para
            return '\n'.join(paragraphs)

        except Exception as e:
            logger.error("edit_paragraph_error", error=str(e))
            return content

    async def process(
        self,
        db: AsyncSession,
        session: WorkflowSession,
        user_message: str,
        history: list[dict],
        prompt_id: str | None = None,
    ) -> StageResult:
        """处理用户消息"""
        article = await db.get(Article, session.article_id)
        if not article:
            raise AIServiceException("关联文章不存在")

        # 首次进入：生成预览并提示
        if not history:
            try:
                docx_path = self._generate_docx(article)
                docx_url = f"/api/v1/articles/{article.id}/preview-docx"

                image_count = len(article.images) if article.images else 0
                para_count = len([p for p in article.content.split('\n') if p.strip()])

                return StageResult(
                    reply=f"已生成预览文档，包含：\n- 标题：{article.title}\n- 正文：{para_count} 段\n- 配图：{image_count} 张\n\n您可以：\n- 点击「下载预览文档」查看完整效果\n- 输入「修改标题为 xxx」调整标题\n- 输入「修改第N段 + 要求」调整内容\n- 输入「确认完成」结束编辑",
                    can_proceed=True,
                    article_preview={
                        "title": article.title,
                        "content": article.content[:500] + "..." if len(article.content) > 500 else article.content,
                        "images": article.images or [],
                        "docx_url": docx_url,
                    },
                    suggestions=self.default_suggestions,
                    extra_data={"docx_path": docx_path},
                )
            except Exception as e:
                return StageResult(
                    reply=f"生成预览文档失败：{str(e)}\n\n您仍可以进行文本编辑或直接确认完成。",
                    can_proceed=True,
                    suggestions=["确认完成", "修改标题", "修改内容"],
                )

        # 解析用户意图
        intent = self._parse_user_intent(user_message)
        action = intent.get("action")

        # 下载预览
        if action == "download":
            try:
                docx_path = self._generate_docx(article)
                docx_url = f"/api/v1/articles/{article.id}/preview-docx"

                return StageResult(
                    reply=f"预览文档已生成，请点击下载查看。",
                    can_proceed=True,
                    article_preview={
                        "title": article.title,
                        "docx_url": docx_url,
                    },
                    suggestions=["确认完成", "继续修改"],
                    extra_data={"docx_path": docx_path, "docx_url": docx_url},
                )
            except Exception as e:
                return StageResult(
                    reply=f"生成文档失败：{str(e)}",
                    can_proceed=True,
                    suggestions=self.default_suggestions,
                )

        # 确认完成
        if action == "confirm":
            # 生成最终 DOCX
            try:
                final_docx_path = self._generate_docx(article)

                # 保存路径到 stage_data
                stage_data = session.stage_data or {}
                stage_data["final_docx_path"] = final_docx_path
                session.stage_data = stage_data
                await db.commit()

                return StageResult(
                    reply=f"编辑完成！文章《{article.title}》已准备就绪。\n\n您可以进入下一阶段进行发布，或在「文章管理」中查看和发布此文章。",
                    can_proceed=True,
                    article_preview={
                        "title": article.title,
                        "content": article.content,
                        "images": article.images or [],
                        "docx_url": f"/api/v1/articles/{article.id}/preview-docx",
                    },
                    suggestions=["发布文章", "返回文章列表"],
                    extra_data={"completed": True},
                )
            except Exception as e:
                return StageResult(
                    reply=f"生成最终文档时出错：{str(e)}，但文章内容已保存。",
                    can_proceed=True,
                    suggestions=["重试", "仍然完成"],
                )

        # 修改标题
        if action == "edit_title":
            new_title = intent.get("new_title")
            if not new_title:
                return StageResult(
                    reply=f"当前标题：{article.title}\n\n请输入新标题，例如：「标题改为 xxx」",
                    can_proceed=True,
                    suggestions=["保持原标题", "确认完成"],
                )

            article.title = new_title
            await db.commit()

            return StageResult(
                reply=f"标题已修改为：{new_title}",
                can_proceed=True,
                article_preview={
                    "title": article.title,
                },
                suggestions=["下载预览", "继续修改", "确认完成"],
            )

        # 可能是新标题
        if action == "maybe_title":
            text = intent.get("text", "")
            return StageResult(
                reply=f"您是否想将标题改为「{text}」？\n\n如果是，请回复「确认」；如果不是，请告诉我您想做什么。",
                can_proceed=True,
                suggestions=[f"标题改为 {text}", "不是，我想修改内容", "确认完成"],
            )

        # 修改段落
        if action == "edit_paragraph":
            para_num = intent.get("paragraph", 1)
            request = intent.get("request", "")

            paragraphs = article.content.split('\n')
            if para_num < 1 or para_num > len(paragraphs):
                return StageResult(
                    reply=f"文章共有 {len(paragraphs)} 段，请指定有效的段落号。",
                    can_proceed=True,
                    suggestions=self.default_suggestions,
                )

            new_content = await self._edit_paragraph(db, article.content, para_num, request)
            article.content = new_content
            await db.commit()

            new_para = new_content.split('\n')[para_num - 1]
            return StageResult(
                reply=f"第 {para_num} 段已修改：\n\n{new_para[:200]}{'...' if len(new_para) > 200 else ''}",
                can_proceed=True,
                article_preview={
                    "title": article.title,
                    "content": article.content[:500] + "...",
                },
                suggestions=["下载预览", "继续修改", "确认完成"],
            )

        # 通用内容修改
        if action == "edit_content":
            request = intent.get("request", user_message)
            return StageResult(
                reply=f"请告诉我您想修改哪个部分：\n- 「修改标题为 xxx」\n- 「修改第N段 + 具体要求」\n\n当前文章共 {len(article.content.split(chr(10)))} 段。",
                can_proceed=True,
                suggestions=["修改标题", "修改第1段", "修改第2段", "确认完成"],
            )

        # 未识别
        return StageResult(
            reply=f"抱歉，我没有理解您的意图。\n\n您可以：\n- 「下载预览」查看文档\n- 「修改标题为 xxx」\n- 「修改第N段 + 要求」\n- 「确认完成」结束编辑",
            can_proceed=True,
            suggestions=self.default_suggestions,
        )

    async def auto_execute(
        self,
        db: AsyncSession,
        session: WorkflowSession,
    ) -> StageResult:
        """自动模式执行（跳过编辑，直接生成最终文档）"""
        article = await db.get(Article, session.article_id)
        if not article:
            raise AIServiceException("关联文章不存在")

        try:
            docx_path = self._generate_docx(article)

            # 保存路径
            stage_data = session.stage_data or {}
            stage_data["final_docx_path"] = docx_path
            session.stage_data = stage_data
            await db.commit()

            logger.info(
                "edit_stage_auto",
                session_id=str(session.id),
                article_id=str(article.id),
                docx_path=docx_path,
            )

            return StageResult(
                reply="编辑阶段已完成，最终文档已生成。",
                can_proceed=True,
                article_preview={
                    "title": article.title,
                    "docx_url": f"/api/v1/articles/{article.id}/preview-docx",
                },
                extra_data={"docx_path": docx_path},
            )

        except Exception as e:
            logger.error("edit_stage_auto_error", error=str(e))
            return StageResult(
                reply=f"编辑阶段完成（文档生成失败：{str(e)}）",
                can_proceed=True,
                extra_data={"error": str(e)},
            )

    async def snapshot(
        self,
        db: AsyncSession,
        session: WorkflowSession,
    ) -> dict:
        """保存阶段快照"""
        article = await db.get(Article, session.article_id)
        if not article:
            return {}

        return {
            "title": article.title,
            "content": article.content,
            "images": article.images or [],
            "completed_at": session.updated_at.isoformat() if session.updated_at else None,
        }

    async def can_proceed(
        self,
        db: AsyncSession,
        session: WorkflowSession,
    ) -> bool:
        """检查是否可进入下一阶段"""
        article = await db.get(Article, session.article_id)
        if not article:
            return False
        # 必须有标题和内容
        return bool(article.title and article.content)
