<template>
  <div class="scheduled-tasks">
    <!-- 页面标题 -->
    <header class="mb-10">
      <h1 class="text-4xl font-extrabold tracking-tight text-deep-black">
        定时任务
      </h1>
      <p class="mt-2 text-sm text-gray-500">
        配置自动生成和发布任务
      </p>
    </header>

    <!-- 调度器状态 -->
    <div class="glass-container p-6 mb-8 flex items-center justify-between">
      <div class="flex items-center gap-6">
        <div class="flex items-center gap-2">
          <div
            class="w-3 h-3 rounded-full"
            :class="schedulerStatus.running ? 'bg-green-500 animate-pulse' : 'bg-gray-400'"
          ></div>
          <span class="text-sm text-gray-600">
            调度器: {{ schedulerStatus.running ? '运行中' : '已停止' }}
          </span>
        </div>
        <div class="text-sm text-gray-500">
          活跃任务: {{ schedulerStatus.active_tasks }}
        </div>
        <div class="text-sm text-gray-500">
          待执行: {{ schedulerStatus.pending_jobs }}
        </div>
      </div>

      <div class="flex items-center gap-3">
        <button class="btn-secondary flex items-center gap-2" @click="loadData">
          <RefreshCw :size="18" :stroke-width="2" />
          刷新
        </button>

        <button
          v-if="schedulerStatus.running"
          class="btn-secondary flex items-center gap-2"
          @click="pauseScheduler"
        >
          <Pause :size="18" :stroke-width="2" />
          暂停全部
        </button>
        <button
          v-else
          class="btn-secondary flex items-center gap-2"
          @click="resumeScheduler"
        >
          <Play :size="18" :stroke-width="2" />
          恢复全部
        </button>

        <button class="btn-primary flex items-center gap-2" @click="openCreateDialog">
          <Plus :size="20" :stroke-width="2" />
          新建任务
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
        <Calendar :size="48" :stroke-width="1.5" class="mx-auto mb-3 opacity-50" />
        <p>暂无定时任务</p>
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
            :class="getTaskTypeStyle(task.type)"
          >
            <component :is="getTaskTypeIcon(task.type)" :size="24" :stroke-width="2" class="text-white" />
          </div>

          <!-- 任务信息 -->
          <div class="flex-1 min-w-0">
            <div class="flex items-center gap-3 mb-2">
              <h3 class="text-lg font-bold text-deep-black">
                {{ task.name }}
              </h3>
              <span
                class="px-2 py-0.5 rounded text-xs font-medium"
                :class="task.content_type === 'ARTICLE' ? 'bg-blue-100 text-blue-600' : 'bg-purple-100 text-purple-600'"
              >
                {{ task.content_type === 'ARTICLE' ? '文章' : '微头条' }}
              </span>
            </div>

            <div class="flex items-center gap-4 text-sm text-gray-500 mb-2">
              <span class="flex items-center gap-1">
                <Clock :size="14" />
                {{ formatSchedule(task) }}
              </span>
              <span v-if="task.active_start_hour !== 0 || task.active_end_hour !== 24" class="flex items-center gap-1">
                <Sun :size="14" />
                {{ task.active_start_hour }}:00 - {{ task.active_end_hour }}:00
              </span>
              <span class="flex items-center gap-1">
                <Hash :size="14" />
                已执行 {{ task.run_count }} 次
              </span>
            </div>

            <div class="flex items-center gap-4 text-xs text-gray-400">
              <span v-if="task.next_run_at" class="flex items-center gap-1">
                <Timer :size="12" />
                下次: {{ formatDate(task.next_run_at) }}
              </span>
              <span v-if="task.last_run_at" class="flex items-center gap-1">
                <History :size="12" />
                上次: {{ formatDate(task.last_run_at) }}
              </span>
              <span v-if="task.last_error" class="text-red-500 flex items-center gap-1">
                <AlertCircle :size="12" />
                {{ task.last_error.substring(0, 50) }}...
              </span>
            </div>
          </div>

          <!-- 状态和操作 -->
          <div class="flex items-center gap-3 flex-shrink-0">
            <el-switch
              v-model="task.is_active"
              @change="toggleTask(task)"
              :loading="task._toggling"
            />

            <el-dropdown trigger="click">
              <button class="w-8 h-8 rounded-lg hover:bg-gray-100/50 flex items-center justify-center transition">
                <MoreVertical :size="18" :stroke-width="2" class="text-gray-500" />
              </button>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item @click="triggerTask(task)">
                    <Play :size="14" class="mr-2" /> 立即执行
                  </el-dropdown-item>
                  <el-dropdown-item @click="openEditDialog(task)">
                    <Edit :size="14" class="mr-2" /> 编辑
                  </el-dropdown-item>
                  <el-dropdown-item @click="viewLogs(task)">
                    <FileText :size="14" class="mr-2" /> 执行日志
                  </el-dropdown-item>
                  <el-dropdown-item divided @click="deleteTask(task)">
                    <Trash2 :size="14" class="mr-2" /> 删除
                  </el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </div>
        </div>
      </div>
    </div>

    <!-- 创建/编辑对话框 -->
    <el-dialog
      v-model="showFormDialog"
      :title="editingTask ? '编辑任务' : '新建任务'"
      width="700px"
      destroy-on-close
    >
      <el-form :model="form" label-width="100px" class="pr-4">
        <!-- 基本信息 -->
        <el-divider content-position="left">基本信息</el-divider>

        <el-form-item label="任务名称" required>
          <el-input v-model="form.name" placeholder="如: 每日微头条" />
        </el-form-item>

        <el-form-item label="任务类型" required>
          <el-radio-group v-model="form.type">
            <el-radio-button value="GENERATE">仅生成</el-radio-button>
            <el-radio-button value="PUBLISH">仅发布</el-radio-button>
            <el-radio-button value="GENERATE_AND_PUBLISH">生成并发布</el-radio-button>
          </el-radio-group>
        </el-form-item>

        <el-form-item label="内容类型" required>
          <el-radio-group v-model="form.content_type">
            <el-radio-button value="ARTICLE">文章</el-radio-button>
            <el-radio-button value="WEITOUTIAO">微头条</el-radio-button>
          </el-radio-group>
        </el-form-item>

        <!-- 调度配置 -->
        <el-divider content-position="left">调度配置</el-divider>

        <el-form-item label="调度模式" required>
          <el-radio-group v-model="form.schedule_mode">
            <el-radio-button value="RANDOM_INTERVAL">随机间隔</el-radio-button>
            <el-radio-button value="INTERVAL">固定间隔</el-radio-button>
            <el-radio-button value="CRON">Cron表达式</el-radio-button>
          </el-radio-group>
        </el-form-item>

        <!-- 随机间隔配置 -->
        <el-form-item v-if="form.schedule_mode === 'RANDOM_INTERVAL'" label="间隔范围">
          <div class="flex items-center gap-2">
            <el-input-number v-model="form.schedule_config.min_minutes" :min="1" :max="1440" />
            <span class="text-gray-500">~</span>
            <el-input-number v-model="form.schedule_config.max_minutes" :min="1" :max="1440" />
            <span class="text-gray-500">分钟</span>
          </div>
        </el-form-item>

        <!-- 固定间隔配置 -->
        <el-form-item v-if="form.schedule_mode === 'INTERVAL'" label="间隔时间">
          <div class="flex items-center gap-2">
            <el-input-number v-model="form.schedule_config.minutes" :min="1" :max="1440" />
            <span class="text-gray-500">分钟</span>
          </div>
        </el-form-item>

        <!-- Cron配置 -->
        <el-form-item v-if="form.schedule_mode === 'CRON'" label="Cron表达式">
          <el-input v-model="form.schedule_config.cron" placeholder="0 9 * * *" />
          <div class="text-xs text-gray-400 mt-1">格式: 分 时 日 月 周</div>
        </el-form-item>

        <!-- 活跃时段 -->
        <el-form-item v-if="form.schedule_mode !== 'CRON'" label="活跃时段">
          <div class="flex items-center gap-2">
            <el-input-number v-model="form.active_start_hour" :min="0" :max="23" />
            <span class="text-gray-500">:00 ~</span>
            <el-input-number v-model="form.active_end_hour" :min="1" :max="24" />
            <span class="text-gray-500">:00</span>
          </div>
          <div class="text-xs text-gray-400 mt-1">仅在此时段内执行任务</div>
        </el-form-item>

        <!-- 话题配置 (生成类型) -->
        <template v-if="form.type !== 'PUBLISH'">
          <el-divider content-position="left">话题配置</el-divider>

          <el-form-item label="话题模式">
            <el-radio-group v-model="form.topic_mode">
              <el-radio-button value="RANDOM">AI自选</el-radio-button>
              <el-radio-button value="FIXED">固定话题</el-radio-button>
              <el-radio-button value="LIST">话题列表</el-radio-button>
            </el-radio-group>
          </el-form-item>

          <el-form-item v-if="form.topic_mode === 'FIXED'" label="固定话题">
            <el-input v-model="topicInput" placeholder="输入话题" />
          </el-form-item>

          <el-form-item v-if="form.topic_mode === 'LIST'" label="话题列表">
            <div class="w-full">
              <div v-for="(topic, index) in form.topics" :key="index" class="flex items-center gap-2 mb-2">
                <el-input v-model="form.topics[index]" placeholder="输入话题" />
                <el-button type="danger" :icon="Minus" circle size="small" @click="form.topics.splice(index, 1)" />
              </div>
              <el-button type="primary" :icon="Plus" size="small" @click="form.topics.push('')">添加话题</el-button>
            </div>
            <div class="text-xs text-gray-400 mt-1">话题将轮流使用</div>
          </el-form-item>
        </template>

        <!-- 发布配置 -->
        <template v-if="form.type !== 'GENERATE'">
          <el-divider content-position="left">发布配置</el-divider>

          <el-form-item label="发布账号" required>
            <el-select v-model="form.account_id" placeholder="选择账号" style="width: 100%">
              <el-option
                v-for="account in accounts"
                :key="account.id"
                :label="account.nickname"
                :value="account.id"
              />
            </el-select>
          </el-form-item>

          <el-form-item v-if="form.type === 'PUBLISH'" label="发布模式">
            <el-radio-group v-model="form.publish_mode">
              <el-radio-button value="ONE">每次一篇</el-radio-button>
              <el-radio-button value="BATCH">批量发布</el-radio-button>
              <el-radio-button value="ALL">全部发布</el-radio-button>
            </el-radio-group>
          </el-form-item>

          <el-form-item v-if="form.type === 'PUBLISH' && form.publish_mode === 'BATCH'" label="批量数量">
            <el-input-number v-model="form.publish_batch_size" :min="1" :max="10" />
          </el-form-item>

          <el-form-item v-if="form.type === 'PUBLISH'" label="发布顺序">
            <el-radio-group v-model="form.publish_order">
              <el-radio-button value="oldest">最早优先</el-radio-button>
              <el-radio-button value="newest">最新优先</el-radio-button>
              <el-radio-button value="random">随机</el-radio-button>
            </el-radio-group>
          </el-form-item>
        </template>
      </el-form>

      <template #footer>
        <el-button @click="showFormDialog = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="saveTask">
          {{ editingTask ? '保存' : '创建' }}
        </el-button>
      </template>
    </el-dialog>

    <!-- 执行日志对话框 -->
    <el-dialog v-model="showLogsDialog" title="执行日志" width="800px">
      <div v-if="logsLoading" class="text-center py-8">
        <div class="animate-spin w-6 h-6 border-4 border-gray-200 border-t-deep-black rounded-full mx-auto"></div>
      </div>
      <el-table v-else :data="logs" stripe>
        <el-table-column prop="started_at" label="执行时间" width="180">
          <template #default="{ row }">
            {{ formatDate(row.started_at) }}
          </template>
        </el-table-column>
        <el-table-column prop="type" label="类型" width="120">
          <template #default="{ row }">
            {{ formatTaskType(row.type) }}
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <span
              class="px-2 py-1 rounded text-xs font-medium"
              :class="{
                'bg-green-100 text-green-600': row.status === 'completed',
                'bg-red-100 text-red-600': row.status === 'failed',
                'bg-yellow-100 text-yellow-600': row.status === 'running',
              }"
            >
              {{ formatStatus(row.status) }}
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="error_message" label="错误信息" show-overflow-tooltip />
      </el-table>
      <div class="mt-4 flex justify-center">
        <el-pagination
          v-model:current-page="logsPage"
          :page-size="10"
          :total="logsTotal"
          layout="prev, pager, next"
          @current-change="loadLogs"
        />
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, computed, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  scheduledTaskApi,
  schedulerApi,
  accountApi,
  type ScheduledTask,
  type ScheduledTaskCreate,
  type SchedulerStatus,
} from '@/api'
import dayjs from 'dayjs'
import {
  Plus,
  Minus,
  RefreshCw,
  Calendar,
  Clock,
  Sun,
  Hash,
  Timer,
  History,
  AlertCircle,
  MoreVertical,
  Play,
  Pause,
  Edit,
  FileText,
  Trash2,
  FileEdit,
  Send,
  Zap,
} from 'lucide-vue-next'

