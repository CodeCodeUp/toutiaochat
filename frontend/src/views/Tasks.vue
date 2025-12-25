<template>
  <div class="tasks-redesign max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
    <!-- 页面标题 -->
    <header class="mb-10 flex flex-col md:flex-row md:items-center md:justify-between gap-4">
      <div>
        <h1 class="text-4xl font-extrabold tracking-tight text-deep-black">
          任务队列
        </h1>
        <p class="mt-2 text-sm text-gray-500 font-medium">
          实时监控和管理后台执行的自动化任务
        </p>
      </div>
      <div class="flex items-center gap-3">
        <button class="btn-secondary flex items-center gap-2" @click="loadTasks">
          <RefreshCw :size="18" :stroke-width="2" :class="{ 'animate-spin': loading }" />
          刷新列表
        </button>
      </div>
    </header>

    <!-- 工具栏 -->
    <div class="glass-container p-4 mb-8 flex flex-col sm:flex-row items-center justify-between gap-4">
      <div class="flex items-center gap-3 w-full sm:w-auto">
        <div class="relative group w-full sm:w-40">
          <select
            v-model="filters.status"
            class="appearance-none bg-gray-50/50 border border-gray-200 text-gray-700 py-2.5 pl-4 pr-10 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all font-medium text-sm w-full cursor-pointer"
          >
            <option value="">所有状态</option>
            <option value="pending">等待中</option>
            <option value="running">执行中</option>
            <option value="completed">已完成</option>
            <option value="failed">失败</option>
          </select>
          <ChevronDown :size="16" class="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 pointer-events-none group-hover:text-gray-600 transition-colors" />
        </div>

        <div class="relative group w-full sm:w-40">
          <select
            v-model="filters.type"
            class="appearance-none bg-gray-50/50 border border-gray-200 text-gray-700 py-2.5 pl-4 pr-10 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all font-medium text-sm w-full cursor-pointer"
          >
            <option value="">所有类型</option>
            <option value="generate">生成文章</option>
            <option value="humanize">内容优化</option>
            <option value="image_gen">AI 生图</option>
            <option value="publish">发布内容</option>
          </select>
          <ChevronDown :size="16" class="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 pointer-events-none group-hover:text-gray-600 transition-colors" />
        </div>
      </div>
      
      <div class="text-xs text-gray-400 hidden sm:block">
        共 {{ pagination.total }} 个任务
      </div>
    </div>

    <!-- 任务列表 -->
    <div class="space-y-4">
      <div v-if="loading && tasks.length === 0" class="text-center py-20">
        <div class="animate-spin w-10 h-10 border-4 border-gray-100 border-t-deep-black rounded-full mx-auto"></div>
        <p class="mt-4 text-gray-400 font-medium">加载任务队列...</p>
      </div>

      <div v-else-if="tasks.length === 0" class="glass-container p-16 text-center border-dashed border-2 border-gray-200">
        <div class="w-20 h-20 bg-gray-50 rounded-full flex items-center justify-center mx-auto mb-6">
          <ListTodo :size="40" class="text-gray-300" />
        </div>
        <h3 class="text-lg font-bold text-gray-900 mb-2">队列空闲</h3>
        <p class="text-gray-500 max-w-sm mx-auto">
          当前没有正在进行或历史任务记录。
        </p>
      </div>

      <transition-group name="list" tag="div" class="grid grid-cols-1 gap-4">
        <div
          v-for="task in tasks"
          :key="task.id"
          class="bg-white rounded-xl border border-gray-100 shadow-sm hover:shadow-lg hover:border-gray-200 transition-all duration-300 relative overflow-hidden group"
        >
          <!-- 状态色条 -->
          <div class="absolute left-0 top-0 bottom-0 w-1.5" :class="getStatusColorBar(task.status)"></div>

          <div class="p-5 pl-7 flex flex-col sm:flex-row sm:items-center gap-5">
            <!-- 任务图标 -->
            <div
              class="w-12 h-12 rounded-xl flex items-center justify-center flex-shrink-0 shadow-sm"
              :class="getTypeIconBg(task.type)"
            >
              <component :is="getTypeIcon(task.type)" :size="22" :stroke-width="2" class="text-white" />
            </div>

            <!-- 任务信息 -->
            <div class="flex-1 min-w-0">
              <div class="flex items-center gap-3 mb-1.5">
                <h3 class="text-base font-bold text-gray-900">
                  {{ getTypeText(task.type) }}
                </h3>
                <span
                  class="px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider"
                  :class="getStatusBadge(task.status)"
                >
                  {{ getStatusText(task.status) }}
                </span>
              </div>

              <div class="flex items-center gap-4 text-xs text-gray-500">
                <span class="flex items-center gap-1">
                  <Clock :size="12" />
                  {{ formatDate(task.created_at) }}
                </span>
                <span v-if="task.retry_count > 0" class="flex items-center gap-1 text-orange-500 font-medium">
                  <RotateCw :size="12" />
                  已重试 {{ task.retry_count }} 次
                </span>
                <span class="font-mono text-gray-300">ID: {{ task.id.split('-')[0] }}</span>
              </div>
            </div>

            <!-- 错误信息 (如果失败) -->
            <div v-if="task.status === 'failed' && task.error_message" class="sm:max-w-xs w-full bg-red-50 rounded-lg p-3 border border-red-100">
              <div class="flex items-start gap-2">
                <AlertCircle :size="14" class="text-red-500 mt-0.5 flex-shrink-0" />
                <p class="text-xs text-red-600 line-clamp-2 break-all" :title="task.error_message">
                  {{ task.error_message }}
                </p>
              </div>
            </div>

            <!-- 操作按钮 -->
            <div class="flex items-center gap-2 flex-shrink-0 self-end sm:self-center ml-auto sm:ml-0">
              <button
                v-if="task.status === 'failed'"
                class="px-3 py-1.5 rounded-lg bg-white border border-gray-200 text-gray-600 hover:text-orange-600 hover:border-orange-200 hover:bg-orange-50 font-medium text-xs transition flex items-center gap-1.5 shadow-sm"
                @click="retryTask(task)"
              >
                <RotateCcw :size="14" />
                重试
              </button>

              <button
                v-if="task.status === 'pending' || task.status === 'running'"
                class="px-3 py-1.5 rounded-lg bg-white border border-gray-200 text-gray-600 hover:text-red-600 hover:border-red-200 hover:bg-red-50 font-medium text-xs transition flex items-center gap-1.5 shadow-sm"
                @click="cancelTask(task)"
              >
                <X :size="14" />
                取消
              </button>
            </div>
          </div>
        </div>
      </transition-group>

      <!-- 分页 -->
      <div v-if="tasks.length > 0" class="mt-8 flex justify-center py-4">
        <el-pagination
          v-model:current-page="pagination.page"
          v-model:page-size="pagination.pageSize"
          :total="pagination.total"
          layout="prev, pager, next"
          @current-change="loadTasks"
          background
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
  ChevronDown,
  AlertCircle
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
  await ElMessageBox.confirm('确定要重试这个任务吗？', '确认重试', {
    confirmButtonText: '立即重试',
    cancelButtonText: '取消',
    type: 'warning'
  })
  await taskApi.retry(row.id)
  ElMessage.success('任务已重新加入队列')
  loadTasks()
}

