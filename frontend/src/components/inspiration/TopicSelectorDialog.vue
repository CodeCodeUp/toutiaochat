<template>
  <el-dialog
    v-model="visible"
    title="选择话题"
    width="600px"
    destroy-on-close
    @close="handleClose"
  >
    <!-- 搜索框 -->
    <div class="mb-4">
      <el-input
        v-model="searchKeyword"
        placeholder="搜索话题..."
        clearable
        @input="debouncedSearch"
      >
        <template #prefix>
          <Search :size="16" class="text-gray-400" />
        </template>
      </el-input>
    </div>

    <!-- 话题列表 -->
    <div v-if="loading" class="flex justify-center py-8">
      <el-icon class="is-loading" :size="24">
        <Loading />
      </el-icon>
    </div>

    <div v-else-if="topics.length === 0" class="text-center py-8 text-gray-400">
      <Lightbulb :size="32" class="mx-auto mb-2 opacity-50" />
      <p>暂无话题，请先同步</p>
    </div>

    <div v-else class="max-h-[400px] overflow-y-auto space-y-2 custom-scrollbar">
      <div
        v-for="topic in topics"
        :key="topic.id"
        class="topic-item p-3 rounded-lg border border-gray-100 hover:border-blue-200 hover:bg-blue-50/50 cursor-pointer transition-all flex items-center gap-3"
        :class="{ 'border-blue-500 bg-blue-50': isSelected(topic) }"
        @click="toggleSelect(topic)"
      >
        <div
          class="w-5 h-5 rounded border-2 flex items-center justify-center flex-shrink-0 transition-colors"
          :class="isSelected(topic) ? 'bg-blue-500 border-blue-500' : 'border-gray-300'"
        >
          <Check v-if="isSelected(topic)" :size="14" class="text-white" />
        </div>
        <div class="flex-1 min-w-0">
          <div class="text-sm font-medium text-gray-900 truncate">
            {{ topic.forum_name }}
          </div>
          <div class="text-xs text-gray-400 mt-0.5">
            已用 {{ topic.usage_count }} 次
          </div>
        </div>
      </div>
    </div>

    <!-- 已选中 -->
    <div v-if="selectedTopics.length > 0" class="mt-4 pt-4 border-t border-gray-100">
      <div class="text-xs text-gray-500 mb-2">已选择 {{ selectedTopics.length }} 个话题</div>
      <div class="flex flex-wrap gap-2">
        <el-tag
          v-for="topic in selectedTopics"
          :key="topic.id"
          closable
          @close="removeSelection(topic)"
        >
          {{ topic.forum_name }}
        </el-tag>
      </div>
    </div>

    <template #footer>
      <div class="flex justify-end gap-3">
        <el-button @click="handleClose">取消</el-button>
        <el-button
          type="primary"
          :disabled="selectedTopics.length === 0"
          @click="handleConfirm"
        >
          确定 ({{ selectedTopics.length }})
        </el-button>
      </div>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, watch, computed } from 'vue'
import { Loading } from '@element-plus/icons-vue'
import { Search, Lightbulb, Check } from 'lucide-vue-next'
import { inspirationApi, type InspirationTopicOption } from '@/api'

interface Props {
  modelValue: boolean
  multiple?: boolean
  initialSelected?: string[]  // 初始选中的话题名称
}

const props = withDefaults(defineProps<Props>(), {
  multiple: false,
  initialSelected: () => [],
})

const emit = defineEmits<{
  (e: 'update:modelValue', value: boolean): void
  (e: 'select', topics: string[]): void  // 返回话题名称数组
}>()

const visible = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val),
})

const loading = ref(false)
const searchKeyword = ref('')
const topics = ref<InspirationTopicOption[]>([])
const selectedTopics = ref<InspirationTopicOption[]>([])

// 加载话题
const loadTopics = async () => {
  loading.value = true
  try {
    const data = await inspirationApi.getTopicOptions({
      keyword: searchKeyword.value || undefined,
      limit: 50,
    })
    topics.value = data
  } catch (error) {
    console.error('加载话题失败:', error)
  } finally {
    loading.value = false
  }
}

// 防抖搜索
let searchTimer: ReturnType<typeof setTimeout> | null = null
const debouncedSearch = () => {
  if (searchTimer) clearTimeout(searchTimer)
  searchTimer = setTimeout(() => {
    loadTopics()
  }, 300)
}

// 是否选中
const isSelected = (topic: InspirationTopicOption) => {
  return selectedTopics.value.some(t => t.id === topic.id)
}

// 切换选择
const toggleSelect = (topic: InspirationTopicOption) => {
  if (props.multiple) {
    const index = selectedTopics.value.findIndex(t => t.id === topic.id)
    if (index >= 0) {
      selectedTopics.value.splice(index, 1)
    } else {
      selectedTopics.value.push(topic)
    }
  } else {
    // 单选模式
    if (isSelected(topic)) {
      selectedTopics.value = []
    } else {
      selectedTopics.value = [topic]
    }
  }
}

// 移除选择
const removeSelection = (topic: InspirationTopicOption) => {
  const index = selectedTopics.value.findIndex(t => t.id === topic.id)
  if (index >= 0) {
    selectedTopics.value.splice(index, 1)
  }
}

// 关闭
const handleClose = () => {
  visible.value = false
  searchKeyword.value = ''
  selectedTopics.value = []
}

// 确认
const handleConfirm = async () => {
  // 为选中的话题增加使用次数
  for (const topic of selectedTopics.value) {
    try {
      await inspirationApi.useTopic(topic.id)
    } catch (error) {
      console.error('更新使用次数失败:', error)
    }
  }

  // 返回话题名称
  const names = selectedTopics.value.map(t => t.forum_name)
  emit('select', names)
  handleClose()
}

// 监听打开
watch(visible, (val) => {
  if (val) {
    loadTopics()
    // 恢复初始选择
    if (props.initialSelected.length > 0) {
      // 这里需要根据名称匹配，在加载完成后处理
    }
  }
})
</script>

<style scoped>
.custom-scrollbar::-webkit-scrollbar {
  width: 6px;
}
.custom-scrollbar::-webkit-scrollbar-track {
  background: transparent;
}
.custom-scrollbar::-webkit-scrollbar-thumb {
  background-color: #e5e7eb;
  border-radius: 20px;
}

.topic-item:hover {
  transform: translateX(4px);
}
</style>
