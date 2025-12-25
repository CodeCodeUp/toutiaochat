<template>
  <div class="dashboard-redesign max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
    <!-- 页面标题 -->
    <header class="mb-10 flex flex-col md:flex-row md:items-center md:justify-between gap-4">
      <div>
        <h1 class="text-4xl font-extrabold tracking-tight text-deep-black">
          仪表盘
        </h1>
        <p class="mt-2 text-sm text-gray-500 font-medium">
          实时监控系统运行状态和数据统计
        </p>
      </div>
      <div class="text-sm text-gray-400 font-mono">
        {{ new Date().toLocaleDateString() }}
      </div>
    </header>

    <!-- 统计卡片 -->
    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-10">
      <div
        v-for="stat in statsData"
        :key="stat.key"
        class="glass-card p-6 relative overflow-hidden group hover:scale-[1.02] transition-transform duration-300"
      >
        <div class="relative z-10">
          <div class="flex items-center justify-between mb-4">
            <div
              class="w-12 h-12 rounded-2xl flex items-center justify-center shadow-lg transition-transform group-hover:scale-110"
              :class="stat.iconBg"
            >
              <component :is="stat.icon" :size="24" :stroke-width="2" class="text-white" />
            </div>
            <div class="text-xs font-bold text-gray-400 uppercase tracking-wider">{{ stat.label }}</div>
          </div>

          <div class="text-4xl font-extrabold tracking-tight text-deep-black mb-1">
            {{ stat.value }}
          </div>

          <div class="text-sm text-gray-500 font-medium">
            {{ stat.description }}
          </div>
        </div>

        <!-- 装饰背景图标 -->
        <div 
          class="absolute -right-4 -bottom-4 opacity-5 transform rotate-12 group-hover:scale-110 transition-transform duration-500 pointer-events-none"
          :class="stat.iconColor || 'text-gray-900'"
        >
          <component :is="stat.icon" :size="100" />
        </div>
      </div>
    </div>

    <div class="grid grid-cols-1 lg:grid-cols-3 gap-8">
      <!-- 快捷操作 -->
      <section class="glass-container p-8 lg:col-span-1 h-fit">
        <div class="flex items-center gap-2 mb-6 text-gray-400 uppercase tracking-wider text-xs font-bold">
          <Zap :size="14" />
          <span>Quick Actions</span>
        </div>
        
        <div class="space-y-4">
          <button class="w-full btn-primary flex items-center justify-center gap-3 py-4 shadow-lg shadow-deep-black/20 group" @click="goToCreate">
            <Plus :size="20" :stroke-width="2.5" class="group-hover:rotate-90 transition-transform" />
            <span class="text-lg">创建新文章</span>
          </button>

          <button class="w-full btn-secondary flex items-center justify-center gap-3 py-4 group hover:border-blue-200 hover:bg-blue-50/50" @click="goToReview">
            <Eye :size="20" :stroke-width="2" class="text-blue-500" />
            <span>查看待发布</span>
          </button>

          <button class="w-full btn-secondary flex items-center justify-center gap-3 py-4 group hover:border-purple-200 hover:bg-purple-50/50" @click="goToAccounts">
            <Users :size="20" :stroke-width="2" class="text-purple-500" />
            <span>管理账号库</span>
          </button>
        </div>

        <div class="mt-8 pt-6 border-t border-gray-100">
           <div class="text-xs text-center text-gray-400">
             系统运行正常 · 版本 v1.2.0
           </div>
        </div>
      </section>

      <!-- 最近文章 -->
      <section class="bg-white/40 border border-white/60 rounded-ios-xl shadow-sm p-8 lg:col-span-2">
        <div class="flex items-center justify-between mb-6">
          <div class="flex items-center gap-2 text-gray-500 uppercase tracking-wider text-xs font-bold">
            <Clock :size="14" />
            <span>Recent Activity</span>
          </div>
          <button class="text-sm text-blue-600 font-medium hover:underline flex items-center gap-1" @click="router.push('/articles')">
            查看全部 <ChevronRight :size="14" />
          </button>
        </div>

        <div v-if="recentArticles.length === 0" class="text-center py-16 text-gray-400 border-2 border-dashed border-gray-200 rounded-2xl bg-white/50">
          <div class="w-16 h-16 bg-gray-50 rounded-full flex items-center justify-center mx-auto mb-4">
            <FileText :size="32" :stroke-width="1.5" class="text-gray-400" />
          </div>
          <p class="font-medium text-gray-900">暂无文章记录</p>
          <p class="text-xs mt-1 text-gray-500">开始创作你的第一篇内容</p>
        </div>

        <div v-else class="space-y-3">
          <div
            v-for="article in recentArticles"
            :key="article.id"
            class="bg-white rounded-xl border border-gray-200 shadow-sm p-4 flex items-center justify-between cursor-pointer group hover:border-blue-300 hover:shadow-md transition-all duration-200 relative z-0"
            @click="router.push('/articles')"
          >
            <div class="flex items-center gap-5 flex-1 min-w-0">
              <div 
                class="w-12 h-12 rounded-xl flex items-center justify-center flex-shrink-0 shadow-sm border border-gray-100"
                :class="article.content_type === 'weitoutiao' ? 'bg-orange-50 text-orange-600' : 'bg-blue-50 text-blue-600'"
              >
                <component :is="article.content_type === 'weitoutiao' ? MessageCircle : FileText" :size="22" :stroke-width="2" />
              </div>

              <div class="flex-1 min-w-0">
                <h3 
                  class="font-extrabold text-black truncate group-hover:text-blue-600 transition-colors text-base mb-1 relative z-10 opacity-100"
                  style="color: #000000; opacity: 1;"
                >
                  {{ article.title || '无标题草稿' }}
                </h3>
                <div class="flex items-center gap-3 text-xs text-gray-500 font-medium">
                  <span class="flex items-center gap-1 bg-gray-100 px-2 py-0.5 rounded text-gray-600">
                    {{ formatDate(article.created_at) }}
                  </span>
                  <span v-if="article.ai_model" class="flex items-center gap-1">
                    <Bot :size="12" /> {{ article.ai_model }}
                  </span>
                </div>
              </div>
            </div>

            <div class="flex items-center gap-4 pl-4 border-l border-gray-100">
              <span
                class="px-3 py-1 rounded-full text-xs font-bold flex items-center gap-1.5 shadow-sm border border-opacity-10"
                :class="getStatusClass(article.status)"
              >
                <span class="w-1.5 h-1.5 rounded-full bg-current"></span>
                {{ getStatusText(article.status) }}
              </span>

              <div class="w-8 h-8 rounded-full bg-gray-50 flex items-center justify-center text-gray-400 group-hover:bg-blue-50 group-hover:text-blue-500 transition-colors">
                <ChevronRight :size="16" :stroke-width="2" />
              </div>
            </div>
          </div>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { dashboardApi, articleApi } from '@/api'
