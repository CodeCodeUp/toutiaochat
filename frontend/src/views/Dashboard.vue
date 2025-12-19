<template>
  <div class="dashboard-redesign">
    <!-- 页面标题 -->
    <header class="mb-10">
      <h1 class="text-4xl font-extrabold tracking-tight text-deep-black">
        仪表盘
      </h1>
      <p class="mt-2 text-sm text-gray-500">
        实时监控系统运行状态和数据统计
      </p>
    </header>

    <!-- 统计卡片 -->
    <div class="grid grid-cols-4 gap-6 mb-10">
      <div
        v-for="stat in statsData"
        :key="stat.key"
        class="glass-card p-6 group cursor-pointer"
      >
        <div class="flex items-start justify-between mb-4">
          <div
            class="w-12 h-12 rounded-2xl flex items-center justify-center transition-transform group-hover:scale-110"
            :class="stat.iconBg"
          >
            <component :is="stat.icon" :size="24" :stroke-width="2" class="text-white" />
          </div>
          <div class="tag-label">{{ stat.label }}</div>
        </div>

        <div class="text-4xl font-extrabold tracking-tight text-deep-black mb-1">
          {{ stat.value }}
        </div>

        <div class="text-sm text-gray-500">
          {{ stat.description }}
        </div>
      </div>
    </div>

    <!-- 快捷操作 -->
    <section class="glass-container p-8 mb-10">
      <div class="tag-label mb-4">Quick Actions</div>
      <h2 class="text-xl font-bold text-deep-black mb-6">快捷操作</h2>

      <div class="flex gap-4">
        <button class="btn-primary flex items-center gap-2" @click="goToCreate">
          <Plus :size="20" :stroke-width="2" />
          创建文章
        </button>

        <button class="btn-secondary flex items-center gap-2" @click="goToReview">
          <Eye :size="20" :stroke-width="2" />
          审核文章
        </button>

        <button class="btn-secondary flex items-center gap-2" @click="goToAccounts">
          <Users :size="20" :stroke-width="2" />
          管理账号
        </button>
      </div>
    </section>

    <!-- 最近文章 -->
    <section class="glass-container p-8">
      <div class="tag-label mb-4">Recent Articles</div>
      <h2 class="text-xl font-bold text-deep-black mb-6">最近文章</h2>

      <div v-if="recentArticles.length === 0" class="text-center py-12 text-gray-400">
        <FileText :size="48" :stroke-width="1.5" class="mx-auto mb-3 opacity-50" />
        <p>暂无文章</p>
      </div>

      <div v-else class="space-y-3">
        <div
          v-for="article in recentArticles"
          :key="article.id"
          class="glass-card p-5 flex items-center justify-between cursor-pointer group"
        >
          <div class="flex items-center gap-4 flex-1">
            <div class="w-10 h-10 rounded-xl bg-gray-100/50 flex items-center justify-center">
              <FileText :size="20" :stroke-width="2" class="text-gray-500" />
            </div>

            <div class="flex-1 min-w-0">
              <h3 class="font-semibold text-deep-black truncate group-hover:text-blue-600 transition">
                {{ article.title }}
              </h3>
              <p class="text-sm text-gray-500 mt-1">
                {{ formatDate(article.created_at) }}
              </p>
            </div>
          </div>

          <div class="flex items-center gap-4">
            <span
              class="px-3 py-1 rounded-lg text-xs font-bold uppercase tracking-wider"
              :class="getStatusClass(article.status)"
            >
              {{ getStatusText(article.status) }}
            </span>

            <ChevronRight :size="20" :stroke-width="2" class="text-gray-400 group-hover:text-deep-black transition" />
          </div>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { articleApi } from '@/api'
import dayjs from 'dayjs'
import {
  FileText,
  CheckCircle2,
  Clock,
  Users,
  Plus,
  Eye,
  ChevronRight,
} from 'lucide-vue-next'

const router = useRouter()

const statsData = reactive([
  {
    key: 'total',
    label: 'Total',
    value: 0,
    description: '文章总数',
    icon: FileText,
    iconBg: 'bg-blue-500',
  },
  {
    key: 'published',
    label: 'Published',
    value: 0,
    description: '已发布',
    icon: CheckCircle2,
    iconBg: 'bg-green-500',
  },
  {
    key: 'pending',
    label: 'Pending',
    value: 0,
    description: '待审核',
    icon: Clock,
    iconBg: 'bg-orange-500',
  },
  {
    key: 'accounts',
    label: 'Accounts',
    value: 0,
    description: '活跃账号',
    icon: Users,
    iconBg: 'bg-gray-500',
  },
])

const recentArticles = ref<any[]>([])

const loadData = async () => {
  try {
    const res: any = await articleApi.list({ page_size: 5 })
    recentArticles.value = res.items || []
    statsData[0].value = res.total || 0
  } catch (e) {
    console.error(e)
  }
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

const getStatusText = (status: string) => {
  const map: Record<string, string> = {
    draft: '草稿',
    publishing: '发布中',
    published: '已发布',
    failed: '失败',
  }
  return map[status] || status
}

const formatDate = (date: string) => dayjs(date).format('YYYY-MM-DD HH:mm')

const goToCreate = () => router.push('/articles?action=create')
const goToReview = () => router.push('/articles?status=pending_review')
const goToAccounts = () => router.push('/accounts')

onMounted(loadData)
</script>

<style scoped>
.dashboard-redesign {
  @apply animate-in;
}
</style>