const cancelTask = async (row: any) => {
  await ElMessageBox.confirm('确定要取消这个任务吗？', '确认取消', { 
    confirmButtonText: '终止任务',
    cancelButtonText: '再等等',
    type: 'warning',
    confirmButtonClass: 'el-button--danger'
  })
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

const getStatusColorBar = (status: string) => {
  const map: Record<string, string> = {
    pending: 'bg-gray-300',
    running: 'bg-blue-500',
    completed: 'bg-green-500',
    failed: 'bg-red-500',
    cancelled: 'bg-gray-200',
  }
  return map[status] || 'bg-gray-300'
}

const getStatusBadge = (status: string) => {
  const map: Record<string, string> = {
    pending: 'bg-gray-100 text-gray-600',
    running: 'bg-blue-50 text-blue-600 animate-pulse',
    completed: 'bg-green-50 text-green-600',
    failed: 'bg-red-50 text-red-600',
    cancelled: 'bg-gray-50 text-gray-400 line-through',
  }
  return map[status] || 'bg-gray-100 text-gray-600'
}

const getTypeText = (type: string) => {
  const map: Record<string, string> = {
    generate: '生成文章',
    humanize: '内容优化',
    image_gen: '生成图片',
    publish: '发布内容',
  }
  return map[type] || type
}

const getStatusText = (status: string) => {
  const map: Record<string, string> = {
    pending: '等待执行',
    running: '正在运行',
    completed: '执行成功',
    failed: '执行失败',
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

.list-enter-active,
.list-leave-active {
  transition: all 0.3s ease;
}
.list-enter-from,
.list-leave-to {
  opacity: 0;
  transform: translateX(-10px);
}
</style>