const loading = ref(false)
const saving = ref(false)
const tasks = ref<(ScheduledTask & { _toggling?: boolean })[]>([])
const accounts = ref<any[]>([])
const schedulerStatus = ref<SchedulerStatus>({
  running: false,
  active_tasks: 0,
  pending_jobs: 0,
})

// 表单相关
const showFormDialog = ref(false)
const editingTask = ref<ScheduledTask | null>(null)
const topicInput = ref('')

const defaultForm = (): ScheduledTaskCreate => ({
  name: '',
  type: 'GENERATE_AND_PUBLISH',
  content_type: 'WEITOUTIAO',
  schedule_mode: 'RANDOM_INTERVAL',
  schedule_config: {
    min_minutes: 80,
    max_minutes: 200,
  },
  active_start_hour: 5,
  active_end_hour: 20,
  topic_mode: 'RANDOM',
  topics: [],
  account_id: undefined,
  publish_mode: 'ONE',
  publish_batch_size: 1,
  publish_order: 'oldest',
  is_active: true,
})

const form = reactive<ScheduledTaskCreate>(defaultForm())

// 日志相关
const showLogsDialog = ref(false)
const logsLoading = ref(false)
const logs = ref<any[]>([])
const logsPage = ref(1)
const logsTotal = ref(0)
const currentTaskId = ref('')

