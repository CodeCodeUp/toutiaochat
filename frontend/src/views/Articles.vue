<template>
  <div class="articles-redesign">
    <!-- 页面标题 -->
    <header class="mb-10">
      <h1 class="text-4xl font-extrabold tracking-tight text-deep-black">
        文章管理
      </h1>
      <p class="mt-2 text-sm text-gray-500">
        管理和发布您的内容创作
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
          <option value="draft">草稿</option>
          <option value="publishing">发布中</option>
          <option value="published">已发布</option>
          <option value="failed">失败</option>
        </select>

        <button class="btn-secondary flex items-center gap-2" @click="loadArticles">
          <RefreshCw :size="18" :stroke-width="2" />
          刷新
        </button>
      </div>

      <button class="btn-primary flex items-center gap-2" @click="router.push('/articles/workflow')">
        <Plus :size="20" :stroke-width="2" />
        创建文章
      </button>
    </div>

    <!-- 文章列表 -->
    <div class="glass-container p-8">
      <div v-if="loading" class="text-center py-12">
        <div class="animate-spin w-8 h-8 border-4 border-gray-200 border-t-deep-black rounded-full mx-auto"></div>
        <p class="mt-4 text-gray-500">加载中...</p>
      </div>

      <div v-else-if="articles.length === 0" class="text-center py-12 text-gray-400">
        <FileText :size="48" :stroke-width="1.5" class="mx-auto mb-3 opacity-50" />
        <p>暂无文章</p>
      </div>

      <div v-else class="space-y-3">
        <div
          v-for="article in articles"
          :key="article.id"
          class="glass-card p-6 flex items-start gap-6 group"
        >
          <!-- 文章图标 -->
          <div class="w-12 h-12 rounded-2xl bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center flex-shrink-0">
            <FileText :size="24" :stroke-width="2" class="text-white" />
          </div>

          <!-- 文章信息 -->
          <div class="flex-1 min-w-0">
            <h3 class="text-lg font-bold text-deep-black mb-2 truncate group-hover:text-blue-600 transition cursor-pointer"
                @click="showDetail(article)">
              {{ article.title }}
            </h3>

            <div class="flex items-center gap-4 text-sm text-gray-500">
              <span class="flex items-center gap-1">
                <Tag :size="14" />
                {{ article.category }}
              </span>
              <span class="flex items-center gap-1">
                <Coins :size="14" />
                {{ article.token_usage }} tokens
              </span>
              <span class="flex items-center gap-1">
                <Clock :size="14" />
                {{ formatDate(article.created_at) }}
              </span>
            </div>
          </div>

          <!-- 状态和操作 -->
          <div class="flex items-center gap-3 flex-shrink-0">
            <span
              class="px-3 py-1 rounded-lg text-xs font-bold uppercase tracking-wider"
              :class="getStatusClass(article.status)"
            >
              {{ getStatusText(article.status) }}
            </span>

            <el-dropdown trigger="click">
              <button class="w-8 h-8 rounded-lg hover:bg-gray-100/50 flex items-center justify-center transition">
                <MoreVertical :size="18" :stroke-width="2" class="text-gray-500" />
              </button>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item @click="showDetail(article)">查看</el-dropdown-item>
                  <el-dropdown-item v-if="article.status === 'draft'" @click="editArticle(article)">编辑</el-dropdown-item>
                  <el-dropdown-item v-if="article.status === 'draft' || article.status === 'failed'" @click="publishArticle(article)">发布</el-dropdown-item>
                  <el-dropdown-item v-if="article.status === 'draft'" @click="regenerateArticle(article)">重新生成</el-dropdown-item>
                  <el-dropdown-item divided @click="deleteArticle(article)">删除</el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </div>
        </div>
      </div>

      <!-- 分页 -->
      <div v-if="articles.length > 0" class="mt-8 flex justify-center">
        <el-pagination
          v-model:current-page="pagination.page"
          v-model:page-size="pagination.pageSize"
          :total="pagination.total"
          layout="total, prev, pager, next"
          @current-change="loadArticles"
        />
      </div>
    </div>

    <!-- 创建文章对话框 -->
    <el-dialog v-model="showCreateDialog" title="创建文章" width="600px">
      <el-form :model="createForm" label-width="100px">
        <el-form-item label="话题/素材" required>
          <el-input
            v-model="createForm.topic"
            type="textarea"
            :rows="5"
            placeholder="输入文章话题或素材内容，AI将根据此内容生成文章"
          />
        </el-form-item>
        <el-form-item label="分类">
          <el-select v-model="createForm.category" style="width: 100%">
            <el-option label="科技" value="科技" />
            <el-option label="社会" value="社会" />
            <el-option label="娱乐" value="娱乐" />
            <el-option label="体育" value="体育" />
            <el-option label="时事热点" value="时事热点" />
            <el-option label="其他" value="其他" />
          </el-select>
        </el-form-item>
        <el-form-item label="去AI化">
          <el-switch v-model="createForm.auto_humanize" />
          <span style="margin-left: 10px; color: #909399">自动进行二次改写降低AI痕迹</span>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCreateDialog = false">取消</el-button>
        <el-button type="primary" :loading="creating" @click="createArticle">
          生成文章
        </el-button>
      </template>
    </el-dialog>

    <!-- 文章详情/编辑对话框 -->
    <el-dialog v-model="showDetailDialog" :title="isEditing ? '编辑文章' : '文章详情'" width="800px">
      <template v-if="currentArticle">
        <el-form v-if="isEditing" :model="editForm" label-width="80px">
          <el-form-item label="标题">
            <el-input v-model="editForm.title" />
          </el-form-item>
          <el-form-item label="内容">
            <el-input v-model="editForm.content" type="textarea" :rows="15" />
          </el-form-item>
        </el-form>
        <template v-else>
          <h3>{{ currentArticle.title }}</h3>
          <el-divider />
          <div class="article-content" v-html="formatContent(currentArticle.content)"></div>
          <el-divider />
          <el-descriptions :column="2" border>
            <el-descriptions-item label="状态">
              <el-tag :type="getStatusType(currentArticle.status)">
                {{ getStatusText(currentArticle.status) }}
              </el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="分类">{{ currentArticle.category }}</el-descriptions-item>
            <el-descriptions-item label="Token消耗">{{ currentArticle.token_usage }}</el-descriptions-item>
            <el-descriptions-item label="AI模型">{{ currentArticle.ai_model }}</el-descriptions-item>
            <el-descriptions-item label="创建时间">{{ formatDate(currentArticle.created_at) }}</el-descriptions-item>
            <el-descriptions-item label="发布时间">{{ currentArticle.published_at ? formatDate(currentArticle.published_at) : '-' }}</el-descriptions-item>
          </el-descriptions>
        </template>
      </template>
      <template #footer>
        <template v-if="isEditing">
          <el-button @click="isEditing = false">取消</el-button>
          <el-button type="primary" :loading="saving" @click="saveArticle">保存</el-button>
        </template>
        <template v-else>
          <el-button @click="showDetailDialog = false">关闭</el-button>
        </template>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { articleApi } from '@/api'
