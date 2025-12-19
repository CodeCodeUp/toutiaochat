"""图片生成阶段处理器"""

import json
import re
from openai import AsyncOpenAI
import structlog
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.services.workflow.stages.base import BaseStage, StageResult
from app.models.workflow_session import WorkflowSession
from app.models import Article
from app.models.prompt import Prompt, PromptType
from app.models.ai_config import AIConfig, AIConfigType
from app.core.exceptions import AIServiceException
from app.services import image_gen

logger = structlog.get_logger()

# 最大图片数量限制
MAX_IMAGES = 5

# 默认图片提示词生成的系统提示
DEFAULT_IMAGE_SYSTEM_PROMPT = """你是一个专业的图片描述专家。根据文章内容，生成适合作为配图的图片描述。

要求：
1. 每个描述应该具体、详细，便于 AI 绘图模型理解
2. 描述应该与文章内容相关，能够增强文章的可读性
3. 避免生成包含文字的图片描述
4. 描述风格：真实摄影风格或插画风格，根据文章类型选择
5. 最多生成 5 个图片描述

请以 JSON 格式返回：
{
  "prompts": [
    {"description": "图片描述1", "position": "封面/正文"},
    {"description": "图片描述2", "position": "正文"}
  ]
}"""


class ImageStage(BaseStage):
    """
    图片生成阶段处理器

    负责处理图片生成相关的对话，支持：
    - 自动分析文章生成图片提示词
    - 根据提示词生成配图
    - 用户自定义图片需求
    """

    @property
    def name(self) -> str:
        return "image"

    @property
    def default_suggestions(self) -> list[str]:
        return [
            "生成全部配图",
            "只生成封面图",
            "修改图片描述",
            "添加新图片",
            "跳过图片生成",
        ]

    async def _get_ai_config(self, db: AsyncSession) -> AIConfig | None:
        """获取文章生成的 AI 配置（用于生成提示词）"""
        result = await db.execute(
            select(AIConfig).where(AIConfig.type == AIConfigType.ARTICLE_GENERATE.value)
        )
        return result.scalar_one_or_none()

    async def _get_system_prompt(self, db: AsyncSession) -> str:
        """获取图片生成系统提示词"""
        result = await db.execute(
            select(Prompt)
            .where(Prompt.type == PromptType.IMAGE, Prompt.is_active == "true")
            .order_by(Prompt.created_at.desc())
        )
        prompt = result.scalar_one_or_none()
        return prompt.content if prompt else DEFAULT_IMAGE_SYSTEM_PROMPT

    async def _generate_image_prompts(
        self,
        db: AsyncSession,
        article: Article,
    ) -> list[dict]:
        """使用 AI 分析文章内容，生成图片提示词"""
        config = await self._get_ai_config(db)
        if not config or not config.api_key:
            raise AIServiceException("未配置 AI API，无法生成图片提示词")

        system_prompt = await self._get_system_prompt(db)
        client = AsyncOpenAI(api_key=config.api_key, base_url=config.api_url or None)

        user_content = f"请根据以下文章生成配图描述：\n\n标题：{article.title}\n\n正文：{article.content[:3000]}"

        try:
            response = await client.chat.completions.create(
                model=config.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content},
                ],
                temperature=0.7,
                response_format={"type": "json_object"},
            )

            content = response.choices[0].message.content
            # 清理 markdown 代码块
            if content.startswith("```"):
                content = content.split("\n", 1)[1] if "\n" in content else content[3:]
            if content.endswith("```"):
                content = content[:-3]
            content = content.strip()

            result = json.loads(content)
            prompts = result.get("prompts", [])

            # 限制数量
            return prompts[:MAX_IMAGES]

        except Exception as e:
            logger.error("generate_image_prompts_error", error=str(e))
            raise AIServiceException(f"生成图片提示词失败: {str(e)}")

    async def _optimize_prompt(
        self,
        db: AsyncSession,
        original_prompt: str,
        user_request: str,
    ) -> str:
        """根据用户要求优化图片提示词"""
        config = await self._get_ai_config(db)
        if not config or not config.api_key:
            return original_prompt

        client = AsyncOpenAI(api_key=config.api_key, base_url=config.api_url or None)

        try:
            response = await client.chat.completions.create(
                model=config.model,
                messages=[
                    {
                        "role": "system",
                        "content": "你是图片描述优化专家。根据用户要求修改图片描述，返回优化后的描述文本（纯文本，不要JSON）。"
                    },
                    {
                        "role": "user",
                        "content": f"原始描述：{original_prompt}\n\n用户要求：{user_request}\n\n请返回优化后的描述："
                    },
                ],
                temperature=0.7,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error("optimize_prompt_error", error=str(e))
            return original_prompt

    def _parse_user_intent(self, message: str) -> dict:
        """解析用户意图"""
        message_lower = message.lower()

        # 跳过
        if any(kw in message_lower for kw in ["跳过", "不需要", "不用", "算了"]):
            return {"action": "skip"}

        # 生成全部
        if any(kw in message_lower for kw in ["生成全部", "全部生成", "生成所有", "开始生成"]):
            return {"action": "generate_all"}

        # 生成封面
        if any(kw in message_lower for kw in ["封面", "第一张", "第1张"]):
            return {"action": "generate_one", "index": 0}

        # 生成指定图片 (第N张)
        match = re.search(r"第\s*(\d+)\s*张", message)
        if match:
            index = int(match.group(1)) - 1
            return {"action": "generate_one", "index": max(0, index)}

        # 修改提示词
        if any(kw in message_lower for kw in ["修改", "调整", "改一下", "换成"]):
            match = re.search(r"第\s*(\d+)", message)
            index = int(match.group(1)) - 1 if match else 0
            return {"action": "modify_prompt", "index": max(0, index), "request": message}

        # 添加新图片
        if any(kw in message_lower for kw in ["添加", "新增", "加一张"]):
            return {"action": "add_prompt", "description": message}

        # 默认：把用户输入当作新的图片描述
        if len(message) > 10:
            return {"action": "add_prompt", "description": message}

        return {"action": "unknown"}

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

        # 首次进入：检查并生成图片提示词
        if not history and not article.image_prompts:
            try:
                prompts = await self._generate_image_prompts(db, article)
                article.image_prompts = [p["description"] for p in prompts]
                await db.commit()

                prompt_list = "\n".join([f"{i+1}. {p}" for i, p in enumerate(article.image_prompts)])
                return StageResult(
                    reply=f"已根据文章内容生成 {len(article.image_prompts)} 个图片描述：\n\n{prompt_list}\n\n您可以：\n- 输入「生成全部」开始生成\n- 输入「修改第N张」调整描述\n- 输入「跳过」进入下一阶段",
                    can_proceed=True,
                    article_preview={
                        "title": article.title,
                        "image_prompts": article.image_prompts,
                        "images": article.images or [],
                    },
                    suggestions=self.default_suggestions,
                )
            except AIServiceException as e:
                return StageResult(
                    reply=f"自动生成图片描述失败：{str(e)}\n\n您可以手动输入图片描述，或输入「跳过」。",
                    can_proceed=True,
                    suggestions=["跳过图片生成", "手动添加图片描述"],
                )

        # 解析用户意图
        intent = self._parse_user_intent(user_message)
        action = intent.get("action")

        # 跳过
        if action == "skip":
            return StageResult(
                reply="好的，已跳过图片生成阶段。",
                can_proceed=True,
                article_preview={
                    "title": article.title,
                    "images": article.images or [],
                },
                suggestions=["进入下一阶段"],
            )

        # 生成全部图片
        if action == "generate_all":
            prompts = article.image_prompts or []
            if not prompts:
                return StageResult(
                    reply="没有图片描述可供生成。请先添加图片描述。",
                    can_proceed=True,
                    suggestions=["添加图片描述", "跳过图片生成"],
                )

            result = await image_gen.generate_images(
                db, prompts, str(article.id)
            )

            if result["success_count"] > 0:
                # 更新文章图片列表
                article.images = [img["url"] for img in result["images"]]
                await db.commit()

                error_msg = ""
                if result["errors"]:
                    error_msg = f"\n\n失败 {len(result['errors'])} 张：" + ", ".join(
                        [f"第{e['index']+1}张({e['error'][:20]})" for e in result["errors"]]
                    )

                return StageResult(
                    reply=f"图片生成完成！成功 {result['success_count']} 张。{error_msg}",
                    can_proceed=True,
                    article_preview={
                        "title": article.title,
                        "images": article.images,
                        "image_prompts": article.image_prompts,
                    },
                    suggestions=["进入下一阶段", "重新生成失败的图片"],
                    extra_data={"generated_count": result["success_count"]},
                )
            else:
                return StageResult(
                    reply=f"图片生成失败：{result['errors'][0]['error'] if result['errors'] else '未知错误'}",
                    can_proceed=True,
                    suggestions=["重试生成", "跳过图片生成"],
                )

        # 生成单张图片
        if action == "generate_one":
            index = intent.get("index", 0)
            prompts = article.image_prompts or []

            if index >= len(prompts):
                return StageResult(
                    reply=f"没有第 {index+1} 张图片的描述。当前共有 {len(prompts)} 个描述。",
                    can_proceed=True,
                    suggestions=self.default_suggestions,
                )

            result = await image_gen.generate_image(
                db, prompts[index], str(article.id), index
            )

            if result.get("success"):
                # 更新图片列表
                images = list(article.images or [])
                if index < len(images):
                    images[index] = result["url"]
                else:
                    images.append(result["url"])
                article.images = images
                await db.commit()

                return StageResult(
                    reply=f"第 {index+1} 张图片生成成功！",
                    can_proceed=True,
                    article_preview={
                        "title": article.title,
                        "images": article.images,
                    },
                    suggestions=["生成下一张", "生成全部", "进入下一阶段"],
                )
            else:
                return StageResult(
                    reply=f"第 {index+1} 张图片生成失败：{result.get('error', '未知错误')}",
                    can_proceed=True,
                    suggestions=["重试", "修改描述后重试", "跳过"],
                )

        # 修改提示词
        if action == "modify_prompt":
            index = intent.get("index", 0)
            request = intent.get("request", "")
            prompts = list(article.image_prompts or [])

            if index >= len(prompts):
                return StageResult(
                    reply=f"没有第 {index+1} 张图片的描述可供修改。",
                    can_proceed=True,
                    suggestions=self.default_suggestions,
                )

            new_prompt = await self._optimize_prompt(db, prompts[index], request)
            prompts[index] = new_prompt
            article.image_prompts = prompts
            await db.commit()

            return StageResult(
                reply=f"已修改第 {index+1} 张图片描述：\n\n{new_prompt}",
                can_proceed=True,
                article_preview={
                    "title": article.title,
                    "image_prompts": prompts,
                },
                suggestions=["生成这张图片", "继续修改", "生成全部"],
            )

        # 添加新图片描述
        if action == "add_prompt":
            description = intent.get("description", user_message)
            prompts = list(article.image_prompts or [])

            if len(prompts) >= MAX_IMAGES:
                return StageResult(
                    reply=f"已达到最大图片数量限制（{MAX_IMAGES}张）。请先删除现有描述再添加。",
                    can_proceed=True,
                    suggestions=self.default_suggestions,
                )

            # 清理描述（去掉"添加"等词）
            clean_desc = re.sub(r"^(添加|新增|加一张)[：:，,\s]*", "", description).strip()
            if len(clean_desc) < 5:
                return StageResult(
                    reply="图片描述太短，请提供更详细的描述。",
                    can_proceed=True,
                    suggestions=self.default_suggestions,
                )

            prompts.append(clean_desc)
            article.image_prompts = prompts
            await db.commit()

            return StageResult(
                reply=f"已添加第 {len(prompts)} 张图片描述：\n\n{clean_desc}",
                can_proceed=True,
                article_preview={
                    "title": article.title,
                    "image_prompts": prompts,
                },
                suggestions=["生成这张图片", "添加更多", "生成全部"],
            )

        # 未识别的意图
        prompt_list = ""
        if article.image_prompts:
            prompt_list = "\n当前图片描述：\n" + "\n".join(
                [f"{i+1}. {p}" for i, p in enumerate(article.image_prompts)]
            )

        return StageResult(
            reply=f"抱歉，我没有理解您的意图。{prompt_list}\n\n您可以：\n- 「生成全部」- 生成所有配图\n- 「生成第N张」- 生成指定图片\n- 「修改第N张 + 要求」- 修改描述\n- 「跳过」- 进入下一阶段",
            can_proceed=True,
            suggestions=self.default_suggestions,
        )

    async def auto_execute(
        self,
        db: AsyncSession,
        session: WorkflowSession,
    ) -> StageResult:
        """自动模式执行"""
        article = await db.get(Article, session.article_id)
        if not article:
            raise AIServiceException("关联文章不存在")

        # 1. 生成图片提示词（如果没有）
        if not article.image_prompts:
            try:
                prompts = await self._generate_image_prompts(db, article)
                article.image_prompts = [p["description"] for p in prompts]
                await db.commit()
            except Exception as e:
                logger.error("auto_generate_prompts_error", error=str(e))
                # 自动模式下跳过图片生成
                return StageResult(
                    reply="图片生成阶段已完成（跳过：无法生成图片描述）",
                    can_proceed=True,
                    extra_data={"skipped": True, "reason": str(e)},
                )

        # 2. 生成图片
        prompts = article.image_prompts or []
        if not prompts:
            return StageResult(
                reply="图片生成阶段已完成（跳过：无图片描述）",
                can_proceed=True,
                extra_data={"skipped": True},
            )

        result = await image_gen.generate_images(db, prompts, str(article.id))

        if result["success_count"] > 0:
            article.images = [img["url"] for img in result["images"]]
            await db.commit()

        logger.info(
            "image_stage_auto",
            session_id=str(session.id),
            article_id=str(article.id),
            success_count=result["success_count"],
            error_count=len(result["errors"]),
        )

        return StageResult(
            reply=f"图片生成阶段已完成，成功生成 {result['success_count']} 张图片。",
            can_proceed=True,
            article_preview={
                "title": article.title,
                "images": article.images or [],
            },
            extra_data={
                "generated_count": result["success_count"],
                "errors": result["errors"],
            },
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
            "image_prompts": article.image_prompts or [],
            "images": article.images or [],
            "image_count": len(article.images or []),
            "completed_at": session.updated_at.isoformat() if session.updated_at else None,
        }

    async def can_proceed(
        self,
        db: AsyncSession,
        session: WorkflowSession,
    ) -> bool:
        """检查是否可进入下一阶段（图片阶段始终可跳过）"""
        return True
