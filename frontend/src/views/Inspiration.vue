<template>
  <div class="inspiration-page max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
    <!-- 页面标题 -->
    <header class="mb-10 flex flex-col md:flex-row md:items-center md:justify-between gap-4">
      <div>
        <h1 class="text-4xl font-extrabold tracking-tight text-deep-black">
          创作灵感
        </h1>
        <p class="mt-2 text-sm text-gray-500 font-medium">
          发现热门话题，激发创作灵感（每天 06:00 自动同步）
        </p>
      </div>
    </header>

    <!-- Tab 切换 -->
    <el-tabs v-model="activeTab" class="inspiration-tabs">
      <el-tab-pane label="热门话题" name="topics">
        <!-- 筛选栏 -->
        <div class="bg-white rounded-xl border border-gray-100 shadow-sm p-4 mb-6">
          <div class="flex flex-wrap items-center gap-4">
            <el-input
              v-model="searchKeyword"
              placeholder="搜索话题..."
              clearable
              style="width: 240px"
              @keyup.enter="loadTopics"
              @clear="loadTopics"
            >
              <template #prefix>
                <Search :size="16" class="text-gray-400" />
              </template>
            </el-input>

            <el-select v-model="sortBy" placeholder="排序" style="width: 140px" @change="loadTopics">
              <el-option label="最新同步" value="created_at" />
              <el-option label="使用次数" value="usage_count" />
              <el-option label="阅读数" value="read_count" />
              <el-option label="讨论数" value="talk_count" />
            </el-select>

            <div class="flex-1"></div>

            <!-- 实时获取按钮 -->
            <el-popover
              placement="bottom"
              :width="320"
              trigger="click"
              v-model:visible="showFetchPopover"
            >
              <template #reference>
                <el-button type="primary" :loading="fetching">
                  <RefreshCw :size="16" class="mr-1" />
                  获取新话题
                </el-button>
              </template>
              <div class="space-y-4">
                <div>
                  <div class="text-sm font-medium text-gray-700 mb-2">选择账号</div>
                  <el-select v-model="selectedAccountId" placeholder="选择账号" style="width: 100%">
                    <el-option
                      v-for="account in accounts"
                      :key="account.id"
                      :label="account.nickname || account.uid"
                      :value="account.id"
                    />
                  </el-select>
                </div>
                <div>
                  <div class="text-sm font-medium text-gray-700 mb-2">偏移量 (offset)</div>
                  <el-input-number v-model="fetchOffset" :min="0" :step="50" style="width: 100%" />
                </div>
                <div class="flex justify-end gap-2">
                  <el-button size="small" @click="showFetchPopover = false">取消</el-button>
                  <el-button
                    type="primary"
                    size="small"
                    :disabled="!selectedAccountId"
                    :loading="fetching"
                    @click="handleFetchTopics"
                  >
                    获取
                  </el-button>
                </div>
              </div>
            </el-popover>

            <span class="text-sm text-gray-400">
              共 {{ total }} 个话题
            </span>
          </div>
        </div>

        <!-- 话题表格 -->
        <div class="bg-white rounded-xl border border-gray-100 shadow-sm overflow-hidden">
          <el-table
            v-loading="loading"
            :data="topics"
            style="width: 100%"
            row-class-name="cursor-pointer hover:bg-blue-50/50"
            @row-click="useTopic"
          >
            <el-table-column label="话题" min-width="300">
              <template #default="{ row }">
                <div class="flex items-center gap-3 py-2">
                  <div
                    class="w-10 h-10 rounded-lg bg-gradient-to-br from-blue-50 to-purple-50 flex-shrink-0 overflow-hidden"
                  >
                    <img
                      v-if="row.avatar_url"
                      :src="row.avatar_url"
                      class="w-full h-full object-cover"
                      @error="(e: Event) => (e.target as HTMLImageElement).style.display = 'none'"
                    />
                  </div>
                  <span class="font-medium text-gray-900 line-clamp-2">{{ row.forum_name }}</span>
                </div>
              </template>
            </el-table-column>

            <el-table-column label="讨论" width="100" align="center">
              <template #default="{ row }">
                <span class="text-gray-500">{{ formatNumber(row.talk_count) }}</span>
              </template>
            </el-table-column>

            <el-table-column label="阅读" width="100" align="center">
              <template #default="{ row }">
                <span class="text-gray-500">{{ formatNumber(row.read_count) }}</span>
              </template>
            </el-table-column>

            <el-table-column label="已用" width="80" align="center">
              <template #default="{ row }">
                <el-tag v-if="row.usage_count > 0" size="small" type="info">
                  {{ row.usage_count }}次
                </el-tag>
                <span v-else class="text-gray-300">-</span>
              </template>
            </el-table-column>

            <el-table-column label="操作" width="150" align="center">
              <template #default="{ row }">
                <el-button type="primary" link @click.stop="useTopic(row)">
                  使用
                </el-button>
                <el-button type="info" link @click.stop="copyTopic(row)">
                  复制
                </el-button>
                <el-button type="danger" link @click.stop="deleteTopic(row)">
                  删除
                </el-button>
              </template>
            </el-table-column>
          </el-table>

          <!-- 空状态 -->
          <div v-if="!loading && topics.length === 0" class="text-center py-16">
            <Lightbulb :size="48" class="mx-auto mb-4 text-gray-300" />
            <h3 class="text-lg font-bold text-gray-900 mb-2">暂无话题</h3>
            <p class="text-gray-500">点击"获取新话题"从头条同步热门话题</p>
          </div>
        </div>

        <!-- 分页 -->
        <div v-if="total > pageSize" class="mt-6 flex justify-center">
          <el-pagination
            v-model:current-page="currentPage"
            :page-size="pageSize"
            :total="total"
            layout="prev, pager, next"
            @current-change="loadTopics"
          />
        </div>
      </el-tab-pane>

      <el-tab-pane label="素材文章" name="articles" disabled>
        <div class="text-center py-20 text-gray-400">
          即将上线，敬请期待...
        </div>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Search, Lightbulb, RefreshCw } from 'lucide-vue-next'