import dayjs from 'dayjs'
import {
  FileText,
  Plus,
  RefreshCw,
  MoreVertical,
  Tag,
  Coins,
  Clock,
} from 'lucide-vue-next'

const router = useRouter()
const loading = ref(false)
const creating = ref(false)
const saving = ref(false)
const articles = ref([])
const showCreateDialog = ref(false)
const showDetailDialog = ref(false)
const isEditing = ref(false)
const currentArticle = ref<any>(null)

const filters = reactive({
  status: '',
})

const pagination = reactive({
  page: 1,
  pageSize: 20,
  total: 0,
})

const createForm = reactive({
  topic: '',
  category: '其他',
  auto_humanize: false,
})

const editForm = reactive({
  title: '',
  content: '',
})

const loadArticles = async () => {
  loading.value = true
  try {
    const res: any = await articleApi.list({
      page: pagination.page,
      page_size: pagination.pageSize,
      status: filters.status || undefined,
    })
    articles.value = res.items || []
    pagination.total = res.total || 0
  } catch (e) {
    console.error(e)
  } finally {
    loading.value = false
  }
}

const createArticle = async () => {
  if (!createForm.topic.trim()) {
    ElMessage.warning('请输入话题或素材')
    return
  }

  creating.value = true
  try {
    await articleApi.create(createForm)
    ElMessage.success('文章生成成功')
    showCreateDialog.value = false
    createForm.topic = ''
    loadArticles()
  } catch (e) {
    console.error(e)
  } finally {
    creating.value = false
  }
}

