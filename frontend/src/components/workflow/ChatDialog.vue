<template>
  <div class="chat-layout">
    <!-- 左侧：对话区域 -->
    <div class="chat-panel">
      <!-- 消息列表 -->
      <div ref="messageListRef" class="message-list">
        <div v-if="messages.length === 0" class="empty-state">
          <MessageSquare :size="48" class="text-gray-300" />
          <p class="mt-4 text-gray-500">{{ placeholder }}</p>
        </div>

        <div
          v-for="msg in messages"
          :key="msg.id"
          class="message-item"
          :class="[
            `message-${msg.role}`,
            { 'message-error': msg.extra_data?.is_error }
          ]"
        >
          <div class="message-avatar">
            <User v-if="msg.role === 'user'" :size="18" />
            <Bot v-else :size="18" />
          </div>
          <div class="message-content">
            <div class="message-text">{{ msg.content }}</div>
            <div class="message-time">
              {{ formatTime(msg.created_at) }}
            </div>
          </div>
        </div>

        <!-- 加载中 -->
        <div v-if="loading" class="message-item message-assistant">
          <div class="message-avatar">
            <Bot :size="18" />
          </div>
          <div class="message-content">
            <div class="typing-indicator">
              <span></span>
              <span></span>
              <span></span>
            </div>
          </div>
        </div>
      </div>

      <!-- 建议操作 -->
      <div v-if="suggestions.length > 0" class="suggestions">
        <button
          v-for="(suggestion, index) in suggestions"
          :key="index"
          class="suggestion-chip"
          @click="$emit('use-suggestion', suggestion)"
        >
          {{ suggestion }}
        </button>
      </div>

      <!-- 输入区域 -->
      <div class="input-area">
        <div class="input-row">
          <button class="prompt-btn" title="选择提示词" @click="$emit('select-prompt')">
            <Sparkles :size="18" />
          </button>
          <textarea
            v-model="inputText"
            class="message-input"
            :placeholder="inputPlaceholder"
            rows="3"
            @keydown.ctrl.enter="handleSend"
            @keydown.meta.enter="handleSend"
          />
          <button
            class="btn-send"
            :disabled="!inputText.trim() || loading"
            @click="handleSend"
          >
            <Send :size="18" />
          </button>
        </div>
        <div class="input-footer">
          <span class="input-hint">Ctrl + Enter 发送</span>
          <button
            v-if="canProceed"
            class="btn-next"
            :disabled="loading"
            @click="$emit('next-stage')"
          >
            完成此阶段
            <ArrowRight :size="16" />
          </button>
        </div>
      </div>
    </div>

    <!-- 右侧：文章预览 -->
    <div class="preview-panel">
      <template v-if="articlePreview && articlePreview.title">
        <!-- 预览头部 -->
        <div class="preview-header">
          <div class="preview-title-row">
            <FileText :size="20" class="text-gray-400" />
            <h2 class="preview-title">{{ articlePreview.title }}</h2>
          </div>
          <div class="preview-actions">
            <a
              v-if="articleId"
              :href="`/api/v1/articles/${articleId}/preview-docx`"
              class="action-btn"
              title="下载 DOCX"
              download
            >
              <Download :size="16" />
            </a>
            <button
              class="action-btn"
              title="全屏预览"
              @click="showFullscreen = true"
            >
              <Maximize2 :size="16" />
            </button>
          </div>
        </div>

        <!-- 文章内容 -->
        <div class="preview-body">
          <div class="article-content prose prose-sm">
            {{ articlePreview.full_content || articlePreview.content }}
          </div>
        </div>

        <!-- 配图预览 -->
        <div v-if="articlePreview.images?.length" class="images-section">
          <div class="images-header">
            <ImageIcon :size="16" />
            <span>配图 ({{ articlePreview.images.length }})</span>
          </div>
          <div class="images-grid">
            <div
              v-for="(img, idx) in articlePreview.images"
              :key="idx"
              class="image-thumb"
            >
              <img :src="img.url" :alt="`配图${idx + 1}`" />
              <span class="image-position">{{ formatPosition(img.position) }}</span>
            </div>
          </div>
        </div>

        <!-- 图片描述预览 -->
        <div v-else-if="articlePreview.image_prompts?.length" class="prompts-section">
          <div class="prompts-header">
            <ImageIcon :size="16" />
            <span>待生成配图 ({{ articlePreview.image_prompts.length }})</span>
          </div>
          <div class="prompts-list">
            <div
              v-for="(prompt, idx) in articlePreview.image_prompts"
              :key="idx"
              class="prompt-item"
            >
              <span class="prompt-index">{{ idx + 1 }}</span>
              <span class="prompt-position">{{ formatPosition(prompt.position) }}</span>
              <span class="prompt-desc">{{ prompt.description || prompt }}</span>
            </div>
          </div>
        </div>
      </template>

      <!-- 无内容时 -->
      <div v-else class="empty-preview">
        <FileText :size="48" class="text-gray-200" />
        <p class="text-gray-400 mt-3">文章预览将在这里显示</p>
      </div>
    </div>

    <!-- 全屏预览弹窗 -->
    <el-dialog
      v-model="showFullscreen"
      :title="articlePreview?.title || '文章预览'"
      width="90%"
      top="5vh"
      destroy-on-close
    >
      <div class="fullscreen-content">
        <div class="prose prose-lg max-w-none">
          {{ articlePreview?.full_content || articlePreview?.content }}
        </div>
      </div>
      <template #footer>
        <div class="flex justify-between">
          <a
            v-if="articleId"
            :href="`/api/v1/articles/${articleId}/preview-docx`"
            class="btn-secondary"
            download
          >
            <Download :size="16" />
            下载 DOCX
          </a>
          <el-button type="primary" @click="showFullscreen = false">关闭</el-button>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, nextTick } from 'vue'