import { inspirationApi, accountApi, type InspirationTopic } from '@/api'

const router = useRouter()

// 状态
const activeTab = ref('topics')
const loading = ref(false)
const topics = ref<InspirationTopic[]>([])
const total = ref(0)
const currentPage = ref(1)
const pageSize = ref(20)
const searchKeyword = ref('')
const sortBy = ref('created_at')

// 实时获取相关状态
const showFetchPopover = ref(false)
const fetching = ref(false)
const accounts = ref<any[]>([])
const selectedAccountId = ref('')
const fetchOffset = ref(0)

// 加载话题列表
const loadTopics = async () => {
  loading.value = true
  try {
    const data = await inspirationApi.listTopics({
      page: currentPage.value,
      page_size: pageSize.value,
      keyword: searchKeyword.value || undefined,
      sort_by: sortBy.value as any,
      sort_order: 'desc',
    })
    topics.value = data.items
    total.value = data.total
  } catch (error) {
    console.error('加载话题失败:', error)
  } finally {
    loading.value = false
  }
}

// 加载账号列表
const loadAccounts = async () => {
  try {
    const data = await accountApi.list({ status: 'active' })
    accounts.value = data.items || []
    if (accounts.value.length > 0 && !selectedAccountId.value) {
      selectedAccountId.value = accounts.value[0].id
    }
  } catch (error) {
    console.error('加载账号失败:', error)
  }
}

// 实时获取话题
const handleFetchTopics = async () => {
  if (!selectedAccountId.value) {
    ElMessage.warning('请选择账号')
    return
  }

  fetching.value = true
  try {
    const result = await inspirationApi.fetchTopics(selectedAccountId.value, fetchOffset.value)
    ElMessage.success(result.message)
    // 更新下次偏移量
    fetchOffset.value = result.offset
    // 刷新列表
    await loadTopics()
    showFetchPopover.value = false
  } catch (error: any) {
    ElMessage.error(error.message || '获取话题失败')
  } finally {
    fetching.value = false
  }
}

// 使用话题
const useTopic = async (topic: InspirationTopic) => {
  try {
    await inspirationApi.useTopic(topic.id)
    router.push({
      path: '/articles/workflow',
      query: { topic: topic.forum_name }
    })
  } catch (error) {
    console.error('使用话题失败:', error)
  }
}

// 复制话题
const copyTopic = async (topic: InspirationTopic) => {
  try {
    await navigator.clipboard.writeText(topic.forum_name)
    ElMessage.success('已复制到剪贴板')
  } catch (error) {
    ElMessage.error('复制失败')
  }
}

// 删除话题
const deleteTopic = async (topic: InspirationTopic) => {
  try {
    await ElMessageBox.confirm(
      `确定删除话题「${topic.forum_name}」吗？删除后即使同步也不会再出现。`,
      '删除确认',
      {
        confirmButtonText: '删除',
        cancelButtonText: '取消',
        type: 'warning',
      }
    )
    await inspirationApi.deleteTopic(topic.id)
    ElMessage.success('话题已删除')
    await loadTopics()
  } catch (error: any) {
    if (error !== 'cancel') {
      ElMessage.error(error.message || '删除失败')
    }
  }
}

// 格式化数字
const formatNumber = (num: number): string => {
  if (num >= 100000000) {
    return (num / 100000000).toFixed(1) + '亿'
  } else if (num >= 10000) {
    return (num / 10000).toFixed(1) + '万'
  }
  return num.toString()
}

onMounted(() => {
  loadTopics()
  loadAccounts()
})
</script>

<style scoped>
.inspiration-page {
  @apply animate-in;
}

.inspiration-tabs :deep(.el-tabs__header) {
  @apply mb-6;
}

.inspiration-tabs :deep(.el-tabs__item) {
  @apply text-base font-medium;
}

.inspiration-tabs :deep(.el-table__row) {
  transition: background-color 0.2s;
}
</style>