const showDetail = (row: any) => {
  currentArticle.value = row
  isEditing.value = false
  showDetailDialog.value = true
}

const editArticle = (row: any) => {
  currentArticle.value = row
  editForm.title = row.title
  editForm.content = row.content
  isEditing.value = true
  showDetailDialog.value = true
}

const saveArticle = async () => {
  saving.value = true
  try {
    await articleApi.update(currentArticle.value.id, editForm)
    ElMessage.success('保存成功')
    isEditing.value = false
    showDetailDialog.value = false
    loadArticles()
  } catch (e) {
    console.error(e)
  } finally {
    saving.value = false
  }
}

const publishArticle = async (row: any) => {
  if (!row.account_id) {
    ElMessage.warning('请先在编辑中选择发布账号')
    return
  }
  await ElMessageBox.confirm('确定要发布这篇文章吗？', '确认发布')
  try {
    await articleApi.publish(row.id)
    ElMessage.success('已提交发布')
    loadArticles()
  } catch (e) {
    console.error(e)
  }
}

const regenerateArticle = async (row: any) => {
  await ElMessageBox.confirm('重新生成将覆盖当前内容，确定吗？', '确认重新生成', { type: 'warning' })
  try {
    await articleApi.regenerate(row.id)
    ElMessage.success('重新生成成功')
    loadArticles()
  } catch (e) {
    console.error(e)
  }
}

const deleteArticle = async (row: any) => {
  await ElMessageBox.confirm('确定要删除这篇文章吗？', '确认删除', { type: 'warning' })
  await articleApi.delete(row.id)
  ElMessage.success('删除成功')
  loadArticles()
}

const getStatusClass = (status: string) => {
  const map: Record<string, string> = {
    draft: 'bg-gray-100 text-gray-600',
    publishing: 'bg-blue-100 text-blue-600',
    published: 'bg-green-100 text-green-600',
    failed: 'bg-red-100 text-red-600',
  }
  return map[status] || 'bg-gray-100 text-gray-600'
}

const getStatusType = (status: string) => {
  const map: Record<string, string> = {
    draft: 'info',
    publishing: 'warning',
    published: 'success',
    failed: 'danger',
  }
  return map[status] || 'info'
}

const getStatusText = (status: string) => {
  const map: Record<string, string> = {
    draft: '草稿',
    publishing: '发布中',
    published: '已发布',
    failed: '发布失败',
  }
  return map[status] || status
}

const formatDate = (date: string) => dayjs(date).format('MM-DD HH:mm')

const formatContent = (content: string) => {
  return content?.replace(/\n/g, '<br>') || ''
}

watch(() => filters.status, () => {
  pagination.page = 1
  loadArticles()
})

onMounted(loadArticles)
</script>

<style scoped>
.articles-redesign {
  @apply animate-in;
}

.article-content {
  line-height: 1.8;
  color: #606266;
  max-height: 400px;
  overflow-y: auto;
}
</style>
