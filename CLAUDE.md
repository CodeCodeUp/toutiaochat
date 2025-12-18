# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

今日头条/百家号自动发文系统 - 基于 FastAPI + Vue 3 的 AI 驱动内容管理与发布平台

**核心功能**: AI 文章生成 → 人工审核 → Playwright 自动化发布

## 开发环境配置

### 快速启动

```bash
# 完整环境启动 (推荐用于初次运行)
docker-compose up -d

# 本地开发 - 后端
cd backend
pip install -r requirements.txt
# 需要先配置 .env 文件
python -m app.main  # 默认端口 8100

# 本地开发 - 前端
cd frontend
npm install
npm run dev  # 默认端口 5173
```

### 测试命令

```bash
# 后端测试
cd backend
pytest                           # 运行所有测试
pytest tests/test_article.py     # 运行单个测试文件
pytest -v                        # 详细输出
pytest -k "test_generate"        # 运行匹配的测试

# 前端
cd frontend
npm run build                    # 构建生产版本
npm run lint                     # 代码检查
```

### 数据库操作

```bash
# 使用 Alembic 进行数据库迁移
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
├── api/v1/          # API 路由层
│   ├── articles.py  # 文章 CRUD + 生成/发布接口
│   ├── accounts.py  # 账号管理 + Cookie 验证
│   ├── tasks.py     # 任务队列状态查询
│   └── prompts.py   # 提示词模板管理
├── models/          # SQLAlchemy ORM 模型
│   ├── base.py      # Base + UUIDMixin + TimestampMixin
│   ├── article.py   # Article 模型 (status: draft/publishing/published/failed)
│   ├── account.py   # Account 模型 (加密 cookies 字段)
│   └── task.py      # Task 模型 (任务队列)
├── schemas/         # Pydantic 数据验证模型
├── services/        # 业务逻辑核心
│   ├── ai_writer.py # OpenAI GPT-4 文章生成
│   ├── publisher.py # Playwright 自动化发布 (关键)
│   └── image_gen.py # 图片生成接口 (预留)
└── core/
    ├── config.py    # Pydantic Settings (从 .env 加载)
    ├── database.py  # AsyncSession 工厂
    └── exceptions.py
```

**关键设计模式**:
- **异步优先**: 所有数据库/网络操作使用 `async/await`
- **依赖注入**: 使用 FastAPI 的 `Depends` 注入 `get_db` session
- **统一异常**: 所有业务异常继承自 `core.exceptions`

### 前端架构 (Vue 3 + TypeScript)

```
src/
├── views/           # 页面组件 (使用 Composition API)
│   ├── Dashboard.vue   # 数据统计看板
│   ├── Articles.vue    # 文章列表 + 编辑器
│   ├── Prompts.vue     # 提示词模板库
│   ├── Accounts.vue    # 账号管理 + Cookie 验证
│   ├── Tasks.vue       # 任务队列监控
│   └── Settings.vue    # 系统配置 (OpenAI key等)
├── api/             # Axios 封装的 API 调用
├── router/          # Vue Router (SPA 路由)
└── components/      # 通用组件 (如有)
```

**状态管理**: 使用 Pinia (代码中已配置但可能未大量使用)

## 核心业务流程

### 1. 文章生成流程 (ai_writer.py)

```python
# services/ai_writer.py 关键方法
generate_article(topic: str) → dict
  ├── 调用 OpenAI GPT-4 生成标题+正文
  ├── 自动生成图片提示词 (用于后续图片生成)
  └── 返回结构化数据 {title, content, image_prompts}

humanize_article(content: str) → str
  └── 使用 GPT 降低 AI 痕迹 (可选步骤)
```

### 2. 自动化发布流程 (publisher.py)

