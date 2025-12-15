<template>
  <div class="articles-page">
    <h2 class="page-title">文章管理</h2>

    <!-- 工具栏 -->
    <el-card class="toolbar">
      <el-row :gutter="20" align="middle">
        <el-col :span="16">
          <el-space>
            <el-select v-model="filters.status" placeholder="状态筛选" clearable style="width: 140px">
              <el-option label="草稿" value="draft" />
              <el-option label="待审核" value="pending_review" />
              <el-option label="已通过" value="approved" />
              <el-option label="已拒绝" value="rejected" />
              <el-option label="已发布" value="published" />
            </el-select>
            <el-button @click="loadArticles">
              <el-icon><Refresh /></el-icon>
              刷新
            </el-button>
          </el-space>
        </el-col>
        <el-col :span="8" style="text-align: right">
          <el-button type="primary" @click="showCreateDialog = true">
            <el-icon><Plus /></el-icon>
            创建文章
          </el-button>
        </el-col>
      </el-row>
    </el-card>

    <!-- 文章列表 -->
    <el-card>
      <el-table :data="articles" v-loading="loading" style="width: 100%">
        <el-table-column prop="title" label="标题" min-width="250">
          <template #default="{ row }">
            <el-link type="primary" @click="showDetail(row)">{{ row.title }}</el-link>
          </template>
        </el-table-column>
        <el-table-column prop="category" label="分类" width="100" />
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.status)">
              {{ getStatusText(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="token_usage" label="Token" width="80" />
        <el-table-column prop="created_at" label="创建时间" width="160">
          <template #default="{ row }">
            {{ formatDate(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="280" fixed="right">
          <template #default="{ row }">
            <el-space>
              <el-button size="small" @click="showDetail(row)">查看</el-button>
              <el-button
                v-if="row.status === 'draft' || row.status === 'rejected'"
                size="small"
                type="warning"
                @click="submitReview(row)"
              >
                提交审核
              </el-button>
              <el-button
                v-if="row.status === 'pending_review'"
                size="small"
                type="success"
                @click="reviewArticle(row, true)"
              >
                通过
              </el-button>
              <el-button
                v-if="row.status === 'pending_review'"
                size="small"
                type="danger"
                @click="reviewArticle(row, false)"
              >
                拒绝
              </el-button>
              <el-button
                v-if="row.status === 'approved'"
                size="small"
                type="primary"
                @click="publishArticle(row)"
              >
                发布
              </el-button>
              <el-button size="small" type="danger" @click="deleteArticle(row)">删除</el-button>
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
        @current-change="loadArticles"
      />
    </el-card>

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

    <!-- 文章详情对话框 -->
    <el-dialog v-model="showDetailDialog" title="文章详情" width="800px">
      <template v-if="currentArticle">
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
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { articleApi } from '@/api'
import dayjs from 'dayjs'

const loading = ref(false)
const creating = ref(false)
const articles = ref([])
const showCreateDialog = ref(false)
const showDetailDialog = ref(false)
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
  showDetailDialog.value = true
}

const submitReview = async (row: any) => {
  try {
    await articleApi.update(row.id, { status: 'pending_review' })
    ElMessage.success('已提交审核')
    loadArticles()
  } catch (e) {
    console.error(e)
  }
}

const reviewArticle = async (row: any, approved: boolean) => {
  if (!approved) {
    const { value } = await ElMessageBox.prompt('请输入拒绝原因', '拒绝文章', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
    })
    await articleApi.review(row.id, { approved: false, reject_reason: value })
  } else {
    await articleApi.review(row.id, { approved: true })
  }
  ElMessage.success(approved ? '已通过' : '已拒绝')
  loadArticles()
}

const publishArticle = async (row: any) => {
  await ElMessageBox.confirm('确定要发布这篇文章吗？', '确认发布')
  // TODO: 调用发布接口
  ElMessage.info('发布功能开发中')
}

const deleteArticle = async (row: any) => {
  await ElMessageBox.confirm('确定要删除这篇文章吗？', '确认删除', { type: 'warning' })
  await articleApi.delete(row.id)
  ElMessage.success('删除成功')
  loadArticles()
}

const getStatusType = (status: string) => {
  const map: Record<string, string> = {
    draft: 'info',
    pending_review: 'warning',
    approved: 'success',
    rejected: 'danger',
    published: 'success',
    failed: 'danger',
  }
  return map[status] || 'info'
}

const getStatusText = (status: string) => {
  const map: Record<string, string> = {
    draft: '草稿',
    pending_review: '待审核',
    approved: '已通过',
    rejected: '已拒绝',
    published: '已发布',
    failed: '发布失败',
  }
  return map[status] || status
}

const formatDate = (date: string) => dayjs(date).format('YYYY-MM-DD HH:mm')

const formatContent = (content: string) => {
  return content?.replace(/\n/g, '<br>') || ''
}

watch(() => filters.status, () => {
  pagination.page = 1
  loadArticles()
})

onMounted(loadArticles)
</script>

<style lang="scss" scoped>
.articles-page {
  .page-title {
    margin-bottom: 20px;
    font-size: 20px;
    color: #303133;
  }

  .toolbar {
    margin-bottom: 20px;
  }

  .article-content {
    line-height: 1.8;
    color: #606266;
    max-height: 400px;
    overflow-y: auto;
  }
}
</style>
