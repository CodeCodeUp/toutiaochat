<template>
  <div class="workflow-page">
    <!-- 页面头部 -->
    <header class="page-header">
      <div class="header-left">
        <button class="back-btn" @click="handleBack">
          <ArrowLeft :size="20" />
        </button>
        <div>
          <h1 class="page-title">{{ !workflowStore.isSessionActive ? '创建文章' : '文章工作流' }}</h1>
          <p class="page-subtitle">
            {{ !workflowStore.isSessionActive ? '选择模式开始创作' : workflowStore.currentStageLabel }}
          </p>
        </div>
      </div>
      <div v-if="workflowStore.isSessionActive" class="header-right">
        <span class="mode-badge" :class="workflowStore.isAutoMode ? 'mode-auto' : 'mode-manual'">
          {{ workflowStore.isAutoMode ? '全自动' : '半自动' }}
        </span>
      </div>
    </header>

    <!-- 创建表单 - 简化为模式选择 -->
    <div v-if="!workflowStore.isSessionActive" class="create-form glass-container">
      <div class="mode-selection">
        <h2 class="selection-title">选择创作模式</h2>
        <p class="selection-subtitle">半自动模式可以自由对话调整，全自动模式一键生成</p>

        <!-- 内容类型选择 -->
        <div class="content-type-selection">
          <button
            class="content-type-btn"
            :class="{ active: createForm.contentType === 'article' }"
            @click="createForm.contentType = 'article'"
          >
            <FileText :size="20" />
            <span>文章</span>
          </button>
          <button
            class="content-type-btn"
            :class="{ active: createForm.contentType === 'weitoutiao' }"
            @click="createForm.contentType = 'weitoutiao'"
          >
            <MessageCircle :size="20" />
            <span>微头条</span>
          </button>
        </div>

        <div class="mode-buttons">
          <button
            class="mode-card"
            :disabled="creating"
            @click="handleCreate('manual')"
          >
            <div class="mode-icon">
              <MessageSquare :size="32" />
            </div>
            <div class="mode-info">
              <span class="mode-title">半自动模式</span>
              <span class="mode-desc">自由对话，逐步调整</span>
            </div>
            <Loader2 v-if="creating && createForm.mode === 'manual'" :size="20" class="animate-spin" />
            <ArrowRight v-else :size="20" class="mode-arrow" />
          </button>

          <button
            class="mode-card"
            :disabled="creating"
            @click="handleCreate('auto')"
          >
            <div class="mode-icon mode-icon-auto">
              <Zap :size="32" />
            </div>
            <div class="mode-info">
              <span class="mode-title">全自动模式</span>
              <span class="mode-desc">一键生成，快速完成</span>
            </div>
            <Loader2 v-if="creating && createForm.mode === 'auto'" :size="20" class="animate-spin" />
            <ArrowRight v-else :size="20" class="mode-arrow" />
          </button>
        </div>
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
            :article-id="workflowStore.articleId"
            @send="handleSendMessage"
            @next-stage="handleNextStage"
            @select-prompt="handleOpenPromptSelector"
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
              <div class="article-content-preview" v-html="renderedArticleContent"></div>
            </div>

            <div class="completion-actions">
              <a
                v-if="workflowStore.articleId"
                :href="`/api/v1/articles/${workflowStore.articleId}/preview-docx`"
                class="btn-secondary"
                download
              >
                <Download :size="18" />
                下载 DOCX
              </a>
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

    <!-- 话题输入弹窗 -->
    <el-dialog
      v-model="showTopicDialog"
      title="输入创作话题"
      width="500px"
      :close-on-click-modal="false"
    >
      <div class="topic-input-container">
        <p class="text-gray-500 mb-4">请输入您想要创作的话题，AI 将根据此话题生成内容</p>
        <el-input
          v-model="customTopic"
          type="textarea"
          :rows="4"
          placeholder="例如：分享一个关于时间管理的实用技巧..."
          @keyup.ctrl.enter="handleConfirmTopic"
        />
      </div>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="showTopicDialog = false; pendingAutoCreate = false">取消</el-button>
          <el-button type="primary" :loading="creating" @click="handleConfirmTopic">
            开始创作
          </el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { marked } from 'marked'
import {
  ArrowLeft,
  ArrowRight,
  MessageSquare,
  MessageCircle,
  FileText,
  Zap,
  Loader2,
  CheckCircle,
  Plus,
  Send,
  Download,
} from 'lucide-vue-next'
import { useWorkflowStore } from '@/stores/workflow'
import { promptApi, workflowConfigApi } from '@/api'
import WorkflowStepper from '@/components/workflow/WorkflowStepper.vue'
import ChatDialog from '@/components/workflow/ChatDialog.vue'
import AutoProgress from '@/components/workflow/AutoProgress.vue'