```python
# services/publisher.py - PublisherService 类
publish_to_toutiao(title, content, cookies, images)
  ├── 启动 Playwright Chromium (headless)
  ├── 注入账号 cookies
  ├── 访问 https://mp.toutiao.com/profile_v4/graphic/publish
  ├── 自动填写表单
  │   ├── 标题: textarea[placeholder*="标题"]
  │   ├── 正文: [contenteditable="true"] (使用 keyboard.insert_text 绕过剪贴板)
  │   └── 图片: input[type="file"] (最多3张)
  ├── 点击发布按钮
  └── 检测发布结果 (URL变化/成功提示)

check_account_status(cookies) → {valid: bool}
  └── 验证 Cookie 是否过期
```

**关键技术点**:
- Playwright 选择器可能随头条页面更新而失效,需要定期维护
- Cookie 加密存储使用 `COOKIE_ENCRYPTION_KEY` (AES-256)
- 发布间隔由 `PUBLISH_INTERVAL_MINUTES` 控制 (默认30分钟)

### 3. 文章状态机

```
draft (草稿)
  → publishing (发布中,调用 publisher.py)
    → published (成功,记录 publish_url)
    → failed (失败,记录 error,可重试最多 MAX_RETRY_COUNT 次)
```

## 数据库模型关键字段

### Article (文章)
- `status`: ENUM('draft', 'publishing', 'published', 'failed')
- `original_topic`: 用户输入的话题/素材
- `image_prompts`: JSONB,存储图片生成提示词
- `token_usage`: 记录 GPT 消耗的 token 数
- `publish_url`: 发布成功后的文章链接

### Account (账号)
- `cookies`: TEXT,加密存储的 Cookie JSON
- `platform`: VARCHAR('头条号'/'百家号')
- `status`: ENUM('active', 'inactive', 'expired')

### Task (任务队列)
- `type`: ENUM('generate', 'humanize', 'image_gen', 'publish')
- `retry_count`: 失败重试计数器

## 环境变量说明

**必须配置** (.env):
```bash
DATABASE_URL=postgresql+asyncpg://...  # 注意使用 asyncpg 驱动
OPENAI_API_KEY=sk-...                  # 必须配置否则无法生成文章
SECRET_KEY=...                         # 用于 JWT/加密,生产环境必改
COOKIE_ENCRYPTION_KEY=...              # 32字节密钥,用于加密账号 Cookie
```

**可选配置**:
```bash
OPENAI_BASE_URL=...                    # 使用代理或第三方 API
IMAGE_GEN_PROVIDER=none                # 图片生成暂未实现
PUBLISH_INTERVAL_MINUTES=30            # 发布间隔限制
MAX_RETRY_COUNT=3                      # 发布失败最大重试次数
```

## 代码规范与约束

### 后端开发规范

1. **异步编程强制要求**
   - 所有 I/O 操作必须使用 `async/await`
   - 数据库操作使用 `AsyncSession`
   - 避免同步阻塞调用 (如 `requests` 改用 `httpx`)

2. **数据库操作**
   - 通过 `get_db()` 依赖注入获取 session
   - 使用 SQLAlchemy ORM,避免原始 SQL (除非性能优化)
   - 所有模型继承 `Base` + 混入 `UUIDMixin` + `TimestampMixin`

3. **日志规范**
   - 使用 `structlog` 结构化日志
   - 关键操作记录: 文章生成、发布、错误
   ```python
   logger.info("article_generated", article_id=str(article.id), token_usage=123)
   logger.error("publish_failed", error=str(e), article_id=...)
   ```

4. **异常处理**
   - 业务异常继承 `core.exceptions` 自定义类
   - API 层捕获异常转换为 HTTP 状态码
   - 发布失败必须记录详细错误信息到 `Task.error_message`

### 前端开发规范

1. **Composition API 优先**
   ```vue
   <script setup lang="ts">
   import { ref, onMounted } from 'vue'
   // 避免使用 Options API
   </script>
   ```

2. **API 调用封装**
   - 统一通过 `src/api/index.ts` 导出
   - 使用 TypeScript 定义请求/响应类型

