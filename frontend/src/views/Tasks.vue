<template>
  <div class="tasks-redesign">
    <!-- 页面标题 -->
    <header class="mb-10">
      <h1 class="text-4xl font-extrabold tracking-tight text-deep-black">
        任务队列
      </h1>
      <p class="mt-2 text-sm text-gray-500">
        监控和管理后台任务执行状态
      </p>
    </header>

    <!-- 工具栏 -->
    <div class="glass-container p-6 mb-8 flex items-center justify-between">
      <div class="flex items-center gap-4">
        <select
          v-model="filters.status"
          class="input-inset text-sm font-medium cursor-pointer"
        >
          <option value="">全部状态</option>
          <option value="pending">等待中</option>
          <option value="running">执行中</option>
          <option value="completed">已完成</option>
          <option value="failed">失败</option>
        </select>

        <select
          v-model="filters.type"
          class="input-inset text-sm font-medium cursor-pointer"
        >
          <option value="">全部类型</option>
          <option value="generate">生成文章</option>
          <option value="humanize">去AI化</option>
          <option value="image_gen">生成图片</option>
          <option value="publish">发布</option>
        </select>

        <button class="btn-secondary flex items-center gap-2" @click="loadTasks">
          <RefreshCw :size="18" :stroke-width="2" />
          刷新
        </button>
      </div>
    </div>

    <!-- 任务列表 -->
    <div class="glass-container p-8">
      <div v-if="loading" class="text-center py-12">
        <div class="animate-spin w-8 h-8 border-4 border-gray-200 border-t-deep-black rounded-full mx-auto"></div>
        <p class="mt-4 text-gray-500">加载中...</p>
      </div>

      <div v-else-if="tasks.length === 0" class="text-center py-12 text-gray-400">
        <ListTodo :size="48" :stroke-width="1.5" class="mx-auto mb-3 opacity-50" />
        <p>暂无任务</p>
      </div>

      <div v-else class="space-y-3">
        <div
          v-for="task in tasks"
          :key="task.id"
          class="glass-card p-6 flex items-start gap-6 group"
        >
          <!-- 任务图标 -->
          <div
            class="w-12 h-12 rounded-2xl flex items-center justify-center flex-shrink-0"
            :class="getTypeIconBg(task.type)"
          >
            <component :is="getTypeIcon(task.type)" :size="24" :stroke-width="2" class="text-white" />
          </div>

          <!-- 任务信息 -->
          <div class="flex-1 min-w-0">
            <div class="flex items-center gap-3 mb-2">
              <h3 class="text-lg font-bold text-deep-black">
                {{ getTypeText(task.type) }}
              </h3>
              <span
                class="px-2 py-1 rounded-lg text-xs font-bold uppercase tracking-wider flex-shrink-0"
                :class="getStatusClass(task.status)"
              >
                {{ getStatusText(task.status) }}
              </span>
            </div>

            <div v-if="task.error_message" class="mb-3 p-3 rounded-lg bg-red-50/50 border border-red-100">
              <p class="text-sm text-red-600 line-clamp-2">
                {{ task.error_message }}
              </p>
            </div>

            <div class="flex items-center gap-4 text-xs text-gray-400">
              <span class="flex items-center gap-1">
                <Clock :size="12" />
                {{ formatDate(task.created_at) }}
              </span>
              <span class="flex items-center gap-1">
                <RotateCw :size="12" />
                重试 {{ task.retry_count }} 次
              </span>
            </div>
          </div>

          <!-- 操作 -->
          <div class="flex items-center gap-2 flex-shrink-0">
            <button
              v-if="task.status === 'failed'"
              class="px-4 py-2 rounded-lg bg-orange-100 hover:bg-orange-200 text-orange-600 font-semibold text-sm transition flex items-center gap-2"
              @click="retryTask(task)"
            >
              <RotateCcw :size="16" :stroke-width="2" />
              重试
            </button>

            <button
              v-if="task.status === 'pending' || task.status === 'running'"
              class="px-4 py-2 rounded-lg bg-red-100 hover:bg-red-200 text-red-600 font-semibold text-sm transition flex items-center gap-2"
              @click="cancelTask(task)"
            >
              <X :size="16" :stroke-width="2" />
              取消
            </button>
          </div>
        </div>
      </div>

      <!-- 分页 -->
      <div v-if="tasks.length > 0" class="mt-8 flex justify-center">
        <el-pagination
          v-model:current-page="pagination.page"
          v-model:page-size="pagination.pageSize"
          :total="pagination.total"
          layout="total, prev, pager, next"
          @current-change="loadTasks"
        />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { taskApi } from '@/api'
import dayjs from 'dayjs'
import {
  RefreshCw,
  ListTodo,
  Clock,
  RotateCw,
  RotateCcw,
  X,
  Sparkles,
  Wand2,
  Image as ImageIcon,
  Send,
} from 'lucide-vue-next'

const loading = ref(false)
const tasks = ref([])

const filters = reactive({
  status: '',
  type: '',
})

const pagination = reactive({
  page: 1,
  pageSize: 20,
  total: 0,
})

const loadTasks = async () => {
  loading.value = true
  try {
    const res: any = await taskApi.list({
      page: pagination.page,
      page_size: pagination.pageSize,
      status: filters.status || undefined,
      task_type: filters.type || undefined,
    })
    tasks.value = res.items || []
    pagination.total = res.total || 0
  } catch (e) {
    console.error(e)
  } finally {
    loading.value = false
  }
}

const retryTask = async (row: any) => {
  await ElMessageBox.confirm('确定要重试这个任务吗？', '确认重试')
  await taskApi.retry(row.id)
  ElMessage.success('任务已重新加入队列')
  loadTasks()
}

const cancelTask = async (row: any) => {
  await ElMessageBox.confirm('确定要取消这个任务吗？', '确认取消', { type: 'warning' })
  await taskApi.cancel(row.id)
  ElMessage.success('任务已取消')
  loadTasks()
}

const getTypeIcon = (type: string) => {
  const map: Record<string, any> = {
    generate: Sparkles,
    humanize: Wand2,
    image_gen: ImageIcon,
    publish: Send,
  }
  return map[type] || ListTodo
}

const getTypeIconBg = (type: string) => {
  const map: Record<string, string> = {
    generate: 'bg-blue-500',
    humanize: 'bg-green-500',
    image_gen: 'bg-purple-500',
    publish: 'bg-orange-500',
  }
  return map[type] || 'bg-gray-500'
}

const getStatusClass = (status: string) => {
  const map: Record<string, string> = {
    pending: 'bg-gray-100 text-gray-600',
    running: 'bg-blue-100 text-blue-600',
    completed: 'bg-green-100 text-green-600',
    failed: 'bg-red-100 text-red-600',
    cancelled: 'bg-gray-100 text-gray-500',
  }
  return map[status] || 'bg-gray-100 text-gray-600'
}

const getTypeText = (type: string) => {
  const map: Record<string, string> = {
    generate: '生成文章',
    humanize: '去AI化',
    image_gen: '生成图片',
    publish: '发布',
  }
  return map[type] || type
}

const getStatusText = (status: string) => {
  const map: Record<string, string> = {
    pending: '等待中',
    running: '执行中',
    completed: '已完成',
    failed: '失败',
    cancelled: '已取消',
  }
  return map[status] || status
}

const formatDate = (date: string) => dayjs(date).format('MM-DD HH:mm')

watch([() => filters.status, () => filters.type], () => {
  pagination.page = 1
  loadTasks()
})

onMounted(loadTasks)
</script>

<style scoped>
.tasks-redesign {
  @apply animate-in;
}

.line-clamp-2 {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
</style>
