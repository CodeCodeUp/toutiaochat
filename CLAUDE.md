# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

今日头条自动发文系统 - 基于 FastAPI + Vue 3 的 AI 驱动内容管理与发布平台

**核心功能**: AI 文章生成 → 工作流引擎编排 → Playwright 自动化发布

**内容类型**: 支持「文章」和「微头条」两种内容类型，各阶段根据类型加载对应提示词

## 开发环境配置

### 快速启动

```bash
# 完整环境启动 (推荐用于初次运行)
docker-compose up -d  # 后端端口 8000, 前端端口 3000, 数据库端口 5432

# 本地开发 - 后端
cd backend
pip install -r requirements.txt
# 需要先配置 .env 文件
python -m app.main  # 端口 8100 (与 docker 不同)

# 本地开发 - 前端
cd frontend
npm install
npm run dev  # 端口 5173 (Vite 开发服务器)
```

### 常用命令

```bash
# 后端
cd backend
pytest                           # 运行测试
pytest -k "test_generate"        # 运行匹配的测试

# 前端
cd frontend
npm run build                    # 构建 (vue-tsc + vite build)
npm run lint                     # ESLint 检查
```

### 数据库操作

```bash
cd backend
alembic revision --autogenerate -m "描述变更"
alembic upgrade head            # 应用迁移
alembic downgrade -1            # 回退一个版本

# 直接连接数据库
docker exec -it toutiao_db psql -U postgres -d toutiao
```

## 架构关键点

### 后端架构 (FastAPI)

```
app/
├── api/v1/           # API 路由层
│   ├── articles.py   # 文章 CRUD + 发布
│   ├── accounts.py   # 账号管理 + Cookie 验证
│   ├── workflows.py  # 工作流 API (核心)
│   ├── ai_configs.py # AI 配置管理
│   └── prompts.py    # 提示词模板
├── models/           # SQLAlchemy ORM 模型
│   ├── article.py    # Article (status, content_type)
│   ├── account.py    # Account (加密 cookies)
│   ├── workflow_session.py  # 工作流会话状态
│   ├── ai_config.py  # AI 配置存储
│   └── prompt.py     # 提示词模板 (PromptType, ContentType)
├── services/
│   ├── publisher.py  # Playwright 自动化发布
│   ├── image_gen.py  # 图片生成服务
│   ├── docx_generator.py  # Word 导出
│   └── workflow/     # 工作流引擎 (状态机)
│       ├── engine.py # WorkflowEngine 核心
│       ├── conversation.py  # 对话管理
│       └── stages/   # 阶段处理器
│           ├── generate.py  # 生成阶段
│           ├── optimize.py  # 优化阶段 (去AI化)
│           ├── image.py     # 配图阶段
│           └── edit.py      # 编辑预览阶段
└── core/
    ├── config.py     # Pydantic Settings
    ├── database.py   # AsyncSession 工厂
    └── exceptions.py # 业务异常定义
```

**关键设计模式**:
- **异步优先**: 所有 I/O 操作使用 `async/await`
- **依赖注入**: 使用 `Depends(get_db)` 获取 session
- **状态机**: WorkflowEngine 管理阶段转移 (generate → optimize → image → edit → completed)

### 前端架构 (Vue 3 + TypeScript)

```
src/
├── views/           # 页面组件 (Composition API)
│   ├── ArticleWorkflow.vue  # 工作流主界面 (核心)
│   ├── Articles.vue         # 文章列表
│   ├── Accounts.vue         # 账号管理
│   ├── Prompts.vue          # 提示词模板
│   └── Settings.vue         # 系统配置
├── components/workflow/     # 工作流组件
│   ├── ChatDialog.vue       # 对话界面
│   ├── WorkflowStepper.vue  # 步骤指示器
│   └── AutoProgress.vue     # 自动模式进度
├── stores/workflow.ts       # Pinia 状态管理
└── api/index.ts             # Axios API 封装
```

**技术栈**: Vue 3 + TypeScript + Pinia + Element Plus + Tailwind CSS

## 核心业务流程

### 工作流引擎 (services/workflow/engine.py)

支持两种模式：
- **半自动模式 (manual)**: 每个阶段通过对话交互，用户确认后进入下一阶段
- **全自动模式 (auto)**: 自动执行所有阶段，通过轮询查看进度

```python
# 阶段状态机转移
GENERATE → OPTIMIZE → IMAGE → EDIT → COMPLETED

# 关键 API
POST /api/v1/workflows/sessions                    # 创建会话 (传入 mode, content_type)
POST /api/v1/workflows/sessions/{id}/messages      # 发送消息 (半自动)
POST /api/v1/workflows/sessions/{id}/next-stage    # 进入下一阶段
POST /api/v1/workflows/sessions/{id}/execute-auto  # 执行全自动
GET  /api/v1/workflows/sessions/{id}/status        # 查询状态 (用于轮询)
GET  /api/v1/workflows/sessions/{id}               # 获取详情
```

