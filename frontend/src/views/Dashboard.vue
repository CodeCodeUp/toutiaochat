<template>
  <div class="dashboard">
    <h2 class="page-title">仪表盘</h2>

    <!-- 统计卡片 -->
    <el-row :gutter="20" class="stat-cards">
      <el-col :span="6">
        <el-card shadow="hover">
          <div class="stat-item">
            <div class="stat-icon" style="background: #409EFF">
              <el-icon><Document /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ stats.totalArticles }}</div>
              <div class="stat-label">文章总数</div>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover">
          <div class="stat-item">
            <div class="stat-icon" style="background: #67C23A">
              <el-icon><CircleCheck /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ stats.publishedArticles }}</div>
              <div class="stat-label">已发布</div>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover">
          <div class="stat-item">
            <div class="stat-icon" style="background: #E6A23C">
              <el-icon><Clock /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ stats.pendingReview }}</div>
              <div class="stat-label">待审核</div>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover">
          <div class="stat-item">
            <div class="stat-icon" style="background: #909399">
              <el-icon><User /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ stats.activeAccounts }}</div>
              <div class="stat-label">活跃账号</div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 快捷操作 -->
    <el-card class="quick-actions">
      <template #header>
        <span>快捷操作</span>
      </template>
      <el-space>
        <el-button type="primary" @click="goToCreate">
          <el-icon><Plus /></el-icon>
          创建文章
        </el-button>
        <el-button @click="goToReview">
          <el-icon><View /></el-icon>
          审核文章
        </el-button>
        <el-button @click="goToAccounts">
          <el-icon><User /></el-icon>
          管理账号
        </el-button>
      </el-space>
    </el-card>

    <!-- 最近文章 -->
    <el-card class="recent-articles">
      <template #header>
        <span>最近文章</span>
      </template>
      <el-table :data="recentArticles" style="width: 100%">
        <el-table-column prop="title" label="标题" min-width="200" />
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.status)">
              {{ getStatusText(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="180">
          <template #default="{ row }">
            {{ formatDate(row.created_at) }}
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { articleApi } from '@/api'
import dayjs from 'dayjs'

const router = useRouter()

const stats = ref({
  totalArticles: 0,
  publishedArticles: 0,
  pendingReview: 0,
  activeAccounts: 0,
})

const recentArticles = ref([])

const loadData = async () => {
  try {
    const res: any = await articleApi.list({ page_size: 5 })
    recentArticles.value = res.items || []
    stats.value.totalArticles = res.total || 0
  } catch (e) {
    console.error(e)
  }
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

const formatDate = (date: string) => {
  return dayjs(date).format('YYYY-MM-DD HH:mm')
}

const goToCreate = () => router.push('/articles?action=create')
const goToReview = () => router.push('/articles?status=pending_review')
const goToAccounts = () => router.push('/accounts')

onMounted(loadData)
</script>

<style lang="scss" scoped>
.dashboard {
  .page-title {
    margin-bottom: 20px;
    font-size: 20px;
    color: #303133;
  }

  .stat-cards {
    margin-bottom: 20px;
  }

  .stat-item {
    display: flex;
    align-items: center;
    gap: 16px;

    .stat-icon {
      width: 60px;
      height: 60px;
      border-radius: 8px;
      display: flex;
      align-items: center;
      justify-content: center;
      color: #fff;
      font-size: 28px;
    }

    .stat-info {
      .stat-value {
        font-size: 28px;
        font-weight: bold;
        color: #303133;
      }

      .stat-label {
        font-size: 14px;
        color: #909399;
      }
    }
  }

  .quick-actions {
    margin-bottom: 20px;
  }

  .recent-articles {
    margin-bottom: 20px;
  }
}
</style>
