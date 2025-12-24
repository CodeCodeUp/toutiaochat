<template>
  <el-config-provider :locale="zhCn">
    <div class="min-h-screen bg-gradient-to-br from-base via-cold-gray to-base">
      <!-- 侧边栏 - 玻璃悬浮条 -->
      <aside class="fixed left-safe top-safe bottom-safe w-[260px] z-50 animate-in">
        <nav class="glass-container h-full p-6 flex flex-col">
          <!-- Logo -->
          <div class="mb-10">
            <h1 class="text-2xl font-extrabold tracking-tight text-deep-black">
              智能
              <span class="block text-sm font-normal text-gray-500 mt-1 tracking-wide">
                系统
              </span>
            </h1>
          </div>

          <!-- 导航菜单 -->
          <div class="flex-1 space-y-2">
            <router-link
              v-for="item in menuItems"
              :key="item.path"
              :to="item.path"
              class="nav-item"
              :class="{ 'nav-item-active': isActive(item.path) }"
            >
              <component :is="item.icon" :size="20" :stroke-width="2" />
              <span>{{ item.label }}</span>
            </router-link>
          </div>

          <!-- 底部装饰 -->
          <div class="pt-6 border-t border-gray-200/30">
            <div class="tag-label">System Status</div>
            <div class="mt-2 flex items-center gap-2">
              <div class="w-2 h-2 rounded-full bg-green-500 animate-pulse"></div>
              <span class="text-sm text-gray-600">运行正常</span>
            </div>
          </div>
        </nav>
      </aside>

      <!-- 主内容区 -->
      <main class="ml-[280px] min-h-screen p-safe">
        <div class="max-w-[1400px] mx-auto py-8">
          <router-view v-slot="{ Component }">
            <transition name="page" mode="out-in">
              <component :is="Component" />
            </transition>
          </router-view>
        </div>
      </main>
    </div>
  </el-config-provider>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import zhCn from 'element-plus/dist/locale/zh-cn.mjs'
import {
  LayoutDashboard,
  FileText,
  MessageSquare,
  Users,
  ListTodo,
  Calendar,
  Settings,
} from 'lucide-vue-next'

const route = useRoute()

const menuItems = [
  { path: '/dashboard', label: '仪表盘', icon: LayoutDashboard },
  { path: '/articles', label: '文章管理', icon: FileText },
  { path: '/prompts', label: '提示词管理', icon: MessageSquare },
  { path: '/accounts', label: '账号管理', icon: Users },
  { path: '/scheduled-tasks', label: '定时任务', icon: Calendar },
  { path: '/tasks', label: '任务队列', icon: ListTodo },
  { path: '/settings', label: '系统设置', icon: Settings },
]

const isActive = (path: string) => route.path === path
</script>

<style scoped>
/* 导航项 */
.nav-item {
  @apply flex items-center gap-3 px-4 py-3 rounded-xl;
  @apply text-gray-600 font-medium;
  @apply transition-all duration-200;
  @apply active:scale-[0.98];
}

.nav-item:hover {
  @apply bg-white/40 text-deep-black;
}

.nav-item-active {
  @apply bg-deep-black text-white;
  @apply shadow-float;
}

/* 页面切换动画 */
.page-enter-active,
.page-leave-active {
  transition: all 0.3s ease;
}

.page-enter-from {
  opacity: 0;
  transform: translateY(20px);
}

.page-leave-to {
  opacity: 0;
  transform: translateY(-20px);
}
</style>
