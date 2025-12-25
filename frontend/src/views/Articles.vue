<template>
  <div class="articles-redesign max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
    <!-- 页面标题 -->
    <header class="mb-10 flex flex-col md:flex-row md:items-center md:justify-between gap-4">
      <div>
        <h1 class="text-4xl font-extrabold tracking-tight text-deep-black">
          文章管理
        </h1>
        <p class="mt-2 text-sm text-gray-500 font-medium">
          管理和发布您的内容创作库
        </p>
      </div>
      <button class="btn-primary flex items-center gap-2 shadow-lg shadow-deep-black/20" @click="router.push('/articles/workflow')">
        <Plus :size="20" :stroke-width="2" />
        <span class="hidden sm:inline">创建新文章</span>
        <span class="sm:hidden">新建</span>
      </button>
    </header>

    <!-- 工具栏 -->
    <div class="glass-container p-4 mb-8 flex flex-col sm:flex-row items-center justify-between gap-4">
      <div class="flex items-center gap-3 w-full sm:w-auto overflow-x-auto pb-2 sm:pb-0 hide-scrollbar">
        <div class="relative group">
          <select
            v-model="filters.status"
            class="appearance-none bg-gray-50/50 border border-gray-200 text-gray-700 py-2.5 pl-4 pr-10 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all font-medium text-sm w-32 cursor-pointer"
          >
            <option value="">所有状态</option>
            <option value="draft">草稿箱</option>
            <option value="publishing">发布中</option>
            <option value="published">已发布</option>
            <option value="failed">发布失败</option>
          </select>
          <ChevronDown :size="16" class="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 pointer-events-none group-hover:text-gray-600 transition-colors" />
        </div>

        <div class="relative group">
          <select
            v-model="filters.content_type"
            class="appearance-none bg-gray-50/50 border border-gray-200 text-gray-700 py-2.5 pl-4 pr-10 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all font-medium text-sm w-32 cursor-pointer"
          >
            <option value="">所有类型</option>
            <option value="article">长文章</option>
            <option value="weitoutiao">微头条</option>
          </select>
          <ChevronDown :size="16" class="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 pointer-events-none group-hover:text-gray-600 transition-colors" />
        </div>
      </div>

      <button class="btn-secondary flex items-center gap-2 text-sm w-full sm:w-auto justify-center" @click="loadArticles">
        <RefreshCw :size="16" :stroke-width="2" :class="{ 'animate-spin': loading }" />
        刷新列表
      </button>
    </div>

    <!-- 文章列表 -->
    <div class="space-y-4">
      <div v-if="loading && articles.length === 0" class="text-center py-20">
        <div class="animate-spin w-10 h-10 border-4 border-gray-100 border-t-deep-black rounded-full mx-auto"></div>
        <p class="mt-4 text-gray-400 font-medium">加载内容中...</p>
      </div>

      <div v-else-if="articles.length === 0" class="glass-container p-16 text-center border-dashed border-2 border-gray-200">
        <div class="w-20 h-20 bg-gray-50 rounded-full flex items-center justify-center mx-auto mb-6">
          <FileText :size="40" class="text-gray-300" />
        </div>
        <h3 class="text-lg font-bold text-gray-900 mb-2">暂无文章</h3>
        <p class="text-gray-500 max-w-sm mx-auto mb-8">
          这里空空如也。点击右上角按钮开始创作第一篇内容。
        </p>
      </div>

      <transition-group name="list" tag="div" class="space-y-4">
        <div
          v-for="article in articles"
          :key="article.id"
          class="glass-card p-5 flex items-start gap-5 group transition-all duration-300 hover:shadow-lg hover:border-blue-100/60 hover:-translate-y-0.5"
        >
          <!-- 文章图标 -->
          <div
            class="w-14 h-14 rounded-2xl flex items-center justify-center flex-shrink-0 shadow-inner relative overflow-hidden group-hover:shadow-md transition-all"
            :class="article.content_type === 'weitoutiao' ? 'bg-gradient-to-br from-orange-500 to-amber-600' : 'bg-gradient-to-br from-blue-500 to-indigo-600'"
          >
             <!-- 背景纹理 -->
            <div class="absolute inset-0 opacity-20 bg-[url('data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMjAiIGhlaWdodD0iMjAiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+PGNpcmNsZSBjeD0iMiIgY3k9IjIiIHI9IjIiIGZpbGw9IiNmZmYiLz48L3N2Zz4=')]"></div>
            
            <MessageCircle v-if="article.content_type === 'weitoutiao'" :size="26" :stroke-width="2" class="text-white relative z-10" />
            <FileText v-else :size="26" :stroke-width="2" class="text-white relative z-10" />
          </div>

          <!-- 文章信息 -->
          <div class="flex-1 min-w-0 py-0.5">
            <div class="flex items-center justify-between mb-2">
               <div class="flex items-center gap-3 min-w-0">
                  <h3 class="text-lg font-bold text-deep-black truncate group-hover:text-blue-600 transition cursor-pointer"
                      @click="showDetail(article)">
                    {{ article.title || '(无标题)' }}
                  </h3>
                   <span
                    class="px-2 py-0.5 rounded-md text-[10px] font-bold uppercase tracking-wider border flex-shrink-0"
                    :class="article.content_type === 'weitoutiao' ? 'bg-orange-50 text-orange-600 border-orange-100' : 'bg-blue-50 text-blue-600 border-blue-100'"
                  >
                    {{ article.content_type === 'weitoutiao' ? '微头条' : '文章' }}
                  </span>
               </div>
            </div>

            <div class="flex items-center flex-wrap gap-x-6 gap-y-2 text-sm text-gray-500">
               <div class="flex items-center gap-1.5" title="创建时间">
                <Clock :size="14" class="text-gray-400" />
                <span>{{ formatDate(article.created_at) }}</span>
              </div>
              
              <div class="flex items-center gap-1.5" title="Token消耗">
                <Coins :size="14" class="text-yellow-500" />
                <span class="font-mono">{{ article.token_usage }}</span>
              </div>

              <div v-if="article.ai_model" class="flex items-center gap-1.5" title="AI模型">
                <Bot :size="14" class="text-purple-500" />
                <span>{{ article.ai_model }}</span>
              </div>
            </div>
          </div>

          <!-- 状态和操作 -->
          <div class="flex flex-col items-end gap-3 flex-shrink-0 pl-4 border-l border-gray-100/50 my-auto">
            <span
              class="px-2.5 py-1 rounded-full text-xs font-bold inline-flex items-center gap-1.5"
              :class="getStatusClass(article.status)"
            >
              <span class="w-1.5 h-1.5 rounded-full bg-current"></span>
              {{ getStatusText(article.status) }}
            </span>

            <el-dropdown trigger="click" placement="bottom-end">
              <button class="w-8 h-8 rounded-lg hover:bg-gray-100 flex items-center justify-center transition text-gray-400 hover:text-gray-600">
                <MoreVertical :size="18" :stroke-width="2" />
              </button>
              <template #dropdown>
                <el-dropdown-menu class="!p-1.5 !rounded-xl !border-gray-100 !shadow-xl">
                  <el-dropdown-item @click="showDetail(article)" class="!rounded-lg !mb-0.5">
                     <div class="flex items-center gap-2 text-deep-black"><Eye :size="14" /> 查看详情</div>
                  </el-dropdown-item>
                  <el-dropdown-item v-if="article.status === 'draft'" @click="editArticle(article)" class="!rounded-lg !mb-0.5">
                     <div class="flex items-center gap-2 text-deep-black"><Edit :size="14" /> 编辑内容</div>
                  </el-dropdown-item>
                  <el-dropdown-item @click="downloadDocx(article)" class="!rounded-lg !mb-0.5">
                    <div class="flex items-center gap-2 text-deep-black"><Download :size="14" /> 导出 DOCX</div>
                  </el-dropdown-item>
                  <div class="h-px bg-gray-100 my-1 mx-2"></div>
                  <el-dropdown-item v-if="article.status === 'draft' || article.status === 'failed'" @click="publishArticle(article)" class="!rounded-lg !mb-0.5 !text-blue-600 hover:!bg-blue-50">
                    <div class="flex items-center gap-2"><Send :size="14" /> 发布文章</div>
                  </el-dropdown-item>
                  <el-dropdown-item divided @click="deleteArticle(article)" class="!rounded-lg !text-red-500 hover:!bg-red-50">
                     <div class="flex items-center gap-2"><Trash2 :size="14" /> 删除</div>
                  </el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </div>
        </div>
      </transition-group>

      <!-- 分页 -->
      <div v-if="articles.length > 0" class="mt-8 flex justify-center py-4">
        <el-pagination
          v-model:current-page="pagination.page"
          v-model:page-size="pagination.pageSize"
          :total="pagination.total"
          layout="prev, pager, next"
          @current-change="loadArticles"
          background
        />
      </div>
    </div>

    <!-- 文章详情/编辑对话框 -->
    <el-dialog 
      v-model="showDetailDialog" 
      :title="isEditing ? '编辑文章' : '文章详情'" 
      width="800px"
      class="custom-dialog"
      destroy-on-close
    >
      <template v-if="currentArticle">
        <div v-if="isEditing" class="px-2">
          <el-form :model="editForm" label-position="top">
            <el-form-item label="标题">
              <el-input v-model="editForm.title" size="large" />
            </el-form-item>
            <el-form-item label="正文内容">
              <el-input 
                v-model="editForm.content" 
                type="textarea" 
                :rows="15" 
                class="font-mono text-sm leading-relaxed"
                resize="none"
              />
            </el-form-item>
            <el-form-item label="默认发布账号">
              <el-select v-model="editForm.account_id" placeholder="选择账号 (可选)" clearable class="!w-full" size="large">
                <el-option
                  v-for="account in accounts"
                  :key="account.id"
                  :label="`${account.nickname || account.platform}`"
                  :value="account.id"
                >
                   <div class="flex items-center gap-2">
                     <span class="w-2 h-2 rounded-full" :class="account.platform === 'toutiao' ? 'bg-red-500' : 'bg-gray-400'"></span>
                     <span>{{ account.nickname || account.platform }}</span>
                   </div>
                </el-option>
              </el-select>
            </el-form-item>
          </el-form>
        </div>
        <div v-else class="article-preview px-2">
          <h3 class="text-2xl font-bold text-gray-900 mb-4 leading-tight">{{ currentArticle.title }}</h3>
          
          <div class="flex items-center gap-4 text-xs text-gray-400 mb-6 pb-4 border-b border-gray-100">
             <span class="flex items-center gap-1"><Clock :size="12"/> {{ formatDate(currentArticle.created_at) }}</span>
             <span class="flex items-center gap-1"><Bot :size="12"/> {{ currentArticle.ai_model || 'AI Assistant' }}</span>
             <span class="flex items-center gap-1"><Coins :size="12"/> {{ currentArticle.token_usage }} tokens</span>
          </div>

          <div class="article-content bg-gray-50/50 rounded-xl p-6 mb-6 font-serif text-lg leading-relaxed text-gray-700 whitespace-pre-line" v-html="currentArticle.content"></div>
          
          <div class="grid grid-cols-2 gap-4 bg-blue-50/30 rounded-xl p-4 border border-blue-50">
             <div>
               <div class="text-xs text-gray-400 mb-1">当前状态</div>
               <el-tag :type="getStatusType(currentArticle.status)" effect="dark" size="small" round>
                  {{ getStatusText(currentArticle.status) }}
               </el-tag>
             </div>
             <div>
               <div class="text-xs text-gray-400 mb-1">发布时间</div>
               <div class="text-sm font-medium text-gray-700">
                 {{ currentArticle.published_at ? formatDate(currentArticle.published_at) : '尚未发布' }}
               </div>
             </div>
          </div>
        </div>
      </template>
      <template #footer>
        <div class="flex items-center justify-end gap-3">
          <template v-if="isEditing">
            <el-button @click="isEditing = false" round>取消编辑</el-button>
            <el-button type="primary" :loading="saving" @click="saveArticle" round class="!px-6">保存修改</el-button>
          </template>
          <template v-else>
            <el-button @click="showDetailDialog = false" round>关闭</el-button>
            <el-button type="primary" @click="editArticle(currentArticle)" round plain v-if="currentArticle.status === 'draft'">
              <Edit :size="14" class="mr-2"/> 编辑
            </el-button>
          </template>
        </div>
      </template>
    </el-dialog>

    <!-- 发布账号选择对话框 -->
    <el-dialog 
      v-model="showPublishDialog" 
      title="选择发布账号" 
      width="480px"
      class="custom-dialog"
    >
      <div v-if="accounts.length === 0" class="text-center py-12">
        <div class="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-4 text-gray-400">
           <Users :size="24" />
        </div>
        <p class="mb-6 text-gray-600">暂无可用账号，请先添加。</p>
        <el-button type="primary" @click="router.push('/accounts')" round>前往添加账号</el-button>
      </div>
      <div v-else class="space-y-3 max-h-[400px] overflow-y-auto pr-2 custom-scrollbar">
        <div
          v-for="account in accounts"
          :key="account.id"
          class="p-4 rounded-xl border-2 cursor-pointer transition-all flex items-center justify-between group"
          :class="publishForm.account_id === account.id ? 'border-blue-500 bg-blue-50 ring-2 ring-blue-100' : 'border-gray-100 hover:border-gray-300 hover:bg-gray-50'"
          @click="publishForm.account_id = account.id"
        >
          <div class="flex items-center gap-3">
            <div class="w-10 h-10 rounded-full bg-gradient-to-br from-green-500 to-emerald-600 flex items-center justify-center text-white font-bold text-lg shadow-sm">
              {{ (account.nickname || account.platform).charAt(0) }}
            </div>
            <div>
              <div class="font-bold text-gray-900">{{ account.nickname || account.platform }}</div>
              <div class="text-xs text-gray-500 flex items-center gap-1">
                <span class="w-1.5 h-1.5 rounded-full bg-green-500"></span>
                {{ account.platform }}
              </div>
            </div>
          </div>
          <div v-if="publishForm.account_id === account.id" class="text-blue-500">
            <CheckCircle2 :size="20" fill="currentColor" class="text-white" />
          </div>
        </div>
      </div>
      <template #footer>
        <div class="flex justify-between items-center w-full">
           <div class="text-xs text-gray-400">
             将会发布到选定的平台
           </div>
           <div class="flex gap-3">
            <el-button @click="showPublishDialog = false" round>取消</el-button>
            <el-button type="primary" :disabled="!publishForm.account_id" :loading="publishing" @click="confirmPublish" round class="!px-6">
              确认发布
            </el-button>
           </div>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { articleApi, accountApi } from '@/api'
