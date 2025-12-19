# 工作流架构设计文档

> 版本: 1.0
> 日期: 2025-12-19
> 作者: 架构设计

## 目录

- [一、核心数据模型](#一核心数据模型)
- [二、后端服务架构](#二后端服务架构)
- [三、API接口设计](#三api接口设计)
- [四、前端组件架构](#四前端组件架构)
- [五、流程图](#五流程图)
- [六、数据流示例](#六数据流示例)
- [七、核心代码骨架](#七核心代码骨架)
- [八、实现检查清单](#八实现检查清单)

---

## 一、核心数据模型

### 1.1 数据库表设计

#### WorkflowSession (工作流会话表)

```sql
CREATE TABLE workflow_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    article_id UUID NOT NULL REFERENCES articles(id) ON DELETE CASCADE,
    mode VARCHAR(20) NOT NULL,  -- 'auto' | 'manual'
    current_stage VARCHAR(20) NOT NULL DEFAULT 'generate',  -- 'generate'|'optimize'|'image'|'edit'|'completed'
    stage_data JSONB DEFAULT '{}',  -- 各阶段数据快照 {"generate": {...}, "optimize": {...}}
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_workflow_article ON workflow_sessions(article_id);
CREATE INDEX idx_workflow_stage ON workflow_sessions(current_stage);
```

#### ConversationMessage (对话消息表)

```sql
CREATE TABLE conversation_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES workflow_sessions(id) ON DELETE CASCADE,
    stage VARCHAR(20) NOT NULL,  -- 'generate'|'optimize'|'image'
    role VARCHAR(20) NOT NULL,   -- 'user'|'assistant'|'system'
    content TEXT NOT NULL,
    metadata JSONB,              -- 额外信息: {token_usage, prompt_id, model}
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_conv_session_stage ON conversation_messages(session_id, stage, created_at);
```

### 1.2 Python 模型定义

```python
# app/models/workflow_session.py

from sqlalchemy import Column, String, ForeignKey, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
import enum

from app.models.base import Base, UUIDMixin, TimestampMixin

class WorkflowMode(str, enum.Enum):
    AUTO = "auto"       # 全自动模式
    MANUAL = "manual"   # 半自动模式

class WorkflowStage(str, enum.Enum):
    GENERATE = "generate"     # 文章生成阶段
    OPTIMIZE = "optimize"     # 优化阶段
    IMAGE = "image"           # 生图阶段
    EDIT = "edit"             # 编辑阶段
    COMPLETED = "completed"   # 完成

class WorkflowSession(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "workflow_sessions"

    article_id = Column(UUID(as_uuid=True), ForeignKey("articles.id", ondelete="CASCADE"), nullable=False)
    mode = Column(SQLEnum(WorkflowMode), nullable=False)
    current_stage = Column(SQLEnum(WorkflowStage), default=WorkflowStage.GENERATE, nullable=False)
    stage_data = Column(JSONB, default=dict, comment="各阶段快照数据")

    # Relationships
    article = relationship("Article", back_populates="workflow_sessions")
    messages = relationship("ConversationMessage", back_populates="session", cascade="all, delete-orphan")


# app/models/conversation_message.py

class ConversationMessage(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "conversation_messages"

    session_id = Column(UUID(as_uuid=True), ForeignKey("workflow_sessions.id", ondelete="CASCADE"), nullable=False)
    stage = Column(String(20), nullable=False)
    role = Column(String(20), nullable=False)  # 'user' | 'assistant' | 'system'
    content = Column(Text, nullable=False)
    metadata = Column(JSONB, default=dict)

    # Relationships
    session = relationship("WorkflowSession", back_populates="messages")
```

---

## 二、后端服务架构

### 2.1 目录结构

```
backend/app/
├── services/
│   └── workflow/
│       ├── __init__.py
│       ├── engine.py              # WorkflowEngine - 状态机核心引擎
│       ├── conversation.py        # ConversationManager - 对话上下文管理
│       └── stages/
│           ├── __init__.py
│           ├── base.py            # BaseStage - 抽象基类
│           ├── generate.py        # GenerateStage - 生成阶段
│           ├── optimize.py        # OptimizeStage - 优化阶段
│           └── image.py           # ImageStage - 生图阶段
│
├── api/v1/
│   └── workflows.py               # 工作流API路由
│
├── models/
│   ├── workflow_session.py        # 工作流会话模型
│   └── conversation_message.py    # 对话消息模型
│
└── schemas/
    └── workflow.py                # Pydantic Schema
```

### 2.2 核心类职责

#### WorkflowEngine (工作流引擎)

```python
class WorkflowEngine:
    """状态机引擎，负责工作流编排"""

    async def create_session(db, topic, category, mode, account_id) -> UUID
        # 创建Article + WorkflowSession，返回session_id

    async def process_message(db, session_id, user_msg, prompt_id) -> dict
        # 处理用户消息，调用当前阶段的Stage处理器

    async def next_stage(db, session_id) -> dict
        # 保存当前阶段快照，状态机转移到下一阶段

    async def execute_auto(db, session_id) -> dict
        # 全自动模式：顺序执行所有阶段

    async def get_session_status(db, session_id) -> dict
        # 查询会话状态（用于轮询）
```

#### BaseStage (阶段处理器基类)

```python
class BaseStage(ABC):
    """阶段处理器抽象类"""

    @abstractmethod
    async def process(db, session, user_msg, history, prompt_id) -> dict
        # 处理用户消息，返回AI响应

    @abstractmethod
    async def auto_execute(db, session) -> dict
        # 自动模式下的执行逻辑

    @abstractmethod
    async def snapshot(db, session) -> dict
        # 保存当前阶段的快照数据

    async def can_proceed(db, session) -> bool
        # 判断是否可进入下一阶段（默认始终True）
```

#### ConversationManager (对话管理器)

```python
class ConversationManager:
    """对话上下文管理器"""

    async def add_message(db, session_id, stage, role, content, metadata) -> None
        # 保存单条消息

    async def get_history(db, session_id, stage, limit) -> List[dict]
        # 获取指定阶段的对话历史

    async def build_openai_messages(db, session_id, stage) -> List[dict]
        # 构建OpenAI API所需的messages格式
```

---

## 三、API接口设计

### 3.1 接口列表

#### 1. 创建工作流会话

```
POST /api/v1/workflows/sessions

Request Body:
{
  "topic": "AI的未来发展趋势",
  "category": "科技",
  "mode": "manual",  // "auto" | "manual"
  "account_id": "uuid-string"  // 可选
}

Response:
{
  "session_id": "uuid",
  "article_id": "uuid",
  "stage": "generate",
  "mode": "manual"
}
```

#### 2. 发送消息（半自动模式）

```
POST /api/v1/workflows/sessions/{session_id}/messages

Request Body:
{
  "message": "增加一些具体案例",
  "use_prompt_id": "uuid"  // 可选：使用指定提示词
}

Response:
{
  "assistant_reply": "已为您添加了3个具体案例...",
  "stage": "generate",
  "can_proceed": true,
  "article_preview": {
    "title": "AI时代的变革",
    "content": "..."
  },
  "suggestions": [
    "您可以要求调整写作风格",
    "可以增加更多数据支撑"
  ]
}
```

#### 3. 进入下一阶段

```
POST /api/v1/workflows/sessions/{session_id}/next-stage

Response:
{
  "previous_stage": "generate",
  "current_stage": "optimize",
  "snapshot_saved": true
}
```

#### 4. 执行全自动流程

```
POST /api/v1/workflows/sessions/{session_id}/execute-auto

Response:
{
  "task_id": "uuid",
  "message": "后台任务已启动，请轮询状态接口"
}
```

#### 5. 查询会话状态（用于轮询）

```
GET /api/v1/workflows/sessions/{session_id}/status

Response:
{
  "session_id": "uuid",
  "stage": "optimize",
  "mode": "auto",
  "progress": 50,  // 0-100
  "status": "processing",  // "processing" | "completed" | "failed"
  "result": {  // 完成后返回
    "docx_url": "/static/...",
    "article_id": "uuid"
  },
  "error": null
}
```

#### 6. 获取对话历史

```
GET /api/v1/workflows/sessions/{session_id}/messages?stage=generate&limit=50

Response:
{
  "messages": [
    {
      "id": "uuid",
      "role": "user",
      "content": "写一篇关于AI的文章",
      "created_at": "2025-12-19T10:00:00Z"
    },
    {
      "id": "uuid",
      "role": "assistant",
      "content": "已生成文章...",
      "created_at": "2025-12-19T10:00:05Z",
      "metadata": {
        "token_usage": 1500
      }
    }
  ],
  "total": 6
}
```

---

## 四、前端组件架构

### 4.1 目录结构

```
frontend/src/
├── views/
│   ├── Articles.vue              # 现有：文章列表（增加工作流入口）
│   └── ArticleWorkflow.vue       # 新增：工作流主页面
│
├── components/
│   └── workflow/
│       ├── WorkflowStepper.vue   # 步骤条组件
│       ├── ChatDialog.vue        # 对话框组件
│       ├── PromptSelector.vue    # 提示词选择器
│       ├── AutoProgress.vue      # 自动模式进度条
│       └── DocxPreview.vue       # 文档预览组件
│
├── stores/
│   └── workflow.ts               # Pinia状态管理
│
└── api/
    └── workflow.ts               # 工作流API封装
```

### 4.2 核心组件设计

#### ArticleWorkflow.vue (主容器)

```vue
<template>
  <div class="workflow-container">
    <!-- 顶部步骤条 -->
    <WorkflowStepper
      :current="currentStage"
      :completed="completedStages"
      @stage-click="handleStageClick"
    />

    <!-- 模式切换 -->
    <div class="mode-switch">
      <el-switch
        v-model="isAutoMode"
        active-text="全自动"
        inactive-text="半自动"
        :disabled="sessionStarted"
      />
    </div>

    <!-- 主内容区 -->
    <div class="workflow-main">
      <!-- 半自动模式 -->
      <template v-if="!isAutoMode">
        <ChatDialog
          v-if="currentStage !== 'edit' && currentStage !== 'completed'"
          :session-id="sessionId"
          :stage="currentStage"
          :messages="messages"
          :loading="chatLoading"
          @send="handleSendMessage"
          @use-prompt="handleUsePrompt"
          @next-stage="handleNextStage"
        />

        <DocxPreview
          v-if="currentStage === 'edit' || currentStage === 'completed'"
          :article-id="articleId"
          @save="handleSaveDocx"
          @publish="handlePublish"
        />
      </template>

      <!-- 全自动模式 -->
      <template v-else>
        <AutoProgress
          :session-id="sessionId"
          :progress="autoProgress"
          :status="autoStatus"
          @completed="handleAutoCompleted"
        />
      </template>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useWorkflowStore } from '@/stores/workflow'

const workflowStore = useWorkflowStore()
const isAutoMode = ref(false)
const sessionId = ref<string>()
const currentStage = computed(() => workflowStore.currentStage)
// ... 其他逻辑
</script>
```

#### ChatDialog.vue (对话框)

```vue
<template>
  <el-card class="chat-dialog">
    <!-- 对话历史 -->
    <div class="message-list" ref="messageContainer">
      <div
        v-for="msg in messages"
        :key="msg.id"
        :class="['message', msg.role]"
      >
        <div class="message-content">{{ msg.content }}</div>
        <div class="message-time">{{ formatTime(msg.created_at) }}</div>
      </div>
    </div>

    <!-- 文章预览 -->
    <el-collapse v-if="articlePreview">
      <el-collapse-item title="预览当前文章">
        <h3>{{ articlePreview.title }}</h3>
        <div v-html="formatContent(articlePreview.content)"></div>
      </el-collapse-item>
    </el-collapse>

    <!-- 输入区 -->
    <div class="input-area">
      <el-button size="small" @click="showPromptSelector = true">
        选择提示词
      </el-button>
      <el-input
        v-model="inputMessage"
        type="textarea"
        :rows="3"
        placeholder="输入您的要求..."
        @keydown.ctrl.enter="handleSend"
      />
      <el-button type="primary" :loading="loading" @click="handleSend">
        发送
      </el-button>
      <el-button type="success" @click="$emit('next-stage')">
        完成此阶段
      </el-button>
    </div>

    <!-- 提示词选择器 -->
    <PromptSelector
      v-model="showPromptSelector"
      :stage="stage"
      @select="handleSelectPrompt"
    />
  </el-card>
</template>
```

### 4.3 Pinia Store

```typescript
// stores/workflow.ts

import { defineStore } from 'pinia'
import { workflowApi } from '@/api/workflow'

export const useWorkflowStore = defineStore('workflow', {
  state: () => ({
    sessionId: null as string | null,
    articleId: null as string | null,
    mode: 'manual' as 'auto' | 'manual',
    currentStage: 'generate' as string,
    messages: [] as any[],
    autoProgress: 0,
    autoStatus: 'idle' as 'idle' | 'processing' | 'completed' | 'failed',
  }),

  actions: {
    async createSession(topic: string, category: string, mode: 'auto' | 'manual') {
      const res = await workflowApi.createSession({ topic, category, mode })
      this.sessionId = res.session_id
      this.articleId = res.article_id
      this.mode = mode
      this.currentStage = res.stage
    },

    async sendMessage(message: string, promptId?: string) {
      const res = await workflowApi.sendMessage(this.sessionId!, { message, use_prompt_id: promptId })
      this.messages.push(
        { role: 'user', content: message, created_at: new Date() },
        { role: 'assistant', content: res.assistant_reply, created_at: new Date() }
      )
      return res
    },

    async nextStage() {
      const res = await workflowApi.nextStage(this.sessionId!)
      this.currentStage = res.current_stage
    },

    async executeAuto() {
      const res = await workflowApi.executeAuto(this.sessionId!)
      this.startPolling(res.task_id)
    },

    startPolling(taskId: string) {
      const timer = setInterval(async () => {
        const status = await workflowApi.getStatus(this.sessionId!)
        this.autoProgress = status.progress
        this.autoStatus = status.status

        if (status.status === 'completed' || status.status === 'failed') {
          clearInterval(timer)
          this.currentStage = 'completed'
        }
      }, 2000)
    },
  },
})
```

---

## 五、流程图

### 5.1 半自动模式流程

```
用户点击"创建文章"
  ↓
选择"半自动模式" + 输入话题
  ↓
后端: 创建Article + WorkflowSession (stage=GENERATE)
  ↓
前端: 打开工作流页面，显示聊天框
  ↓
┌─────────────────────────────────────┐
│  阶段1: 生成 (GENERATE)               │
├─────────────────────────────────────┤
│  用户: "写一篇关于AI的文章"           │
│  AI: 生成文章内容...                  │
│  用户: "增加一些具体案例"             │
│  AI: 已添加3个案例...                 │
│  用户: 点击"完成此阶段"               │
└─────────────────────────────────────┘
  ↓
后端: 保存快照到stage_data['generate']，stage → OPTIMIZE
  ↓
前端: 弹出提示"是否进入优化阶段？"
  ↓
┌─────────────────────────────────────┐
│  阶段2: 优化 (OPTIMIZE)               │
├─────────────────────────────────────┤
│  用户: "降低AI痕迹"                   │
│  AI: 已优化...                        │
│  用户: 点击"完成此阶段"               │
└─────────────────────────────────────┘
  ↓
后端: stage → IMAGE
  ↓
前端: 弹出提示"是否生成图片？"
  ↓
┌─────────────────────────────────────┐
│  阶段3: 生图 (IMAGE)                  │
├─────────────────────────────────────┤
│  用户: "生成3张配图"                  │
│  AI: 调用image_gen.py生成图片...      │
│  用户: 点击"完成此阶段"               │
└─────────────────────────────────────┘
  ↓
后端: stage → EDIT，生成DOCX
  ↓
前端: 显示DOCX预览和编辑器
  ↓
┌─────────────────────────────────────┐
│  阶段4: 编辑 (EDIT)                   │
├─────────────────────────────────────┤
│  用户: 在线编辑DOCX内容               │
│  用户: 点击"保存"                     │
└─────────────────────────────────────┘
  ↓
后端: stage → COMPLETED
  ↓
前端: 显示"发布"按钮
  ↓
用户: 点击"发布"
  ↓
后端: 调用publisher.py发布到头条
```

### 5.2 全自动模式流程

```
用户点击"创建文章"
  ↓
选择"全自动模式" + 输入话题
  ↓
后端: 创建Article + WorkflowSession (mode=AUTO)
  ↓
前端: 打开工作流页面，显示"一键生成"按钮
  ↓
用户: 点击"一键生成"
  ↓
后端: 启动后台异步任务，返回task_id
  ↓
前端: 显示进度条，开始轮询状态
  ↓
┌──────────────────────────────────┐
│  后台任务执行中...                │
├──────────────────────────────────┤
│  [25%] 生成文章 (generate)        │
│    调用ai_writer.generate_article │
│                                   │
│  [50%] 优化文章 (humanize)        │
│    调用ai_writer.humanize_article │
│                                   │
│  [75%] 生成图片 (images)          │
│    调用image_gen.generate_images  │
│                                   │
│  [100%] 整合DOCX                  │
│    调用docx_generator             │
└──────────────────────────────────┘
  ↓
后端: 更新session.current_stage = COMPLETED
  ↓
前端: 轮询检测到completed，跳转到预览页
  ↓
显示DOCX预览和编辑器
  ↓
用户: 点击"发布"
  ↓
后端: 调用publisher.py发布
```

### 5.3 状态机图

```
                    ┌──────────┐
                    │  START   │
                    └────┬─────┘
                         │
                  create_session()
                         │
                         ▼
                  ┌─────────────┐
                  │  GENERATE   │◄────┐
                  └──────┬──────┘     │
                         │            │ user continues
                   next_stage()       │ conversation
                         │            │
                         ▼            │
                  ┌─────────────┐    │
                  │  OPTIMIZE   │────┘
                  └──────┬──────┘
                         │
                   next_stage()
                         │
                         ▼
                  ┌─────────────┐
                  │   IMAGE     │
                  └──────┬──────┘
                         │
                   next_stage()
                         │
                         ▼
                  ┌─────────────┐
                  │    EDIT     │
                  └──────┬──────┘
                         │
                   next_stage()
                         │
                         ▼
                  ┌─────────────┐
                  │  COMPLETED  │
                  └──────┬──────┘
                         │
                   publish()
                         │
                         ▼
                  ┌─────────────┐
                  │  PUBLISHED  │
                  └─────────────┘
```

---

## 六、数据流示例

### 6.1 半自动模式 - 生成阶段对话

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
前端 → 后端: POST /workflows/sessions
{
  "topic": "AI的未来发展",
  "category": "科技",
  "mode": "manual"
}

后端执行:
  1. 创建Article (status=DRAFT, original_topic="AI的未来发展")
  2. 创建WorkflowSession (mode=MANUAL, current_stage=GENERATE)
  3. 返回session_id

前端 ← 后端: {session_id: "xxx", article_id: "yyy", stage: "generate"}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
前端显示: 聊天框 + "请描述您的需求"

用户输入: "写一篇关于AI未来发展的文章，要有数据支撑"

前端 → 后端: POST /workflows/sessions/xxx/messages
{
  "message": "写一篇关于AI未来发展的文章，要有数据支撑"
}

后端执行:
  1. 获取session (current_stage=GENERATE)
  2. 调用GenerateStage.process()
     - 获取历史消息 (首次为空)
     - 构建OpenAI messages:
       [
         {role: "system", content: <生成提示词>},
         {role: "user", content: "写一篇..."}
       ]
     - 调用ai_writer.generate_article()
     - 更新Article.title, Article.content
  3. 保存消息到conversation_messages表
  4. 返回结果

前端 ← 后端:
{
  "assistant_reply": "我已经为您生成了一篇文章...",
  "stage": "generate",
  "can_proceed": true,
  "article_preview": {
    "title": "人工智能：重塑未来的技术革命",
    "content": "根据Gartner 2024年报告..."
  }
}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
前端显示: AI回复 + 文章预览

用户继续对话: "增加一些中国的AI企业案例"

前端 → 后端: POST /workflows/sessions/xxx/messages
{
  "message": "增加一些中国的AI企业案例"
}

后端执行:
  1. 获取历史消息 (包含上一轮对话)
  2. 构建OpenAI messages:
     [
       {role: "system", content: <提示词>},
       {role: "user", content: "写一篇..."},
       {role: "assistant", content: "我已经为您生成..."},
       {role: "user", content: "增加一些中国的AI企业案例"}
     ]
  3. 调用OpenAI API
  4. 更新Article内容
  5. 保存消息

前端 ← 后端:
{
  "assistant_reply": "已添加百度、阿里、腾讯等企业案例...",
  "article_preview": {
    "title": "...",
    "content": "...百度的文心一言...阿里的通义千问..."
  }
}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
用户满意: 点击"完成此阶段"按钮

前端 → 后端: POST /workflows/sessions/xxx/next-stage

后端执行:
  1. 调用GenerateStage.snapshot()
     - 保存到stage_data['generate'] = {
         title: "...",
         content: "...",
         message_count: 4,
         final_token_usage: 2500
       }
  2. 状态机转移: current_stage = OPTIMIZE
  3. 返回结果

前端 ← 后端:
{
  "previous_stage": "generate",
  "current_stage": "optimize"
}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
前端弹出提示: "已完成生成阶段，是否进入优化阶段？"
用户点击"是" → 显示优化阶段聊天框
```

### 6.2 全自动模式 - 执行流程

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
前端 → 后端: POST /workflows/sessions
{
  "topic": "AI的未来发展",
  "mode": "auto"
}

后端: 返回 {session_id: "xxx"}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
前端显示: "一键生成"按钮

用户点击按钮

前端 → 后端: POST /workflows/sessions/xxx/execute-auto

后端执行:
  1. 创建后台任务:
     async def auto_workflow_task():
         await workflow_engine.execute_auto(db, session_id)

  2. 立即返回

前端 ← 后端: {task_id: "zzz"}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
前端显示: 进度条 (0%)

前端开始轮询: GET /workflows/sessions/xxx/status (每2秒)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
后台任务执行中:

[T+0s] 阶段1: 生成文章
  result = await ai_writer.generate_article(topic)
  article.title = result['title']
  article.content = result['content']
  更新progress = 25%

[T+15s] 轮询返回: {progress: 25, status: "processing", stage: "generate"}
        前端更新进度条: 25%

[T+20s] 阶段2: 优化文章
  result = await ai_writer.humanize_article(title, content)
  article.title = result['title']
  article.content = result['content']
  更新progress = 50%

[T+35s] 轮询返回: {progress: 50, status: "processing", stage: "optimize"}
        前端更新进度条: 50%

[T+40s] 阶段3: 生成图片
  images = await image_gen.generate_images(prompts)
  article.images = images
  更新progress = 75%

[T+65s] 轮询返回: {progress: 75, status: "processing", stage: "image"}
        前端更新进度条: 75%

[T+70s] 阶段4: 生成DOCX
  docx_path = docx_generator.create_article_docx(...)
  session.current_stage = COMPLETED
  更新progress = 100%

[T+75s] 轮询返回:
{
  progress: 100,
  status: "completed",
  stage: "completed",
  result: {
    docx_url: "/static/articles/xxx.docx",
    article_id: "yyy"
  }
}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
前端检测到completed: 停止轮询，跳转到预览页面
显示: DOCX内容 + "发布"按钮
```

---

## 七、核心代码骨架

### 7.1 WorkflowEngine

```python
# app/services/workflow/engine.py

from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models import Article, ArticleStatus, ArticleCategory
from app.models.workflow_session import WorkflowSession, WorkflowMode, WorkflowStage
from app.models.conversation_message import ConversationMessage
from app.services.workflow.stages import GenerateStage, OptimizeStage, ImageStage
from app.services.workflow.conversation import ConversationManager
from app.services import ai_writer, image_gen
from app.services.docx_generator import docx_generator

class WorkflowEngine:
    def __init__(self):
        self.stages = {
            WorkflowStage.GENERATE: GenerateStage(),
            WorkflowStage.OPTIMIZE: OptimizeStage(),
            WorkflowStage.IMAGE: ImageStage(),
        }
        self.conversation_mgr = ConversationManager()

    async def create_session(
        self,
        db: AsyncSession,
        topic: str,
        category: str,
        mode: WorkflowMode,
        account_id: UUID | None = None,
    ) -> UUID:
        """创建工作流会话"""
        # 1. 创建Article
        article = Article(
            title="",
            content="",
            original_topic=topic,
            category=ArticleCategory(category),
            status=ArticleStatus.DRAFT,
            account_id=account_id,
        )
        db.add(article)
        await db.flush()

        # 2. 创建WorkflowSession
        session = WorkflowSession(
            article_id=article.id,
            mode=mode,
            current_stage=WorkflowStage.GENERATE,
            stage_data={},
        )
        db.add(session)
        await db.commit()

        return session.id

    async def process_message(
        self,
        db: AsyncSession,
        session_id: UUID,
        user_message: str,
        prompt_id: UUID | None = None,
    ) -> dict:
        """处理用户消息"""
        # 1. 获取session
        session = await self._get_session(db, session_id)

        # 2. 获取当前阶段处理器
        stage_handler = self.stages[session.current_stage]

        # 3. 获取历史对话
        history = await self.conversation_mgr.get_history(
            db, session_id, session.current_stage.value
        )

        # 4. 处理消息
        result = await stage_handler.process(
            db, session, user_message, history, prompt_id
        )

        # 5. 保存消息
        await self.conversation_mgr.add_message(
            db, session_id, session.current_stage.value, "user", user_message
        )
        await self.conversation_mgr.add_message(
            db, session_id, session.current_stage.value, "assistant", result['reply']
        )

        await db.commit()
        return result

    async def next_stage(self, db: AsyncSession, session_id: UUID) -> dict:
        """进入下一阶段"""
        session = await self._get_session(db, session_id)

        # 1. 保存当前阶段快照
        stage_handler = self.stages.get(session.current_stage)
        if stage_handler:
            snapshot = await stage_handler.snapshot(db, session)
            if session.stage_data is None:
                session.stage_data = {}
            session.stage_data[session.current_stage.value] = snapshot

        # 2. 状态机转移
        stage_map = {
            WorkflowStage.GENERATE: WorkflowStage.OPTIMIZE,
            WorkflowStage.OPTIMIZE: WorkflowStage.IMAGE,
            WorkflowStage.IMAGE: WorkflowStage.EDIT,
            WorkflowStage.EDIT: WorkflowStage.COMPLETED,
        }

        previous_stage = session.current_stage
        session.current_stage = stage_map.get(session.current_stage, WorkflowStage.COMPLETED)

        await db.commit()

        return {
            "previous_stage": previous_stage.value,
            "current_stage": session.current_stage.value,
        }

    async def execute_auto(self, db: AsyncSession, session_id: UUID) -> dict:
        """执行全自动流程"""
        session = await self._get_session(db, session_id)
        article = await db.get(Article, session.article_id)

        try:
            # 阶段1: 生成文章 (25%)
            gen_result = await ai_writer.generate_article(
                db, article.original_topic, article.category.value
            )
            article.title = gen_result['title']
            article.content = gen_result['content']
            article.image_prompts = gen_result.get('image_prompts', [])
            article.token_usage += gen_result['token_usage']
            session.stage_data['generate'] = {'completed': True, 'token_usage': gen_result['token_usage']}
            await db.commit()

            # 阶段2: 优化文章 (50%)
            opt_result = await ai_writer.humanize_article(db, article.title, article.content)
            article.title = opt_result['title']
            article.content = opt_result['content']
            article.token_usage += opt_result['token_usage']
            session.stage_data['optimize'] = {'completed': True, 'token_usage': opt_result['token_usage']}
            await db.commit()

            # 阶段3: 生成图片 (75%)
            images = []
            if article.image_prompts:
                images = await image_gen.generate_images(db, article.image_prompts[:3])
                article.images = images
            session.stage_data['image'] = {'completed': True, 'image_count': len(images)}
            await db.commit()

            # 阶段4: 生成DOCX (100%)
            docx_path = docx_generator.create_article_docx(
                title=article.title,
                content=article.content,
                article_id=str(article.id),
            )

            # 更新状态
            session.current_stage = WorkflowStage.COMPLETED
            await db.commit()

            return {
                "success": True,
                "docx_url": docx_path,
                "article_id": str(article.id),
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
            }

    async def get_session_status(self, db: AsyncSession, session_id: UUID) -> dict:
        """查询会话状态（用于轮询）"""
        session = await self._get_session(db, session_id)

        # 计算进度
        progress_map = {
            WorkflowStage.GENERATE: 25,
            WorkflowStage.OPTIMIZE: 50,
            WorkflowStage.IMAGE: 75,
            WorkflowStage.EDIT: 90,
            WorkflowStage.COMPLETED: 100,
        }

        return {
            "session_id": str(session.id),
            "stage": session.current_stage.value,
            "mode": session.mode.value,
            "progress": progress_map.get(session.current_stage, 0),
            "status": "completed" if session.current_stage == WorkflowStage.COMPLETED else "processing",
        }

    async def _get_session(self, db: AsyncSession, session_id: UUID) -> WorkflowSession:
        """获取会话"""
        result = await db.execute(
            select(WorkflowSession).where(WorkflowSession.id == session_id)
        )
        session = result.scalar_one_or_none()
        if not session:
            raise ValueError(f"Session {session_id} not found")
        return session


# 导出单例
workflow_engine = WorkflowEngine()
```

### 7.2 BaseStage

```python
# app/services/workflow/stages/base.py

from abc import ABC, abstractmethod
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.workflow_session import WorkflowSession

class BaseStage(ABC):
    """阶段处理器基类"""

    @abstractmethod
    async def process(
        self,
        db: AsyncSession,
        session: WorkflowSession,
        user_message: str,
        history: list[dict],
        prompt_id: str | None = None,
    ) -> dict:
        """
        处理用户消息

        Returns:
            {
                "reply": str,              # AI回复
                "can_proceed": bool,       # 是否可进入下一阶段
                "article_preview": dict,   # 文章预览
                "suggestions": list[str],  # 操作建议
            }
        """
        raise NotImplementedError

    @abstractmethod
    async def snapshot(self, db: AsyncSession, session: WorkflowSession) -> dict:
        """
        保存当前阶段快照

        Returns:
            dict: 快照数据
        """
        raise NotImplementedError

    async def can_proceed(self, db: AsyncSession, session: WorkflowSession) -> bool:
        """判断是否可进入下一阶段（默认始终可以）"""
        return True
```

### 7.3 GenerateStage

```python
# app/services/workflow/stages/generate.py

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.services.workflow.stages.base import BaseStage
from app.models.workflow_session import WorkflowSession
from app.models import Article
from app.models.prompt import Prompt, PromptType
from app.services import ai_writer

class GenerateStage(BaseStage):
    """生成阶段处理器"""

    async def process(
        self,
        db: AsyncSession,
        session: WorkflowSession,
        user_message: str,
        history: list[dict],
        prompt_id: str | None = None,
    ) -> dict:
        # 1. 获取关联的文章
        article = await db.get(Article, session.article_id)

        # 2. 如果是首次生成，使用generate_article
        if not history:
            result = await ai_writer.generate_article(
                db=db,
                topic=article.original_topic,
                category=article.category.value,
            )
            article.title = result['title']
            article.content = result['content']
            article.image_prompts = result.get('image_prompts', [])
            article.token_usage += result['token_usage']
            await db.commit()

            return {
                "reply": f"已为您生成文章《{result['title']}》",
                "can_proceed": True,
                "article_preview": {
                    "title": result['title'],
                    "content": result['content'][:500] + "...",
                },
                "suggestions": [
                    "您可以要求调整写作风格",
                    "可以增加更多具体案例",
                    "可以修改文章结构",
                ],
            }

        # 3. 后续对话：基于历史上下文继续修改
        # TODO: 这里需要重构ai_writer支持多轮对话
        # 暂时简单实现：重新调用generate_article
        result = await ai_writer.generate_article(
            db=db,
            topic=f"{article.original_topic}\n\n用户要求：{user_message}",
            category=article.category.value,
        )
        article.title = result['title']
        article.content = result['content']
        article.token_usage += result['token_usage']
        await db.commit()

        return {
            "reply": f"已根据您的要求修改文章",
            "can_proceed": True,
            "article_preview": {
                "title": result['title'],
                "content": result['content'][:500] + "...",
            },
        }

    async def snapshot(self, db: AsyncSession, session: WorkflowSession) -> dict:
        """保存生成阶段快照"""
        article = await db.get(Article, session.article_id)
        return {
            "title": article.title,
            "content": article.content,
            "token_usage": article.token_usage,
        }
```

### 7.4 ConversationManager

```python
# app/services/workflow/conversation.py

from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.conversation_message import ConversationMessage

class ConversationManager:
    """对话上下文管理器"""

    async def add_message(
        self,
        db: AsyncSession,
        session_id: UUID,
        stage: str,
        role: str,
        content: str,
        metadata: dict | None = None,
    ) -> None:
        """保存单条消息"""
        message = ConversationMessage(
            session_id=session_id,
            stage=stage,
            role=role,
            content=content,
            metadata=metadata or {},
        )
        db.add(message)
        await db.flush()

    async def get_history(
        self,
        db: AsyncSession,
        session_id: UUID,
        stage: str,
        limit: int = 50,
    ) -> list[dict]:
        """获取指定阶段的对话历史"""
        result = await db.execute(
            select(ConversationMessage)
            .where(
                ConversationMessage.session_id == session_id,
                ConversationMessage.stage == stage,
            )
            .order_by(ConversationMessage.created_at.asc())
            .limit(limit)
        )
        messages = result.scalars().all()

        return [
            {
                "id": str(msg.id),
                "role": msg.role,
                "content": msg.content,
                "created_at": msg.created_at.isoformat(),
            }
            for msg in messages
        ]

    async def build_openai_messages(
        self,
        db: AsyncSession,
        session_id: UUID,
        stage: str,
    ) -> list[dict]:
        """构建OpenAI API所需的messages格式"""
        history = await self.get_history(db, session_id, stage)

        return [
            {"role": msg["role"], "content": msg["content"]}
            for msg in history
        ]


# 导出单例
conversation_mgr = ConversationManager()
```

---

## 八、实现检查清单

### 8.1 数据库迁移

- [ ] 创建`workflow_sessions`表
- [ ] 创建`conversation_messages`表
- [ ] 在`Article`模型添加relationship: `workflow_sessions`
- [ ] 运行Alembic迁移: `alembic revision --autogenerate -m "add workflow tables"`
- [ ] 应用迁移: `alembic upgrade head`

### 8.2 后端开发

#### 核心服务
- [ ] 实现`WorkflowEngine`类
- [ ] 实现`ConversationManager`类
- [ ] 实现`BaseStage`抽象类
- [ ] 实现`GenerateStage`处理器
- [ ] 实现`OptimizeStage`处理器
- [ ] 实现`ImageStage`处理器

#### API接口
- [ ] `POST /workflows/sessions` - 创建会话
- [ ] `POST /workflows/sessions/{id}/messages` - 发送消息
- [ ] `POST /workflows/sessions/{id}/next-stage` - 进入下一阶段
- [ ] `POST /workflows/sessions/{id}/execute-auto` - 执行全自动
- [ ] `GET /workflows/sessions/{id}/status` - 查询状态
- [ ] `GET /workflows/sessions/{id}/messages` - 获取历史

#### 重构现有服务
- [ ] 重构`ai_writer.py`支持传入历史消息（多轮对话）
- [ ] 确保`image_gen.py`可被工作流调用
- [ ] 确保`docx_generator.py`可被工作流调用

### 8.3 前端开发

#### 组件开发
- [ ] `ArticleWorkflow.vue` - 主容器
- [ ] `WorkflowStepper.vue` - 步骤条
- [ ] `ChatDialog.vue` - 对话框
- [ ] `PromptSelector.vue` - 提示词选择器
- [ ] `AutoProgress.vue` - 自动模式进度条
- [ ] `DocxPreview.vue` - 文档预览

#### 状态管理
- [ ] 创建`stores/workflow.ts`
- [ ] 实现`createSession`
- [ ] 实现`sendMessage`
- [ ] 实现`nextStage`
- [ ] 实现`executeAuto`
- [ ] 实现轮询逻辑

#### API封装
- [ ] 封装所有工作流API到`api/workflow.ts`

#### 路由配置
- [ ] 在`router/index.ts`添加`/workflow/:sessionId`路由

### 8.4 集成测试

- [ ] 测试半自动模式完整流程
- [ ] 测试全自动模式完整流程
- [ ] 测试多轮对话是否正确保存历史
- [ ] 测试阶段切换逻辑
- [ ] 测试异常处理（API失败、网络中断等）
- [ ] 测试并发场景（多个会话同时运行）

### 8.5 文档与优化

- [ ] 编写API文档（Swagger/OpenAPI）
- [ ] 添加日志记录（structlog）
- [ ] 添加性能监控（token消耗、执行时间）
- [ ] 优化前端加载性能
- [ ] 添加错误恢复机制

---

## 附录：技术决策记录

### ADR-001: 工作流状态管理策略

**决策**: 使用数据库表存储工作流状态，而非纯内存状态机

**理由**:
1. 支持分布式部署（多个worker可共享状态）
2. 会话可持久化，支持用户中断后继续
3. 便于追溯和调试

**代价**:
1. 每次状态转移需要数据库写入（性能开销）
2. 需要处理并发更新问题

### ADR-002: 全自动模式使用后台任务

**决策**: 全自动模式启动异步后台任务，前端轮询状态

**理由**:
1. 避免HTTP请求超时（整个流程可能需要1-2分钟）
2. 用户可查看实时进度
3. 实现相对简单（不需要WebSocket）

**代价**:
1. 轮询增加服务器负载
2. 进度更新有延迟（2秒间隔）

**备选方案**: WebSocket实时推送（后续优化可考虑）

### ADR-003: 对话历史粒度

**决策**: 只保存关键阶段的最终结果快照到`stage_data`，详细对话保存到独立表

**理由**:
1. `stage_data` JSONB字段用于快速读取各阶段结果
2. `conversation_messages`表用于完整追溯对话历史
3. 分离存储避免单条记录过大

**代价**:
1. 查询需要JOIN两张表
2. 需要维护数据一致性

---

**文档版本历史**:
- v1.0 (2025-12-19): 初始版本，完整架构设计