3. **Element Plus 组件**
   - 已全局注册,直接使用 `<el-button>` 等
   - 图标已注册,使用 `<Edit />` 等组件

## 安全注意事项

⚠️ **关键安全点**:
1. **Cookie 存储**: 数据库中的 `cookies` 字段必须使用 AES 加密
2. **CORS 配置**: `main.py` 当前允许所有源 (`allow_origins=["*"]`),生产环境必须限制
3. **API Key 泄露**: `.env` 文件已加入 `.gitignore`,永远不要提交敏感配置
4. **XSS 防护**: 文章内容展示时注意转义 (Vue 默认转义但要小心 `v-html`)

## Playwright 维护指南

**头条页面 XPath/Selector 可能失效的元素**:
- 标题输入框: `textarea[placeholder*="标题"]`
- 正文编辑器: `[contenteditable="true"]`
- 发布按钮: `button:has-text("发布")`

**调试技巧**:
```python
# publisher.py 临时改为有头模式
self.browser = await playwright.chromium.launch(
    headless=False,  # 改为 False 查看浏览器操作
)
```

**发布失败排查步骤**:
1. 检查 Cookie 是否过期 (`check_account_status`)
2. 使用有头模式查看页面结构变化
3. 检查网络请求日志 (`await page.route("**/*", handler)`)
4. 截图保存: `await page.screenshot(path="debug.png")`

## 常见问题排查

### 后端启动失败
```bash
# 检查数据库连接
docker ps | grep toutiao_db  # 确保数据库容器运行
# 检查环境变量
python -c "from app.core.config import settings; print(settings.DATABASE_URL)"
```

### 文章生成失败
- 检查 `OPENAI_API_KEY` 是否有效
- 查看 structlog 日志中的错误详情
- 确认 OpenAI API 配额未超限

### 发布卡住/失败
- Cookie 可能过期,使用账号管理页面重新获取
- 检查 Playwright 浏览器是否能正常启动 (Docker 需要安装依赖)
- 头条页面改版导致选择器失效,需要更新 `publisher.py`

## 开发任务常用命令速查

```bash
# 添加新的 API 接口
# 1. 在 app/api/v1/ 创建新路由文件
# 2. 在 app/api/v1/__init__.py 注册路由
# 3. 定义对应的 schema (app/schemas/) 和 model (app/models/)

# 数据库模型变更
# 1. 修改 app/models/ 中的模型
# 2. 生成迁移: alembic revision --autogenerate -m "描述"
# 3. 应用迁移: alembic upgrade head

# 添加新的前端页面
# 1. 在 frontend/src/views/ 创建 .vue 文件
# 2. 在 frontend/src/router/index.ts 注册路由
# 3. 在 App.vue 菜单中添加导航 (如需要)
```

## Git 分支策略

- `main`: 生产环境代码 (当前未使用,本地开发为主)
- 直接在主分支开发,提交前确保测试通过

## 已知限制与未完成功能

✅ 已实现:
- AI 文章生成 (GPT-4)
- 基础 CRUD API
- Playwright 发布框架
- 前端基础页面

🚧 进行中/未实现:
- ❌ 数据库迁移脚本 (Alembic 配置)
- ❌ 用户认证 (JWT)
- ❌ 任务队列 (Celery/Redis)
- ❌ 图片自动生成 (Stable Diffusion/DALL-E)
- ❌ 定时发布任务
- ❌ 完整的单元测试覆盖

## 技术债务提醒

⚠️ **必须修复 (生产环境前)**:
1. CORS 白名单限制 (`main.py:46`)
2. Cookie 加密实现 (当前可能未加密直接存储)
3. JWT 认证缺失 (API 无鉴权保护)
4. 缺少 Rate Limiting (防止 API 滥用)

⚠️ **建议优化**:
1. `publisher.py` 硬编码选择器应提取到配置
2. 统一错误响应格式 (当前可能不一致)
3. 添加 API 请求日志中间件
4. 前端缺少全局错误处理