// 监听话题模式变化
watch(() => form.topic_mode, (mode) => {
  if (mode === 'FIXED') {
    form.topics = topicInput.value ? [topicInput.value] : []
  }
})

watch(topicInput, (val) => {
  if (form.topic_mode === 'FIXED') {
    form.topics = val ? [val] : []
  }
})

const loadData = async () => {
  loading.value = true
  try {
    const [tasksRes, statusRes, accountsRes] = await Promise.all([
      scheduledTaskApi.list(),
      schedulerApi.status(),
      accountApi.list(),
    ])
    tasks.value = (tasksRes as any).items || []
    schedulerStatus.value = statusRes as SchedulerStatus
    accounts.value = (accountsRes as any).items || []
  } catch (e) {
    console.error(e)
  } finally {
    loading.value = false
  }
}

const openCreateDialog = () => {
  editingTask.value = null
  Object.assign(form, defaultForm())
  topicInput.value = ''
  showFormDialog.value = true
}

const openEditDialog = (task: ScheduledTask) => {
  editingTask.value = task
  Object.assign(form, {
    name: task.name,
    type: task.type,
    content_type: task.content_type,
    schedule_mode: task.schedule_mode,
    schedule_config: { ...task.schedule_config },
    active_start_hour: task.active_start_hour,
    active_end_hour: task.active_end_hour,
    topic_mode: task.topic_mode,
    topics: [...(task.topics || [])],
    account_id: task.account_id,
    publish_mode: task.publish_mode,
    publish_batch_size: task.publish_batch_size,
    publish_order: task.publish_order,
    is_active: task.is_active,
  })
  topicInput.value = task.topics?.[0] || ''
  showFormDialog.value = true
}