import {
  MessageSquare,
  User,
  Bot,
  FileText,
  Sparkles,
  Send,
  ArrowRight,
  Download,
  Maximize2,
  Image as ImageIcon,
} from 'lucide-vue-next'
import type { Message, ArticlePreview } from '@/stores/workflow'

const props = defineProps<{
  messages: Message[]
  loading?: boolean
  articlePreview?: ArticlePreview | null
  suggestions?: string[]
  canProceed?: boolean
  placeholder?: string
  inputPlaceholder?: string
  articleId?: string | null
}>()

const emit = defineEmits<{
  (e: 'send', message: string): void
  (e: 'next-stage'): void
  (e: 'select-prompt'): void
  (e: 'use-suggestion', suggestion: string): void
}>()

const inputText = ref('')
const showFullscreen = ref(false)
const messageListRef = ref<HTMLElement | null>(null)

// 发送消息
function handleSend() {
  if (!inputText.value.trim() || props.loading) return
  emit('send', inputText.value.trim())
  inputText.value = ''
}

// 格式化时间
function formatTime(dateStr: string) {
  const date = new Date(dateStr)
  return date.toLocaleTimeString('zh-CN', {
    hour: '2-digit',
    minute: '2-digit',
  })
}

// 格式化位置
function formatPosition(pos: string | undefined) {
  if (!pos) return '正文'
  if (pos === 'cover') return '封面'
  if (pos === 'end') return '结尾'
  if (pos.startsWith('after_paragraph:')) {
    return `第${pos.split(':')[1]}段后`
  }
  return pos
}

// 滚动到底部
function scrollToBottom() {
  nextTick(() => {
    if (messageListRef.value) {
      messageListRef.value.scrollTop = messageListRef.value.scrollHeight
    }
  })
}

// 监听消息变化自动滚动
watch(
  () => props.messages.length,
  () => scrollToBottom()
)
</script>

<style scoped>
.chat-layout {
  @apply flex gap-4 h-[calc(100vh-220px)] min-h-[500px];
}

/* 左侧对话面板 */
.chat-panel {
  @apply flex flex-col w-[55%] bg-white/70 backdrop-blur-sm rounded-2xl border border-gray-100 shadow-sm;
}

.message-list {
  @apply flex-1 overflow-y-auto p-5 space-y-4;
}

.empty-state {
  @apply flex flex-col items-center justify-center h-full text-center;
}

.message-item {
  @apply flex gap-3;
}

.message-user {
  @apply flex-row-reverse;
}

.message-avatar {
  @apply w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0;
  @apply bg-gray-100 text-gray-500;
}

.message-user .message-avatar {
  @apply bg-deep-black text-white;
}

.message-content {
  @apply max-w-[80%];
}

.message-text {
  @apply px-4 py-3 rounded-2xl text-sm leading-relaxed whitespace-pre-wrap;
  @apply bg-gray-100 text-gray-800;
}

.message-user .message-text {
  @apply bg-deep-black text-white;
}

.message-time {
  @apply text-xs text-gray-400 mt-1.5 px-2;
}

.message-user .message-time {
  @apply text-right;
}

.message-error .message-text {
  @apply bg-red-50 text-red-700 border border-red-200;
}

.message-error .message-avatar {
  @apply bg-red-100 text-red-600;
}

/* 打字动画 */
.typing-indicator {
  @apply flex gap-1.5 px-4 py-3;
}

.typing-indicator span {
  @apply w-2 h-2 rounded-full bg-gray-400;
  animation: typing 1.4s infinite ease-in-out;
}

.typing-indicator span:nth-child(2) { animation-delay: 0.2s; }
.typing-indicator span:nth-child(3) { animation-delay: 0.4s; }

