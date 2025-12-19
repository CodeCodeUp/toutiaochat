<template>
  <div class="workflow-page">
    <!-- 页面头部 -->
    <header class="page-header">
      <div class="header-left">
        <button class="back-btn" @click="handleBack">
          <ArrowLeft :size="20" />
        </button>
        <div>
          <h1 class="page-title">{{ isCreating ? '创建文章' : '文章工作流' }}</h1>
          <p class="page-subtitle">
            {{ isCreating ? '选择模式开始创作' : workflowStore.currentStageLabel }}
          </p>
        </div>
      </div>
      <div v-if="!isCreating" class="header-right">
        <span class="mode-badge" :class="workflowStore.isAutoMode ? 'mode-auto' : 'mode-manual'">
          {{ workflowStore.isAutoMode ? '全自动' : '半自动' }}
        </span>
      </div>
    </header>

    <!-- 创建表单 -->
    <div v-if="isCreating" class="create-form glass-container">
      <div class="form-section">
        <label class="form-label">文章话题</label>
        <textarea
          v-model="createForm.topic"
          class="form-textarea"
          placeholder="请输入文章话题或素材，例如：AI技术在医疗领域的应用..."
          rows="4"
        />
      </div>

      <div class="form-row">
        <div class="form-section flex-1">
          <label class="form-label">文章分类</label>
          <select v-model="createForm.category" class="form-select">
            <option v-for="cat in categories" :key="cat" :value="cat">{{ cat }}</option>
          </select>
        </div>

        <div class="form-section flex-1">
          <label class="form-label">工作模式</label>
          <div class="mode-selector">
            <button
              class="mode-option"
              :class="{ 'mode-selected': createForm.mode === 'manual' }"
              @click="createForm.mode = 'manual'"
            >
              <MessageSquare :size="20" />
              <span>半自动</span>
              <small>逐步对话调整</small>
            </button>
            <button
              class="mode-option"
              :class="{ 'mode-selected': createForm.mode === 'auto' }"
              @click="createForm.mode = 'auto'"
            >
              <Zap :size="20" />
              <span>全自动</span>
              <small>一键生成完成</small>
            </button>
          </div>
        </div>
      </div>

      <div class="form-actions">
        <button class="btn-cancel" @click="handleBack">取消</button>
        <button
          class="btn-start"
          :disabled="!createForm.topic.trim() || creating"
          @click="handleCreate"
        >
          <Loader2 v-if="creating" :size="18" class="animate-spin" />
          <Play v-else :size="18" />
          开始创作
        </button>
      </div>
    </div>

    <!-- 工作流主体 -->
    <template v-else>
      <!-- 步骤条 -->
      <WorkflowStepper :current="workflowStore.currentStage" @step-click="handleStepClick" />

      <!-- 内容区域 -->
      <div class="workflow-content">
        <!-- 半自动模式 - 对话 -->
        <template v-if="!workflowStore.isAutoMode">
          <ChatDialog
            v-if="!workflowStore.isCompleted"
            :messages="workflowStore.messages"
            :loading="workflowStore.loading"
            :article-preview="workflowStore.articlePreview"
            :suggestions="workflowStore.suggestions"
            :can-proceed="workflowStore.canProceed"
            :placeholder="getStagePlaceholder()"
            :input-placeholder="getInputPlaceholder()"
            @send="handleSendMessage"
            @next-stage="handleNextStage"
            @select-prompt="showPromptSelector = true"
            @use-suggestion="handleUseSuggestion"
          />

          <!-- 完成状态 -->
          <div v-else class="completion-panel glass-container">
            <CheckCircle :size="64" class="text-green-500 mx-auto mb-4" />
            <h2 class="text-xl font-semibold mb-2">文章创作完成</h2>
            <p class="text-gray-500 mb-6">您可以预览文章内容或直接发布</p>

            <!-- 文章预览 -->
            <div v-if="workflowStore.articlePreview" class="article-final-preview">
              <h3 class="text-lg font-semibold mb-2">{{ workflowStore.articlePreview.title }}</h3>
              <div class="prose prose-sm max-h-64 overflow-y-auto">
                {{ workflowStore.articlePreview.full_content || workflowStore.articlePreview.content }}
              </div>
            </div>

            <div class="completion-actions">
              <button class="btn-secondary" @click="handleNewArticle">
                <Plus :size="18" />
                创建新文章
              </button>
              <button class="btn-primary" @click="handlePublish">
                <Send :size="18" />
                发布文章
              </button>
            </div>
          </div>
        </template>

        <!-- 全自动模式 - 进度 -->
        <template v-else>
          <AutoProgress
            :progress="workflowStore.progress"
            :status="workflowStore.status"
            :current-stage="workflowStore.currentStage"
            :error="workflowStore.error"
            @view-result="handleViewResult"
            @publish="handlePublish"
            @retry="handleRetry"
          />
        </template>
      </div>
    </template>

    <!-- 提示词选择器弹窗 -->
    <el-dialog v-model="showPromptSelector" title="选择提示词" width="500px">
      <div class="prompt-list">
        <div
          v-for="prompt in prompts"
          :key="prompt.id"
          class="prompt-item"
          @click="handleSelectPrompt(prompt)"
        >
          <div class="prompt-name">{{ prompt.name }}</div>
          <div class="prompt-preview">{{ prompt.content.slice(0, 100) }}...</div>
        </div>
        <div v-if="prompts.length === 0" class="empty-prompts">
          暂无可用提示词
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  ArrowLeft,
  MessageSquare,
  Zap,
  Play,
  Loader2,
  CheckCircle,
  Plus,
  Send,
} from 'lucide-vue-next'
import { useWorkflowStore } from '@/stores/workflow'
import { promptApi } from '@/api'
import WorkflowStepper from '@/components/workflow/WorkflowStepper.vue'
import ChatDialog from '@/components/workflow/ChatDialog.vue'
import AutoProgress from '@/components/workflow/AutoProgress.vue'

