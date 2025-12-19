<template>
  <div class="workflow-stepper">
    <div class="steps-container">
      <div
        v-for="(step, index) in steps"
        :key="step.key"
        class="step-item"
        :class="{
          'step-active': currentIndex === index,
          'step-completed': currentIndex > index,
          'step-pending': currentIndex < index,
        }"
        @click="handleStepClick(step.key, index)"
      >
        <div class="step-indicator">
          <div class="step-circle">
            <Check v-if="currentIndex > index" :size="16" />
            <span v-else>{{ index + 1 }}</span>
          </div>
          <div v-if="index < steps.length - 1" class="step-line" />
        </div>
        <div class="step-content">
          <div class="step-title">{{ step.label }}</div>
          <div class="step-desc">{{ step.description }}</div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { Check } from 'lucide-vue-next'
import type { WorkflowStage } from '@/stores/workflow'

interface Step {
  key: WorkflowStage
  label: string
  description: string
}

const props = defineProps<{
  current: WorkflowStage
}>()

const emit = defineEmits<{
  (e: 'step-click', stage: WorkflowStage): void
}>()

const steps: Step[] = [
  { key: 'generate', label: '生成文章', description: '根据话题生成初稿' },
  { key: 'optimize', label: '优化润色', description: '降低AI痕迹，润色文章' },
  { key: 'image', label: '配图生成', description: '生成文章配图' },
  { key: 'edit', label: '编辑预览', description: '最终编辑和预览' },
  { key: 'completed', label: '完成', description: '准备发布' },
]

const currentIndex = computed(() => {
  return steps.findIndex((s) => s.key === props.current)
})

function handleStepClick(stage: WorkflowStage, index: number) {
  // 只允许点击已完成的步骤
  if (index < currentIndex.value) {
    emit('step-click', stage)
  }
}
</script>

<style scoped>
.workflow-stepper {
  @apply py-6 px-4;
}

.steps-container {
  @apply flex items-start justify-between max-w-4xl mx-auto;
}

.step-item {
  @apply flex flex-col items-center flex-1 relative cursor-default;
}

.step-indicator {
  @apply flex items-center w-full;
}

.step-circle {
  @apply w-10 h-10 rounded-full flex items-center justify-center;
  @apply text-sm font-semibold transition-all duration-300;
  @apply bg-gray-100 text-gray-400 border-2 border-gray-200;
}

.step-line {
  @apply flex-1 h-0.5 bg-gray-200 mx-2;
  @apply transition-all duration-300;
}

.step-content {
  @apply mt-3 text-center;
}

.step-title {
  @apply text-sm font-medium text-gray-500;
  @apply transition-colors duration-300;
}

.step-desc {
  @apply text-xs text-gray-400 mt-1 max-w-[100px];
}

/* 激活状态 */
.step-active .step-circle {
  @apply bg-deep-black text-white border-deep-black;
  @apply shadow-float;
}

.step-active .step-title {
  @apply text-deep-black font-semibold;
}

/* 已完成状态 */
.step-completed .step-circle {
  @apply bg-green-500 text-white border-green-500 cursor-pointer;
}

.step-completed .step-line {
  @apply bg-green-500;
}

.step-completed .step-title {
  @apply text-green-600;
}

.step-completed:hover .step-circle {
  @apply bg-green-600;
}
</style>