@keyframes typing {
  0%, 60%, 100% { transform: translateY(0); }
  30% { transform: translateY(-4px); }
}

/* 建议按钮 */
.suggestions {
  @apply flex flex-wrap gap-2 px-5 py-3 border-t border-gray-100 bg-gray-50/50;
}

.suggestion-chip {
  @apply px-3 py-1.5 text-xs rounded-full font-medium;
  @apply bg-white text-gray-600 border border-gray-200;
  @apply hover:bg-gray-100 hover:border-gray-300 transition-all;
  @apply active:scale-95;
}

/* 输入区域 */
.input-area {
  @apply p-4 border-t border-gray-100 bg-white/80;
}

.input-row {
  @apply flex items-end gap-3;
}

.prompt-btn {
  @apply w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0;
  @apply bg-gray-100 text-gray-500;
  @apply hover:bg-gray-200 hover:text-gray-700 transition-colors;
  @apply active:scale-95;
}

.message-input {
  @apply flex-1 px-4 py-3 rounded-xl resize-none;
  @apply bg-gray-50 border border-gray-200;
  @apply focus:outline-none focus:border-gray-300 focus:ring-2 focus:ring-gray-100;
  @apply text-sm leading-relaxed;
}

.btn-send {
  @apply w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0;
  @apply bg-deep-black text-white;
  @apply hover:bg-gray-800 transition-colors;
  @apply disabled:opacity-40 disabled:cursor-not-allowed;
  @apply active:scale-95;
}

.input-footer {
  @apply flex items-center justify-between mt-3;
}

.input-hint {
  @apply text-xs text-gray-400;
}

.btn-next {
  @apply px-5 py-2 rounded-xl text-sm font-medium;
  @apply flex items-center gap-1.5;
  @apply bg-green-500 text-white;
  @apply hover:bg-green-600 transition-colors;
  @apply disabled:opacity-50 disabled:cursor-not-allowed;
  @apply active:scale-95;
}

/* 右侧预览面板 */
.preview-panel {
  @apply flex flex-col w-[45%] bg-white/70 backdrop-blur-sm rounded-2xl border border-gray-100 shadow-sm overflow-hidden;
}

.preview-header {
  @apply flex items-center justify-between px-5 py-4 border-b border-gray-100 bg-gray-50/50;
}

.preview-title-row {
  @apply flex items-center gap-3 flex-1 min-w-0;
}

.preview-title {
  @apply text-lg font-bold text-gray-800 truncate;
}

.preview-actions {
  @apply flex items-center gap-2;
}

.action-btn {
  @apply w-8 h-8 rounded-lg flex items-center justify-center;
  @apply text-gray-400 hover:text-gray-600 hover:bg-gray-100 transition-colors;
}

.preview-body {
  @apply flex-1 overflow-y-auto p-5;
}

.article-content {
  @apply text-sm text-gray-700 leading-relaxed whitespace-pre-wrap;
}

.empty-preview {
  @apply flex-1 flex flex-col items-center justify-center;
}

/* 配图区域 */
.images-section,
.prompts-section {
  @apply border-t border-gray-100 p-4 bg-gray-50/50;
}

.images-header,
.prompts-header {
  @apply flex items-center gap-2 text-sm font-medium text-gray-600 mb-3;
}

.images-grid {
  @apply grid grid-cols-3 gap-2;
}

.image-thumb {
  @apply relative aspect-square rounded-lg overflow-hidden bg-gray-100;
}

.image-thumb img {
  @apply w-full h-full object-cover;
}

.image-position {
  @apply absolute bottom-0 left-0 right-0 px-2 py-1 text-xs text-white bg-black/50;
}

.prompts-list {
  @apply space-y-2;
}

.prompt-item {
  @apply flex items-start gap-2 text-xs;
}

.prompt-index {
  @apply w-5 h-5 rounded-full bg-gray-200 text-gray-600 flex items-center justify-center flex-shrink-0;
}

.prompt-position {
  @apply px-2 py-0.5 rounded bg-blue-100 text-blue-600 flex-shrink-0;
}

.prompt-desc {
  @apply text-gray-600 line-clamp-2;
}

/* 全屏预览 */
.fullscreen-content {
  @apply max-h-[70vh] overflow-y-auto p-4;
}

.btn-secondary {
  @apply px-4 py-2 rounded-lg text-sm font-medium;
  @apply flex items-center gap-2;
  @apply bg-gray-100 text-gray-600;
  @apply hover:bg-gray-200 transition-colors;
}

/* 响应式 */
@media (max-width: 1024px) {
  .chat-layout {
    @apply flex-col h-auto;
  }

  .chat-panel,
  .preview-panel {
    @apply w-full;
  }

  .chat-panel {
    @apply h-[500px];
  }

  .preview-panel {
    @apply h-[400px];
  }
}
</style>
