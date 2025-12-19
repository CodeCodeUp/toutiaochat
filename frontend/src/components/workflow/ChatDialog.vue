<template>
  <div class="chat-dialog glass-container">
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
        :class="[`message-${msg.role}`]"
      >
        <div class="message-avatar">
          <User v-if="msg.role === 'user'" :size="20" />
          <Bot v-else :size="20" />
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
          <Bot :size="20" />
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

    <!-- 文章预览 -->
    <div v-if="articlePreview && articlePreview.title" class="article-preview">
      <div class="preview-header" @click="previewExpanded = !previewExpanded">
        <FileText :size="18" />
        <span class="font-medium">{{ articlePreview.title }}</span>
        <ChevronDown
          :size="18"
          class="ml-auto transition-transform"
          :class="{ 'rotate-180': previewExpanded }"
        />
      </div>
      <div v-show="previewExpanded" class="preview-content">
        <div class="prose prose-sm max-w-none">
          {{ articlePreview.content }}
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
      <button class="prompt-btn" @click="$emit('select-prompt')">
        <Sparkles :size="18" />
      </button>
      <textarea
        v-model="inputText"
        class="message-input"
        :placeholder="inputPlaceholder"
        rows="2"
        @keydown.ctrl.enter="handleSend"
        @keydown.meta.enter="handleSend"
      />
      <div class="input-actions">
        <button
          class="btn-send"
          :disabled="!inputText.trim() || loading"
          @click="handleSend"
        >
          <Send :size="18" />
        </button>
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
</template>

<script setup lang="ts">
import { ref, watch, nextTick } from 'vue'
import {
  MessageSquare,
  User,
  Bot,
  FileText,
  ChevronDown,
  Sparkles,
  Send,
  ArrowRight,
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
}>()

const emit = defineEmits<{
  (e: 'send', message: string): void
  (e: 'next-stage'): void
  (e: 'select-prompt'): void
  (e: 'use-suggestion', suggestion: string): void
}>()

const inputText = ref('')
const previewExpanded = ref(false)
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
.chat-dialog {
  @apply flex flex-col h-[600px];
}

.message-list {
  @apply flex-1 overflow-y-auto p-4 space-y-4;
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
  @apply bg-gray-100 text-gray-600;
}

.message-user .message-avatar {
  @apply bg-deep-black text-white;
}

.message-content {
  @apply max-w-[70%];
}

.message-text {
  @apply px-4 py-2.5 rounded-2xl text-sm leading-relaxed;
  @apply bg-gray-100 text-gray-800;
}

.message-user .message-text {
  @apply bg-deep-black text-white;
}

.message-time {
  @apply text-xs text-gray-400 mt-1 px-2;
}

.message-user .message-time {
  @apply text-right;
}

/* 打字动画 */
.typing-indicator {
  @apply flex gap-1 px-4 py-3;
}

.typing-indicator span {
  @apply w-2 h-2 rounded-full bg-gray-400;
  animation: typing 1.4s infinite ease-in-out;
}

.typing-indicator span:nth-child(2) {
  animation-delay: 0.2s;
}

.typing-indicator span:nth-child(3) {
  animation-delay: 0.4s;
}

@keyframes typing {
  0%,
  60%,
  100% {
    transform: translateY(0);
  }
  30% {
    transform: translateY(-4px);
  }
}

/* 文章预览 */
.article-preview {
  @apply mx-4 mb-4 rounded-xl border border-gray-200 overflow-hidden;
}

.preview-header {
  @apply flex items-center gap-2 px-4 py-3 bg-gray-50 cursor-pointer;
  @apply hover:bg-gray-100 transition-colors;
}

.preview-content {
  @apply p-4 bg-white max-h-48 overflow-y-auto;
  @apply text-sm text-gray-700 whitespace-pre-wrap;
}

/* 建议 */
.suggestions {
  @apply flex flex-wrap gap-2 px-4 mb-4;
}

.suggestion-chip {
  @apply px-3 py-1.5 text-xs rounded-full;
  @apply bg-gray-100 text-gray-600;
  @apply hover:bg-gray-200 transition-colors;
  @apply active:scale-95;
}

/* 输入区域 */
.input-area {
  @apply flex items-end gap-2 p-4 border-t border-gray-100;
}

.prompt-btn {
  @apply w-10 h-10 rounded-xl flex items-center justify-center;
  @apply bg-gray-100 text-gray-500;
  @apply hover:bg-gray-200 transition-colors;
  @apply active:scale-95;
}

.message-input {
  @apply flex-1 px-4 py-2.5 rounded-xl resize-none;
  @apply bg-gray-50 border border-gray-200;
  @apply focus:outline-none focus:border-gray-300 focus:ring-2 focus:ring-gray-100;
  @apply text-sm;
}

.input-actions {
  @apply flex flex-col gap-2;
}

.btn-send {
  @apply w-10 h-10 rounded-xl flex items-center justify-center;
  @apply bg-deep-black text-white;
  @apply hover:bg-gray-800 transition-colors;
  @apply disabled:opacity-50 disabled:cursor-not-allowed;
  @apply active:scale-95;
}

.btn-next {
  @apply px-4 py-2 rounded-xl text-xs font-medium;
  @apply flex items-center gap-1;
  @apply bg-green-500 text-white;
  @apply hover:bg-green-600 transition-colors;
  @apply disabled:opacity-50 disabled:cursor-not-allowed;
  @apply active:scale-95;
}
</style>