const router = useRouter()
const route = useRoute()
const workflowStore = useWorkflowStore()

// 分类列表
const categories = [
  '科技', '经济', '社会', '政治', '体育', '娱乐',
  '国际', '军事', '文化', '生活', '教育', '健康',
  '数码3C', '时事热点', '其他',
]

// 创建表单
const createForm = ref({
  topic: '',
  category: '科技',
  mode: 'manual' as 'auto' | 'manual',
})

const creating = ref(false)
const isCreating = computed(() => !workflowStore.sessionId)
const showPromptSelector = ref(false)
const prompts = ref<any[]>([])
const selectedPromptId = ref<string | null>(null)

// 阶段提示
function getStagePlaceholder() {
  const placeholders: Record<string, string> = {
    generate: '描述您想要的文章内容，AI将为您生成初稿',
    optimize: '告诉AI如何优化文章，例如：降低AI痕迹、调整语气',
    image: '描述您想要的配图，或选择跳过此阶段',
  }
  return placeholders[workflowStore.currentStage] || '请输入您的要求'
}

function getInputPlaceholder() {
  const placeholders: Record<string, string> = {
    generate: '输入创作要求，按 Ctrl+Enter 发送...',
    optimize: '输入优化要求...',
    image: '描述配图需求或输入"跳过"...',
  }
  return placeholders[workflowStore.currentStage] || '请输入...'
}

// 创建工作流
async function handleCreate() {
  if (!createForm.value.topic.trim()) {
    ElMessage.warning('请输入文章话题')
    return
  }

  creating.value = true
  try {
    await workflowStore.createSession({
      topic: createForm.value.topic,
      category: createForm.value.category,
      mode: createForm.value.mode,
    })

    // 如果是全自动模式，立即开始执行
    if (createForm.value.mode === 'auto') {
      await workflowStore.executeAuto()
    } else {
      // 半自动模式，发送初始消息
      await workflowStore.sendMessage(`请根据话题"${createForm.value.topic}"生成一篇文章`)
    }
  } catch (e: any) {
    ElMessage.error(e.message || '创建失败')
  } finally {
    creating.value = false
  }
}

// 发送消息
async function handleSendMessage(message: string) {
  try {
    await workflowStore.sendMessage(message, selectedPromptId.value || undefined)
    selectedPromptId.value = null
  } catch (e: any) {
    ElMessage.error(e.message || '发送失败')
  }
}

// 使用建议
function handleUseSuggestion(suggestion: string) {
  handleSendMessage(suggestion)
}

// 进入下一阶段
async function handleNextStage() {
  try {
    await ElMessageBox.confirm(
      '确定完成当前阶段并进入下一阶段？',
      '提示',
      { confirmButtonText: '确定', cancelButtonText: '取消' }
    )
    await workflowStore.nextStage()
  } catch (e: any) {
    if (e !== 'cancel') {
      ElMessage.error(e.message || '操作失败')
    }
  }
}

// 步骤点击
function handleStepClick(stage: string) {
  // 暂不支持跳转到历史阶段
  ElMessage.info('暂不支持跳转到历史阶段')
}

// 选择提示词
async function handleSelectPrompt(prompt: any) {
  selectedPromptId.value = prompt.id
  showPromptSelector.value = false
  ElMessage.success(`已选择提示词：${prompt.name}`)
}

// 加载提示词列表
async function loadPrompts() {
  try {
    const result: any = await promptApi.list({ type: workflowStore.currentStage })
    prompts.value = result.items || []
  } catch (e) {
    console.error('加载提示词失败', e)
  }
}

// 返回
function handleBack() {
  if (workflowStore.sessionId) {
    ElMessageBox.confirm('退出将丢失当前进度，确定退出？', '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning',
    }).then(() => {
      workflowStore.reset()
      router.push('/articles')
    }).catch(() => {})
  } else {
    router.push('/articles')
  }
}