### 内容类型 (ContentType)

系统支持两种内容类型，在 `app/models/prompt.py` 中定义：
- `ARTICLE` - 文章（有标题，较长内容）
- `WEITOUTIAO` - 微头条（无标题，短内容）

**影响范围**:
- 工作流创建时选择内容类型
- 各阶段处理器根据 `session.content_type` 加载对应提示词
- 发布时根据 `article.content_type` 选择不同发布方式

### 自动化发布 (services/publisher.py)

```python
# 文章发布
publish_to_toutiao(title, content, cookies, images, docx_path)
# URL: https://mp.toutiao.com/profile_v4/graphic/publish

# 微头条发布
publish_weitoutiao(content, cookies, images, docx_path)
# URL: https://mp.toutiao.com/profile_v4/weitoutiao/publish
```

**Playwright 调试**: 设置 `headless=False`，使用 `page.screenshot(path="debug.png")` 截图

### 文章状态机

```
draft → publishing → published (记录 publish_url)
                  ↘ failed (记录 error_message)
```

## 数据库模型

### 核心模型关系
```
WorkflowSession (工作流会话)
  ├── article_id → Article
  ├── mode: auto | manual
  ├── content_type: article | weitoutiao
  ├── current_stage: generate | optimize | image | edit | completed
  └── stage_data: JSONB (阶段快照)

Article (文章)
  ├── content_type: article | weitoutiao
  ├── status: draft | publishing | published | failed
  └── account_id → Account (发布账号)

Prompt (提示词模板)
  ├── type: generate | humanize | image
  ├── content_type: article | weitoutiao
  └── is_active: "true" | "false"

Account (平台账号)
  ├── platform: 头条号
  ├── cookies: TEXT (AES 加密存储)
  └── status: active | inactive | expired
```

## 环境变量

**必须配置** (.env):
```bash
DATABASE_URL=postgresql+asyncpg://...  # 注意使用 asyncpg 驱动
OPENAI_API_KEY=sk-...
SECRET_KEY=...                         # JWT/加密密钥
COOKIE_ENCRYPTION_KEY=...              # 32字节 AES 密钥
```

**可选配置**:
```bash
OPENAI_BASE_URL=...                    # 代理或第三方 API
PUBLISH_INTERVAL_MINUTES=30
MAX_RETRY_COUNT=3
```

## 代码规范

### 后端

1. **异步编程**: 所有 I/O 必须 `async/await`，使用 `httpx` 替代 `requests`
2. **数据库**: 通过 `Depends(get_db)` 注入，使用 ORM 避免原始 SQL
3. **日志**: structlog 结构化日志
   ```python
   logger.info("article_generated", article_id=str(article.id), token_usage=123)
   ```
4. **异常**: 业务异常继承 `core.exceptions`，API 层转 HTTP 状态码

### 前端

1. **Composition API**: 使用 `<script setup lang="ts">`
2. **API 调用**: 统一通过 `src/api/index.ts`
3. **组件**: Element Plus 已全局注册

## 提示词配置格式

### GENERATE 类型（文章生成）

系统提示词需要求 AI 返回以下 JSON 格式：
```json
{
  "title": "文章标题",
  "content": "文章正文...",
  "image_prompts": [
    {"description": "图片描述", "position": "cover"},
    {"description": "图片描述", "position": "after_paragraph:3"},
    {"description": "图片描述", "position": "end"}
  ]
}
```

`position` 可选值：
- `cover` - 封面图
- `after_paragraph:N` - 第N段后（N从1开始）
- `end` - 文章结尾

### IMAGE 类型（图片描述生成）

仅当 GENERATE 阶段未返回 `image_prompts` 时使用，需要求 AI 返回：
```json
{
  "prompts": [
    {"description": "图片描述", "position": "cover"}
  ]
}
```

## 开发指南

### 添加新 API
1. 在 `app/api/v1/` 创建路由文件
2. 在 `app/api/v1/__init__.py` 注册: `api_router.include_router(xxx.router)`
3. 定义 schema (`app/schemas/`) 和 model (`app/models/`)

### 数据库模型变更
1. 修改 `app/models/` 中的模型
2. `alembic revision --autogenerate -m "描述"`
3. `alembic upgrade head`

### 添加前端页面
1. 在 `frontend/src/views/` 创建 `.vue` 文件
2. 在 `frontend/src/router/index.ts` 注册路由

### 添加新的工作流阶段处理器
1. 在 `app/services/workflow/stages/` 创建新的阶段处理器，继承 `BaseStage`
2. 实现 `process()`, `auto_execute()`, `snapshot()`, `can_proceed()` 方法
3. 在 `engine.py` 的 `STAGE_HANDLERS` 和 `STAGE_TRANSITIONS` 中注册

Patchright