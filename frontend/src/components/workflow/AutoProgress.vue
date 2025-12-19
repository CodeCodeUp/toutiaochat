<template>
  <div class="auto-progress glass-container">
    <div class="progress-header">
      <Loader2 v-if="status === 'processing'" :size="24" class="animate-spin text-blue-500" />
      <CheckCircle v-else-if="status === 'completed'" :size="24" class="text-green-500" />
      <XCircle v-else-if="status === 'failed'" :size="24" class="text-red-500" />
      <Zap v-else :size="24" class="text-gray-400" />

      <div class="progress-info">
        <h3 class="text-lg font-semibold">
          {{ statusLabels[status] }}
        </h3>
        <p class="text-sm text-gray-500">
          {{ stageLabels[currentStage] }}
        </p>
      </div>
    </div>

    <!-- 进度条 -->
    <div class="progress-bar-container">
      <div class="progress-bar">
        <div
          class="progress-fill"
          :class="{
            'bg-blue-500': status === 'processing',
            'bg-green-500': status === 'completed',
            'bg-red-500': status === 'failed',
          }"
          :style="{ width: `${progress}%` }"
        />
      </div>
      <span class="progress-text">{{ progress }}%</span>
    </div>

    <!-- 阶段列表 -->
    <div class="stage-list">
      <div
        v-for="stage in stages"
        :key="stage.key"
        class="stage-item"
        :class="{
          'stage-done': isStageCompleted(stage.key),
          'stage-current': stage.key === currentStage && status === 'processing',
        }"
      >
        <div class="stage-icon">
          <Check v-if="isStageCompleted(stage.key)" :size="14" />
          <Loader2
            v-else-if="stage.key === currentStage && status === 'processing'"
            :size="14"
            class="animate-spin"
          />
          <Circle v-else :size="14" />
        </div>
        <span>{{ stage.label }}</span>
      </div>
    </div>

    <!-- 错误信息 -->
    <div v-if="error" class="error-message">
      <AlertTriangle :size="18" />
      <span>{{ error }}</span>
    </div>

    <!-- 完成后的操作 -->
    <div v-if="status === 'completed'" class="completion-actions">
      <button class="btn-primary" @click="$emit('view-result')">
        <Eye :size="18" />
        查看结果
      </button>
      <button class="btn-secondary" @click="$emit('publish')">
        <Send :size="18" />
        立即发布
      </button>
    </div>

    <!-- 失败后的重试 -->
    <div v-if="status === 'failed'" class="completion-actions">
      <button class="btn-primary" @click="$emit('retry')">
        <RefreshCw :size="18" />
        重新执行
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import {
  Loader2,
  CheckCircle,
  XCircle,
  Zap,
  Check,
  Circle,
  AlertTriangle,
  Eye,
  Send,
  RefreshCw,
} from 'lucide-vue-next'
import type { WorkflowStage, WorkflowStatus } from '@/stores/workflow'

const props = defineProps<{
  progress: number
  status: WorkflowStatus
  currentStage: WorkflowStage
  error?: string | null
}>()

defineEmits<{
  (e: 'view-result'): void
  (e: 'publish'): void
  (e: 'retry'): void
}>()

const stages = [
  { key: 'generate' as WorkflowStage, label: '生成文章' },
  { key: 'optimize' as WorkflowStage, label: '优化润色' },
  { key: 'image' as WorkflowStage, label: '配图生成' },
  { key: 'completed' as WorkflowStage, label: '整合完成' },
]

const stageLabels: Record<WorkflowStage, string> = {
  generate: '正在生成文章...',
  optimize: '正在优化润色...',
  image: '正在生成配图...',
  edit: '正在整合...',
  completed: '全部完成',
}

const statusLabels: Record<WorkflowStatus, string> = {
  idle: '准备就绪',
  processing: '正在处理',
  completed: '处理完成',
  failed: '处理失败',
}

const stageOrder = ['generate', 'optimize', 'image', 'edit', 'completed']

function isStageCompleted(stage: WorkflowStage) {
  const currentIndex = stageOrder.indexOf(props.currentStage)
  const stageIndex = stageOrder.indexOf(stage)
  return stageIndex < currentIndex || props.status === 'completed'
}
</script>

<style scoped>
.auto-progress {
  @apply p-8 text-center;
}

.progress-header {
  @apply flex items-center justify-center gap-4 mb-8;
}

.progress-info h3 {
  @apply text-deep-black;
}

.progress-bar-container {
  @apply flex items-center gap-4 mb-8;
}

.progress-bar {
  @apply flex-1 h-3 bg-gray-100 rounded-full overflow-hidden;
}

.progress-fill {
  @apply h-full rounded-full transition-all duration-500;
}

.progress-text {
  @apply text-sm font-medium text-gray-600 w-12 text-right;
}

.stage-list {
  @apply flex justify-center gap-6 mb-8;
}

.stage-item {
  @apply flex items-center gap-2 text-sm text-gray-400;
}

.stage-icon {
  @apply w-5 h-5 rounded-full flex items-center justify-center;
  @apply bg-gray-100;
}

.stage-done {
  @apply text-green-600;
}

.stage-done .stage-icon {
  @apply bg-green-100 text-green-600;
}

.stage-current {
  @apply text-blue-600;
}

.stage-current .stage-icon {
  @apply bg-blue-100 text-blue-600;
}

.error-message {
  @apply flex items-center justify-center gap-2 p-4 mb-6;
  @apply bg-red-50 text-red-600 rounded-xl text-sm;
}

.completion-actions {
  @apply flex justify-center gap-4;
}

.btn-primary {
  @apply px-6 py-3 rounded-xl font-medium;
  @apply flex items-center gap-2;
  @apply bg-deep-black text-white;
  @apply hover:bg-gray-800 transition-colors;
  @apply active:scale-[0.98];
}

.btn-secondary {
  @apply px-6 py-3 rounded-xl font-medium;
  @apply flex items-center gap-2;
  @apply bg-green-500 text-white;
  @apply hover:bg-green-600 transition-colors;
  @apply active:scale-[0.98];
}
</style>