// 新建文章
function handleNewArticle() {
  workflowStore.reset()
}

// 发布文章
function handlePublish() {
  if (workflowStore.articleId) {
    router.push(`/articles?publish=${workflowStore.articleId}`)
  }
}

// 查看结果
function handleViewResult() {
  // 切换到编辑状态查看
}

// 重试
async function handleRetry() {
  try {
    await workflowStore.executeAuto()
  } catch (e: any) {
    ElMessage.error(e.message || '重试失败')
  }
}

// 生命周期
onMounted(() => {
  // 如果URL有sessionId参数，加载会话
  const sessionId = route.query.session as string
  if (sessionId) {
    // TODO: 加载已有会话
  }
})

onUnmounted(() => {
  workflowStore.stopPolling()
})
</script>

<style scoped>
.workflow-page {
  @apply max-w-5xl mx-auto;
}

.page-header {
  @apply flex items-center justify-between mb-6;
}

.header-left {
  @apply flex items-center gap-4;
}

.back-btn {
  @apply w-10 h-10 rounded-xl flex items-center justify-center;
  @apply bg-white/60 backdrop-blur text-gray-600;
  @apply hover:bg-white transition-colors;
  @apply active:scale-95;
}

.page-title {
  @apply text-2xl font-bold text-deep-black;
}

.page-subtitle {
  @apply text-sm text-gray-500;
}

.mode-badge {
  @apply px-3 py-1 rounded-full text-xs font-medium;
}

.mode-auto {
  @apply bg-blue-100 text-blue-600;
}

.mode-manual {
  @apply bg-purple-100 text-purple-600;
}

/* 创建表单 */
.create-form {
  @apply p-8;
}

.form-section {
  @apply mb-6;
}

.form-label {
  @apply block text-sm font-medium text-gray-700 mb-2;
}

.form-textarea {
  @apply w-full px-4 py-3 rounded-xl;
  @apply bg-gray-50 border border-gray-200;
  @apply focus:outline-none focus:border-gray-300 focus:ring-2 focus:ring-gray-100;
  @apply resize-none;
}

.form-select {
  @apply w-full px-4 py-3 rounded-xl;
  @apply bg-gray-50 border border-gray-200;
  @apply focus:outline-none focus:border-gray-300;
}

.form-row {
  @apply flex gap-6;
}

.mode-selector {
  @apply flex gap-4;
}

.mode-option {
  @apply flex-1 p-4 rounded-xl text-left;
  @apply border-2 border-gray-200 bg-white;
  @apply hover:border-gray-300 transition-all;
  @apply active:scale-[0.98];
}

.mode-option span {
  @apply block font-medium text-gray-800;
}

.mode-option small {
  @apply block text-xs text-gray-500 mt-1;
}

.mode-selected {
  @apply border-deep-black bg-gray-50;
}

.form-actions {
  @apply flex justify-end gap-4 mt-8 pt-6 border-t border-gray-100;
}

.btn-cancel {
  @apply px-6 py-3 rounded-xl font-medium;
  @apply bg-gray-100 text-gray-600;
  @apply hover:bg-gray-200 transition-colors;
}

.btn-start {
  @apply px-8 py-3 rounded-xl font-medium;
  @apply flex items-center gap-2;
  @apply bg-deep-black text-white;
  @apply hover:bg-gray-800 transition-colors;
  @apply disabled:opacity-50 disabled:cursor-not-allowed;
}

/* 工作流内容 */
.workflow-content {
  @apply mt-6;
}

/* 完成面板 */
.completion-panel {
  @apply p-8 text-center;
}

.article-final-preview {
  @apply text-left p-6 bg-gray-50 rounded-xl mb-6;
}

.completion-actions {
  @apply flex justify-center gap-4;
}

.btn-primary {
  @apply px-6 py-3 rounded-xl font-medium;
  @apply flex items-center gap-2;
  @apply bg-deep-black text-white;
  @apply hover:bg-gray-800 transition-colors;
}

.btn-secondary {
  @apply px-6 py-3 rounded-xl font-medium;
  @apply flex items-center gap-2;
  @apply bg-gray-100 text-gray-600;
  @apply hover:bg-gray-200 transition-colors;
}

/* 提示词选择器 */
.prompt-list {
  @apply space-y-3 max-h-96 overflow-y-auto;
}

.prompt-item {
  @apply p-4 rounded-xl cursor-pointer;
  @apply bg-gray-50 hover:bg-gray-100 transition-colors;
}

.prompt-name {
  @apply font-medium text-gray-800;
}

.prompt-preview {
  @apply text-sm text-gray-500 mt-1;
}

.empty-prompts {
  @apply text-center text-gray-400 py-8;
}
</style>
