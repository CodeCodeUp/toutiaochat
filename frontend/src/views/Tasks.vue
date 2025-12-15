<template>
  <div class="tasks-page">
    <h2 class="page-title">任务队列</h2>

    <el-card class="toolbar">
      <el-row :gutter="20" align="middle">
        <el-col :span="16">
          <el-space>
            <el-select v-model="filters.status" placeholder="状态筛选" clearable style="width: 140px">
              <el-option label="等待中" value="pending" />
              <el-option label="执行中" value="running" />
              <el-option label="已完成" value="completed" />
              <el-option label="失败" value="failed" />
            </el-select>
            <el-select v-model="filters.type" placeholder="类型筛选" clearable style="width: 140px">
              <el-option label="生成文章" value="generate" />
              <el-option label="去AI化" value="humanize" />
              <el-option label="生成图片" value="image_gen" />
              <el-option label="发布" value="publish" />
            </el-select>
            <el-button @click="loadTasks">
              <el-icon><Refresh /></el-icon>
              刷新
            </el-button>
          </el-space>
        </el-col>
      </el-row>
    </el-card>

    <el-card>
      <el-table :data="tasks" v-loading="loading" style="width: 100%">
        <el-table-column prop="type" label="类型" width="120">
          <template #default="{ row }">
            {{ getTypeText(row.type) }}
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.status)">
              {{ getStatusText(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="retry_count" label="重试次数" width="100" />
        <el-table-column prop="error_message" label="错误信息" min-width="200">
          <template #default="{ row }">
            <el-tooltip v-if="row.error_message" :content="row.error_message" placement="top">
              <span class="error-text">{{ row.error_message }}</span>
            </el-tooltip>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="160">
          <template #default="{ row }">
            {{ formatDate(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="150">
          <template #default="{ row }">
            <el-space>
              <el-button
                v-if="row.status === 'failed'"
                size="small"
                type="warning"
                @click="retryTask(row)"
              >
                重试
              </el-button>
              <el-button
                v-if="row.status === 'pending' || row.status === 'running'"
                size="small"
                type="danger"
                @click="cancelTask(row)"
              >
                取消
              </el-button>
            </el-space>
          </template>
        </el-table-column>
      </el-table>

      <el-pagination
        v-model:current-page="pagination.page"
        v-model:page-size="pagination.pageSize"
        :total="pagination.total"
        layout="total, prev, pager, next"
        style="margin-top: 20px; justify-content: flex-end"
        @current-change="loadTasks"
      />
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { taskApi } from '@/api'
import dayjs from 'dayjs'

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

const getTypeText = (type: string) => {
  const map: Record<string, string> = {
    generate: '生成文章',
    humanize: '去AI化',
    image_gen: '生成图片',
    publish: '发布',
  }
  return map[type] || type
}

const getStatusType = (status: string) => {
  const map: Record<string, string> = {
    pending: 'info',
    running: 'warning',
    completed: 'success',
    failed: 'danger',
    cancelled: 'info',
  }
  return map[status] || 'info'
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

const formatDate = (date: string) => dayjs(date).format('YYYY-MM-DD HH:mm')

watch([() => filters.status, () => filters.type], () => {
  pagination.page = 1
  loadTasks()
})

onMounted(loadTasks)
</script>

<style lang="scss" scoped>
.tasks-page {
  .page-title {
    margin-bottom: 20px;
    font-size: 20px;
    color: #303133;
  }

  .toolbar {
    margin-bottom: 20px;
  }

  .error-text {
    color: #F56C6C;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    display: block;
    max-width: 200px;
  }
}
</style>