// 配置 marked
marked.setOptions({
  breaks: true,
  gfm: true,
})

const router = useRouter()
const route = useRoute()
const workflowStore = useWorkflowStore()

// 创建表单
const createForm = ref({
  mode: 'manual' as 'auto' | 'manual',
  contentType: 'article' as 'article' | 'weitoutiao',
})

const creating = ref(false)
const showPromptSelector = ref(false)
const prompts = ref<any[]>([])
const selectedPromptId = ref<string | null>(null)

// 话题输入弹窗
const showTopicDialog = ref(false)
const customTopic = ref('')
const pendingAutoCreate = ref(false)

// 渲染 Markdown 为 HTML
const renderedArticleContent = computed(() => {
  const content = workflowStore.articlePreview?.full_content || workflowStore.articlePreview?.content
  if (!content) return ''
  return marked(content) as string
})

// 阶段提示
function getStagePlaceholder() {
  const placeholders: Record<string, string> = {
    generate: '描述您想要的文章内容，AI将为您生成初稿',
    optimize: '告诉AI如何优化文章，例如：降低AI痕迹、调整语气',
    image: '描述您想要的配图，或选择跳过此阶段',
    edit: '预览并编辑最终文章，确认无误后完成创作',
  }
  return placeholders[workflowStore.currentStage] || '请输入您的要求'
}

function getInputPlaceholder() {
  const placeholders: Record<string, string> = {
    generate: '输入创作要求，按 Ctrl+Enter 发送...',
    optimize: '输入优化要求...',
    image: '描述配图需求或输入"跳过"...',
    edit: '输入修改要求或"确认完成"...',
  }
  return placeholders[workflowStore.currentStage] || '请输入...'
}

// 创建工作流
async function handleCreate(mode: 'auto' | 'manual') {
  createForm.value.mode = mode

  // 全自动模式：检查是否需要输入自定义话题
  if (mode === 'auto') {
    try {
      const config: any = await workflowConfigApi.get(createForm.value.contentType)
      if (config.enable_custom_topic) {
        // 弹出话题输入框
        customTopic.value = ''
        showTopicDialog.value = true
        pendingAutoCreate.value = true
        return
      }
    } catch (e) {
      console.error('获取工作流配置失败', e)
    }
  }

  // 直接创建
  await doCreate(mode)
}

// 确认话题后创建
async function handleConfirmTopic() {
  if (!customTopic.value.trim()) {
    ElMessage.warning('请输入话题内容')
    return
  }
  showTopicDialog.value = false
  await doCreate('auto', customTopic.value.trim())
}

// 实际创建逻辑
async function doCreate(mode: 'auto' | 'manual', topic?: string) {
  creating.value = true

  try {
    await workflowStore.createSession({
      mode: mode,
      content_type: createForm.value.contentType,
      custom_topic: topic,
    })

    // 如果是全自动模式，立即开始执行
    if (mode === 'auto') {
      await workflowStore.executeAuto()
    } else {
      // 半自动模式：检查是否有多个提示词需要选择
      await checkAndShowPromptSelector()
    }
  } catch (e: any) {
    ElMessage.error(e.message || '创建失败')
  } finally {
    creating.value = false
    pendingAutoCreate.value = false
  }
}