const saveTask = async () => {
  if (!form.name) {
    ElMessage.warning('请输入任务名称')
    return
  }

  if (form.type !== 'GENERATE' && !form.account_id) {
    ElMessage.warning('请选择发布账号')
    return
  }

  saving.value = true
  try {
    if (editingTask.value) {
      await scheduledTaskApi.update(editingTask.value.id, form)
      ElMessage.success('保存成功')
    } else {
      await scheduledTaskApi.create(form)
      ElMessage.success('创建成功')
    }
    showFormDialog.value = false
    loadData()
  } catch (e) {
    console.error(e)
  } finally {
    saving.value = false
  }
}

const toggleTask = async (task: ScheduledTask & { _toggling?: boolean }) => {
  task._toggling = true
  try {
    await scheduledTaskApi.toggle(task.id)
    ElMessage.success(task.is_active ? '已启用' : '已禁用')
    loadData()
  } catch (e) {
    task.is_active = !task.is_active
    console.error(e)
  } finally {
    task._toggling = false
  }
}

const triggerTask = async (task: ScheduledTask) => {
  await ElMessageBox.confirm('确定要立即执行此任务吗？', '确认执行', { type: 'info' })
  try {
    await scheduledTaskApi.trigger(task.id)
    ElMessage.success('任务已触发，请稍后查看执行日志')
  } catch (e) {
    console.error(e)
  }
}

