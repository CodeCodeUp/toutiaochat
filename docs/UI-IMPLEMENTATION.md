# 项目实施进度文档

> 最后更新: 2025-12-19

## 实施进度概览

| 模块 | 状态 | 说明 |
|------|------|------|
| UI 重构 (Zen-iOS) | ✅ 已完成 | 全部 7 个页面已重构 |
| 工作流后端 | ✅ 已完成 | API、服务层、数据库模型 |
| 工作流前端 | ✅ 已完成 | 页面、组件、状态管理 |
| 数据库迁移 | ✅ 已完成 | 版本 58068f869124 |

---

## 一、UI 重构 (已完成)

### 设计系统: Zen-iOS Hybrid

- **玻璃拟态效果**: frosted glass、backdrop-blur-3xl
- **双层边框**: 内层白色 50%、外层灰色 10%
- **iOS 连续曲率圆角**: rounded-ios-xl/2xl
- **物理触感反馈**: active:scale-[0.98]
- **高对比度配色**: deep-black (#1C1C1E)

### 已重构页面

| 页面 | 文件 | 状态 |
|------|------|------|
| 主布局 | `App.vue` | ✅ |
| 仪表盘 | `Dashboard.vue` | ✅ |
| 文章管理 | `Articles.vue` | ✅ |
| 提示词管理 | `Prompts.vue` | ✅ |
| 账号管理 | `Accounts.vue` | ✅ |
| 任务队列 | `Tasks.vue` | ✅ |
| 系统设置 | `Settings.vue` | ✅ |

### 新增配置文件

- `frontend/tailwind.config.js` - Tailwind CSS 配置
- `frontend/postcss.config.js` - PostCSS 配置
- `frontend/src/style.css` - 全局样式 + 设计系统

### 依赖更新

```json
{
  "dependencies": {
    "lucide-vue-next": "^0.460.0"
  },
  "devDependencies": {
    "tailwindcss": "^3.4.0",
    "postcss": "^8.4.0",
    "autoprefixer": "^10.4.0"
  }
}
```

---

## 二、工作流功能 (已完成)

### 功能说明

支持两种文章创作模式：
- **半自动模式**: 逐步对话调整，用户可干预每个阶段
- **全自动模式**: 一键生成，后台自动完成所有阶段

### 工作流阶段

```
生成 (generate) → 优化 (optimize) → 配图 (image) → 编辑 (edit) → 完成 (completed)
```

### 后端实现

#### 数据库模型

| 文件 | 说明 |
|------|------|
| `models/workflow_session.py` | 工作流会话表 |
| `models/conversation_message.py` | 对话消息表 |

#### 服务层

```
backend/app/services/workflow/
├── __init__.py
├── conversation.py      # ConversationManager - 对话上下文管理
├── engine.py            # WorkflowEngine - 状态机核心引擎
└── stages/
    ├── __init__.py
    ├── base.py          # BaseStage - 阶段处理器抽象基类
    ├── generate.py      # GenerateStage - 文章生成阶段
    ├── optimize.py      # OptimizeStage - 文章优化阶段
    └── image.py         # ImageStage - 配图生成阶段
```

#### API 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/v1/workflows/sessions` | 创建工作流会话 |
| POST | `/api/v1/workflows/sessions/{id}/messages` | 发送消息 (半自动) |
| POST | `/api/v1/workflows/sessions/{id}/next-stage` | 进入下一阶段 |
| POST | `/api/v1/workflows/sessions/{id}/execute-auto` | 执行全自动流程 |
| GET | `/api/v1/workflows/sessions/{id}/status` | 查询状态 (轮询) |
| GET | `/api/v1/workflows/sessions/{id}` | 获取会话详情 |
| GET | `/api/v1/workflows/sessions/{id}/messages` | 获取对话历史 |

#### Schema 定义

- `schemas/workflow.py` - Pydantic 请求/响应模型

### 前端实现

#### 状态管理

- `stores/workflow.ts` - Pinia Store

#### 组件

| 组件 | 文件 | 说明 |
|------|------|------|
| 步骤条 | `components/workflow/WorkflowStepper.vue` | 显示当前阶段 |
| 对话框 | `components/workflow/ChatDialog.vue` | 聊天式交互 |
| 进度条 | `components/workflow/AutoProgress.vue` | 全自动模式进度 |

#### 页面

- `views/ArticleWorkflow.vue` - 工作流主页面

#### 路由

```typescript
{
  path: '/articles/workflow',
  name: 'ArticleWorkflow',
  component: () => import('@/views/ArticleWorkflow.vue'),
  meta: { title: '创建文章' },
}
```

#### API 封装

更新 `api/index.ts` 添加 `workflowApi`

---

## 三、数据库迁移 (已完成)

### Alembic 配置

已初始化 Alembic，配置文件：
- `backend/alembic.ini`
- `backend/alembic/env.py`

### 迁移脚本

- `alembic/versions/58068f869124_add_workflow_tables.py`

创建表：
- `workflow_sessions` - 工作流会话
- `conversation_messages` - 对话消息

### 迁移状态

```bash
# 当前版本
58068f869124 (head)

# 如需重新执行
cd backend
alembic upgrade head
```

---

## 四、启动指南

### 1. 启动后端

```bash
cd backend

# 执行数据库迁移 (如果是新环境)
alembic upgrade head

# 启动服务
python -m app.main
```

后端运行在: `http://localhost:8100`

### 2. 启动前端

```bash
cd frontend
npm install
npm run dev
```

前端运行在: `http://localhost:5173` (或其他端口)

### 3. 访问工作流

1. 打开前端页面
2. 点击侧边栏「文章管理」
3. 点击「创建文章」按钮
4. 进入工作流页面，选择模式开始创作

---

## 五、后续计划

### 待实现功能

- [ ] 图片生成集成 (DALL-E / Stable Diffusion)
- [ ] DOCX 文档导出
- [ ] 定时发布任务
- [ ] WebSocket 实时推送 (替代轮询)

### 待优化项

- [ ] 前端构建优化 (chunk 分割)
- [ ] 数据库连接池调优
- [ ] 错误处理和重试机制
- [ ] 单元测试覆盖

---

## 六、问题排查

### Q1: 后端启动后访问超时

**可能原因**: 数据库连接慢

**解决方案**:
1. 检查 `.env` 中的数据库连接字符串
2. 确认数据库服务器可访问
3. 重启后端服务

### Q2: 前端构建 vue-tsc 报错

**错误**: `Search string not found`

**解决方案**:
```bash
# 跳过类型检查直接构建
npx vite build
```

### Q3: 工作流 API 返回 404

**可能原因**: 数据库表不存在

**解决方案**:
```bash
cd backend
alembic upgrade head
```

---

## 七、文件变更清单

### 后端新增文件

```
backend/
├── alembic/
│   ├── env.py
│   ├── versions/
│   │   └── 58068f869124_add_workflow_tables.py
├── alembic.ini
├── app/
│   ├── models/
│   │   ├── workflow_session.py
│   │   └── conversation_message.py
│   ├── schemas/
│   │   └── workflow.py
│   ├── services/
│   │   └── workflow/
│   │       ├── __init__.py
│   │       ├── conversation.py
│   │       ├── engine.py
│   │       └── stages/
│   │           ├── __init__.py
│   │           ├── base.py
│   │           ├── generate.py
│   │           ├── optimize.py
│   │           └── image.py
│   └── api/v1/
│       └── workflows.py
```

### 前端新增文件

```
frontend/
├── tailwind.config.js
├── postcss.config.js
├── src/
│   ├── style.css
│   ├── stores/
│   │   └── workflow.ts
│   ├── components/
│   │   └── workflow/
│   │       ├── WorkflowStepper.vue
│   │       ├── ChatDialog.vue
│   │       └── AutoProgress.vue
│   └── views/
│       └── ArticleWorkflow.vue
```

### 修改的文件

```
backend/
├── app/models/__init__.py          # 添加 WorkflowSession, ConversationMessage
├── app/models/article.py           # 添加 workflow_sessions relationship
├── app/api/v1/__init__.py          # 注册 workflows 路由
├── app/core/database.py            # 添加连接超时配置

frontend/
├── src/main.ts                     # 引入 style.css
├── src/router/index.ts             # 添加 /articles/workflow 路由
├── src/api/index.ts                # 添加 workflowApi
├── src/views/Articles.vue          # 创建按钮跳转到工作流
├── src/App.vue                     # UI 重构
├── src/views/*.vue                 # 所有页面 UI 重构
```