// 发送消息
async function handleSendMessage(message: string) {
  try {
    await workflowStore.sendMessage(message, selectedPromptId.value || undefined)
    selectedPromptId.value = null
  } catch (e: any) {
    // 错误已在 store 中处理并显示在对话框，不需要额外提示
    console.error('消息发送失败', e)
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
    // 进入新阶段后检查是否有多个提示词需要选择
    await checkAndShowPromptSelector()
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

// 打开提示词选择器
async function handleOpenPromptSelector() {
  showPromptSelector.value = true
  await loadPrompts()
}

// 加载提示词列表
async function loadPrompts() {
  try {
    // 映射工作流阶段到提示词类型
    const stageToPromptType: Record<string, string> = {
      generate: 'generate',
      optimize: 'humanize',  // 后端用 humanize
      image: 'image',
    }
    const promptType = stageToPromptType[workflowStore.currentStage] || 'generate'
    const result: any = await promptApi.list({
      type: promptType,
      content_type: workflowStore.contentType,
    })
    // 后端直接返回数组
    prompts.value = Array.isArray(result) ? result : (result.items || [])
  } catch (e) {
    console.error('加载提示词失败', e)
    prompts.value = []
  }
}

// 检查并弹出提示词选择器（如果有多个提示词）
async function checkAndShowPromptSelector() {
  // edit 和 completed 阶段不需要选择提示词
  if (workflowStore.currentStage === 'edit' || workflowStore.currentStage === 'completed') {
    return
  }

  await loadPrompts()
  if (prompts.value.length > 1) {
    showPromptSelector.value = true
  }
}

// 返回
function handleBack() {
  if (workflowStore.isSessionActive) {
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
  // 重置 store 状态
  workflowStore.reset()
  // 重置本地表单状态
  createForm.value = {
    mode: 'manual',
    contentType: 'article',
  }
  customTopic.value = ''
  pendingAutoCreate.value = false
}

// 发布文章
function handlePublish() {
  if (workflowStore.articleId) {
    router.push(`/articles?publish=${workflowStore.articleId}`)
  }
}

// 查看结果 - 切换到半自动完成视图以显示文章内容
async function handleViewResult() {
  // 加载完整的会话详情
  await workflowStore.loadSessionDetail()
  // 切换为半自动模式以显示完成面板（包含文章预览）
  workflowStore.mode = 'manual'
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
  } else {
    // 没有指定会话ID，重置 store 状态，显示创建表单
    workflowStore.reset()
  }
})

onUnmounted(() => {
  workflowStore.stopPolling()
})
</script>

<style scoped>
.workflow-page {
  @apply max-w-7xl mx-auto;
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

/* 创建表单 - 模式选择 */
.create-form {
  @apply p-8;
}

.mode-selection {
  @apply text-center;
}

.selection-title {
  @apply text-2xl font-bold text-deep-black mb-2;
}

.selection-subtitle {
  @apply text-gray-500 mb-6;
}

/* 内容类型选择 */
.content-type-selection {
  @apply flex justify-center gap-4 mb-8;
}

.content-type-btn {
  @apply flex items-center gap-2 px-6 py-3 rounded-xl;
  @apply border-2 border-gray-200 bg-white;
  @apply text-gray-600 font-medium;
  @apply hover:border-gray-300 transition-all;
}

.content-type-btn.active {
  @apply border-deep-black bg-deep-black text-white;
}

.mode-buttons {
  @apply flex flex-col gap-4 max-w-md mx-auto;
}

.mode-card {
  @apply flex items-center gap-4 p-5 rounded-2xl;
  @apply bg-white border-2 border-gray-100;
  @apply hover:border-gray-300 hover:shadow-lg transition-all;
  @apply disabled:opacity-50 disabled:cursor-not-allowed;
  @apply active:scale-[0.98];
}

.mode-icon {
  @apply w-14 h-14 rounded-xl flex items-center justify-center;
  @apply bg-purple-100 text-purple-600;
}

.mode-icon-auto {
  @apply bg-blue-100 text-blue-600;
}

.mode-info {
  @apply flex-1 text-left;
}

.mode-title {
  @apply block font-semibold text-gray-800 text-lg;
}

.mode-desc {
  @apply block text-sm text-gray-500 mt-0.5;
}

.mode-arrow {
  @apply text-gray-400;
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

/* Markdown 内容预览 */
.article-content-preview {
  @apply text-sm text-gray-700 leading-relaxed max-h-64 overflow-y-auto;
}

.article-content-preview :deep(h1),
.article-content-preview :deep(h2),
.article-content-preview :deep(h3) {
  @apply font-bold text-gray-800 mt-4 mb-2;
}

.article-content-preview :deep(h1) { @apply text-xl; }
.article-content-preview :deep(h2) { @apply text-lg; }
.article-content-preview :deep(h3) { @apply text-base; }

.article-content-preview :deep(p) {
  @apply mb-3 leading-relaxed;
}

.article-content-preview :deep(ul),
.article-content-preview :deep(ol) {
  @apply pl-5 mb-3;
}

.article-content-preview :deep(li) {
  @apply mb-1;
}

.article-content-preview :deep(ul) {
  @apply list-disc;
}

.article-content-preview :deep(ol) {
  @apply list-decimal;
}

.article-content-preview :deep(strong) {
  @apply font-bold;
}

.article-content-preview :deep(em) {
  @apply italic;
}

.article-content-preview :deep(blockquote) {
  @apply border-l-4 border-gray-300 pl-4 italic text-gray-600 my-3;
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