const deleteTask = async (task: ScheduledTask) => {
  await ElMessageBox.confirm('确定要删除此任务吗？', '确认删除', { type: 'warning' })
  try {
    await scheduledTaskApi.delete(task.id)
    ElMessage.success('删除成功')
    loadData()
  } catch (e) {
    console.error(e)
  }
}

const viewLogs = async (task: ScheduledTask) => {
  currentTaskId.value = task.id
  logsPage.value = 1
  showLogsDialog.value = true
  await loadLogs()
}

const loadLogs = async () => {
  logsLoading.value = true
  try {
    const res: any = await scheduledTaskApi.logs(currentTaskId.value, {
      skip: (logsPage.value - 1) * 10,
      limit: 10,
    })
    logs.value = res.items || []
    logsTotal.value = res.total || 0
  } catch (e) {
    console.error(e)
  } finally {
    logsLoading.value = false
  }
}

const pauseScheduler = async () => {
  try {
    await schedulerApi.pause()
    ElMessage.success('调度器已暂停')
    loadData()
  } catch (e) {
    console.error(e)
  }
}

const resumeScheduler = async () => {
  try {
    await schedulerApi.resume()
    ElMessage.success('调度器已恢复')
    loadData()
  } catch (e) {
    console.error(e)
  }
}

// 格式化函数
const formatDate = (date: string) => dayjs(date).format('MM-DD HH:mm')

const formatSchedule = (task: ScheduledTask) => {
  if (task.schedule_mode === 'CRON') {
    return `Cron: ${task.schedule_config.cron}`
  } else if (task.schedule_mode === 'INTERVAL') {
    return `每 ${task.schedule_config.minutes} 分钟`
  } else {
    return `${task.schedule_config.min_minutes}-${task.schedule_config.max_minutes} 分钟随机`
  }
}

const formatTaskType = (type: string) => {
  const map: Record<string, string> = {
    GENERATE: '生成',
    PUBLISH: '发布',
    GENERATE_AND_PUBLISH: '生成并发布',
    SCHEDULED_GENERATE: '定时生成',
    SCHEDULED_PUBLISH: '定时发布',
    SCHEDULED_GENERATE_PUBLISH: '定时生成发布',
  }
  return map[type] || type
}

const formatStatus = (status: string) => {
  const map: Record<string, string> = {
    pending: '等待中',
    running: '执行中',
    completed: '已完成',
    failed: '失败',
  }
  return map[status] || status
}

const getTaskTypeStyle = (type: string) => {
  const styles: Record<string, string> = {
    GENERATE: 'bg-gradient-to-br from-blue-500 to-indigo-600',
    PUBLISH: 'bg-gradient-to-br from-green-500 to-emerald-600',
    GENERATE_AND_PUBLISH: 'bg-gradient-to-br from-purple-500 to-pink-600',
  }
  return styles[type] || 'bg-gradient-to-br from-gray-500 to-gray-600'
}

const getTaskTypeIcon = (type: string) => {
  const icons: Record<string, any> = {
    GENERATE: FileEdit,
    PUBLISH: Send,
    GENERATE_AND_PUBLISH: Zap,
  }
  return icons[type] || Calendar
}

onMounted(loadData)
</script>

<style scoped>
.scheduled-tasks {
  @apply animate-in;
}
</style>