import dayjs from 'dayjs'
import {
  FileText,
  Plus,
  RefreshCw,
  MoreVertical,
  Coins,
  Clock,
  MessageCircle,
  Download,
  ChevronDown,
  Eye,
  Edit,
  Trash2,
  Send,
  Bot,
  Users,
  CheckCircle2
} from 'lucide-vue-next'

const router = useRouter()
const loading = ref(false)
const saving = ref(false)
const publishing = ref(false)
const articles = ref([])
const showDetailDialog = ref(false)
const showPublishDialog = ref(false)
const isEditing = ref(false)
const currentArticle = ref<any>(null)

const filters = reactive({
  status: '',
  content_type: '',
})

const pagination = reactive({
  page: 1,
  pageSize: 20,
  total: 0,
})

const editForm = reactive({
  title: '',
  content: '',
  account_id: '' as string | null,
})

const publishForm = reactive({
  article_id: '' as string,
  account_id: '' as string | null,
})

// 账号列表
const accounts = ref<any[]>([])

const loadAccounts = async () => {
  try {
    const res: any = await accountApi.list({ status: 'active' })
    accounts.value = res.items || []
  } catch (e) {
    console.error('加载账号列表失败', e)
  }
}

const loadArticles = async () => {
  loading.value = true
  try {
    const res: any = await articleApi.list({
      page: pagination.page,
      page_size: pagination.pageSize,
      status: filters.status || undefined,
      content_type: filters.content_type || undefined,
    })
    articles.value = res.items || []
    pagination.total = res.total || 0
  } catch (e) {
    console.error(e)
  } finally {
    loading.value = false
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
  editForm.account_id = row.account_id || null
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
  // 如果没有选择账号，弹出账号选择对话框
  if (!row.account_id) {
    publishForm.article_id = row.id
    publishForm.account_id = null
    showPublishDialog.value = true
    return
  }

  // 已有账号，直接确认发布
  await ElMessageBox.confirm('确定要发布这篇文章吗？', '确认发布')
  try {
    await articleApi.publish(row.id)
    ElMessage.success('已提交发布')
    loadArticles()
  } catch (e) {
    console.error(e)
  }
}

const confirmPublish = async () => {
  if (!publishForm.account_id) {
    ElMessage.warning('请选择发布账号')
    return
  }

  publishing.value = true
  try {
    // 先更新文章的账号
    await articleApi.update(publishForm.article_id, { account_id: publishForm.account_id })
    // 然后发布
    await articleApi.publish(publishForm.article_id)
    ElMessage.success('已提交发布')
    showPublishDialog.value = false
    loadArticles()
  } catch (e) {
    console.error(e)
  } finally {
    publishing.value = false
  }
}

const deleteArticle = async (row: any) => {
  await ElMessageBox.confirm('确定要删除这篇文章吗？', '确认删除', { type: 'warning' })
  await articleApi.delete(row.id)
  ElMessage.success('删除成功')
  loadArticles()
}

const downloadDocx = (article: any) => {
  // 直接打开下载链接
  const url = `/api/v1/articles/${article.id}/preview-docx`
  window.open(url, '_blank')
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

watch([() => filters.status, () => filters.content_type], () => {
  pagination.page = 1
  loadArticles()
})

onMounted(() => {
  loadArticles()
  loadAccounts()
})
</script>

<style scoped>
.articles-redesign {
  @apply animate-in;
}

.article-content {
  line-height: 1.8;
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