import dayjs from 'dayjs'
import {
  FileText,
  CheckCircle2,
  Clock,
  Users,
  Plus,
  Eye,
  ChevronRight,
  Zap,
  MessageCircle,
  Bot
} from 'lucide-vue-next'

const router = useRouter()

const statsData = reactive([
  {
    key: 'total',
    label: 'Total Articles',
    value: 0,
    description: '文章总数',
    icon: FileText,
    iconBg: 'bg-gradient-to-br from-blue-500 to-blue-600',
    iconColor: 'text-blue-500'
  },
  {
    key: 'published',
    label: 'Published',
    value: 0,
    description: '已发布',
    icon: CheckCircle2,
    iconBg: 'bg-gradient-to-br from-green-500 to-emerald-600',
    iconColor: 'text-green-500'
  },
  {
    key: 'pending',
    label: 'Pending Publish',
    value: 0,
    description: '待发布',
    icon: Clock,
    iconBg: 'bg-gradient-to-br from-orange-400 to-orange-600',
    iconColor: 'text-orange-500'
  },
  {
    key: 'accounts',
    label: 'All Accounts',
    value: 0,
    description: '账号统计',
    icon: Users,
    iconBg: 'bg-gradient-to-br from-purple-500 to-purple-600',
    iconColor: 'text-purple-500'
  },
])

const recentArticles = ref<any[]>([])

const loadData = async () => {
  try {
    // 加载统计数据
    const stats: any = await dashboardApi.getStats()
    statsData[0].value = stats.total_articles || 0
    statsData[1].value = stats.published_count || 0
    statsData[2].value = stats.draft_count || 0
    statsData[3].value = stats.account_count || 0

    // 加载最近文章
    const res: any = await articleApi.list({ page_size: 5 })
    recentArticles.value = res.items || []
  } catch (e) {
    console.error(e)
  }
}

const getStatusClass = (status: string) => {
  const map: Record<string, string> = {
    draft: 'bg-gray-100 text-gray-600',
    publishing: 'bg-blue-50 text-blue-600',
    published: 'bg-green-50 text-green-600',
    failed: 'bg-red-50 text-red-600',
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

const formatDate = (date: string) => dayjs(date).format('MM-DD HH:mm')

const goToCreate = () => router.push('/articles/workflow')
const goToReview = () => router.push('/articles?status=draft')
const goToAccounts = () => router.push('/accounts')

onMounted(loadData)
</script>

<style scoped>
.dashboard-redesign {
  @apply animate-in;
}
</style>
