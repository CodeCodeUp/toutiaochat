# UI 重构设计指南 - Zen-iOS Hybrid 风格

> 版本: 1.0
> 日期: 2025-12-19
> 设计语言: Zen-iOS Hybrid - 极致的物理触感与光学模糊

---

## 目录

1. [设计系统核心原则](#设计系统核心原则)
2. [技术栈配置](#技术栈配置)
3. [设计Token体系](#设计token体系)
4. [组件重构方案](#组件重构方案)
5. [实施步骤](#实施步骤)

---

## 设计系统核心原则

### 1.1 视觉基调 (Visual Identity)

**色彩系统**:
- **全局底色**: `#F2F2F7` (iOS系统级灰) 或 `#F9F9FB` (冷灰调)
- **绝不使用纯白**: 所有"白色"组件实际为 `#FAFAFA` 或更深
- **对比策略**: 组件与容器必须有3%-10%的色阶差异

**深度系统**:
```
Level 0 (背景层): #F2F2F7
Level 1 (容器层): rgba(255,255,255,0.6) + backdrop-blur-[40px]
Level 2 (卡片层): rgba(255,255,255,0.8) + backdrop-blur-[60px]
Level 3 (弹窗层): rgba(255,255,255,0.95) + backdrop-blur-[80px]
```

### 1.2 材质与物理质感

**毛玻璃规范**:
- **标准容器**: `backdrop-blur-[40px]` + `bg-white/60`
- **重要卡片**: `backdrop-blur-[60px]` + `bg-white/80`
- **模态弹窗**: `backdrop-blur-[80px]` + `bg-white/95`

**双层描边**:
```css
/* 内描边 - 模拟玻璃切面光线 */
border: 1px solid rgba(255, 255, 255, 0.6);

/* 外描边 - 定义物理轮廓 */
box-shadow: 0 0 0 1px rgba(229, 231, 235, 0.4);
```

**阴影系统**:
```css
/* 悬浮组件 - 扩散柔和阴影 */
shadow-[0_24px_48px_-12px_rgba(0,0,0,0.08)]

/* 凹陷组件 (输入框) - 内阴影 */
shadow-inner + bg-gray-100/50
```

### 1.3 交互反馈

**物理回弹**:
- 所有可点击元素: `active:scale-[0.98]` 或 `active:scale-95`
- Hover状态: `hover:backdrop-blur-3xl` + `hover:border-white/80`

**圆角美学** (iOS连续曲率):
- 大容器: `rounded-[40px]` ~ `rounded-[50px]`
- 功能模块: `rounded-[28px]`
- 按钮/输入框: `rounded-xl` (16px)
- 小组件: `rounded-lg` (12px)

---

## 技术栈配置

### 2.1 安装 Tailwind CSS

```bash
cd frontend
npm install -D tailwindcss@latest postcss@latest autoprefixer@latest
npx tailwindcss init -p
```

### 2.2 Tailwind 配置文件

创建 `frontend/tailwind.config.js`:

```javascript
/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{vue,js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // 灰度系统 (iOS风格)
        'base': '#F2F2F7',      // 全局背景
        'cold-gray': '#F9F9FB',  // 冷灰调背景
        'glass-white': '#FAFAFA', // 组件白色
        'deep-black': '#1C1C1E',  // 深空黑 (主按钮)
        'graphite': '#3A3A3C',    // 石墨色 (次级文字)

        // 功能色
        primary: {
          DEFAULT: '#1C1C1E',
          light: '#3A3A3C',
        },
        secondary: {
          DEFAULT: '#FAFAFA',
          dark: '#E5E7EB',
        },
      },
      fontFamily: {
        sans: ['Inter', 'SF Pro Display', 'system-ui', 'sans-serif'],
      },
      fontSize: {
        'tag': ['10px', { lineHeight: '14px', letterSpacing: '0.08em' }], // 标签/次要信息
      },
      boxShadow: {
        // 悬浮阴影
        'float': '0 24px 48px -12px rgba(0, 0, 0, 0.08)',
        'float-lg': '0 32px 64px -16px rgba(0, 0, 0, 0.12)',

        // 内阴影 (凹陷效果)
        'inset-soft': 'inset 0 2px 4px rgba(0, 0, 0, 0.06)',

        // 玻璃边缘
        'glass': '0 0 0 1px rgba(229, 231, 235, 0.4)',
        'glass-inner': 'inset 0 0 0 1px rgba(255, 255, 255, 0.6)',
      },
      backdropBlur: {
        'xs': '2px',
        '3xl': '40px',
        '4xl': '60px',
        '5xl': '80px',
      },
      borderRadius: {
        'ios-lg': '28px',
        'ios-xl': '40px',
        'ios-2xl': '50px',
      },
      spacing: {
        'safe': '20px', // 安全距离
      },
      animation: {
        'press': 'press 0.15s ease-out',
      },
      keyframes: {
        press: {
          '0%, 100%': { transform: 'scale(1)' },
          '50%': { transform: 'scale(0.98)' },
        },
      },
    },
  },
  plugins: [],
}
```

### 2.3 CSS入口文件

创建 `frontend/src/style.css`:

```css
@tailwind base;
@tailwind components;
@tailwind utilities;

/* 全局样式 */
@layer base {
  * {
    @apply antialiased;
  }

  body {
    @apply bg-base text-graphite font-sans;
    font-feature-settings: 'cv11', 'ss01';
    -webkit-font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
  }

  /* 滚动条美化 */
  ::-webkit-scrollbar {
    @apply w-2 h-2;
  }

  ::-webkit-scrollbar-track {
    @apply bg-transparent;
  }

  ::-webkit-scrollbar-thumb {
    @apply bg-gray-300/50 rounded-full;
    transition: background 0.2s;
  }

  ::-webkit-scrollbar-thumb:hover {
    @apply bg-gray-400/60;
  }
}

/* 玻璃容器基础类 */
@layer components {
  .glass-container {
    @apply bg-white/60 backdrop-blur-3xl;
    @apply border border-white/60;
    @apply shadow-glass shadow-glass-inner;
    @apply rounded-ios-xl;
  }

  .glass-card {
    @apply bg-white/80 backdrop-blur-4xl;
    @apply border border-white/60;
    @apply shadow-float shadow-glass;
    @apply rounded-ios-lg;
    @apply transition-all duration-200;
  }

  .glass-card:hover {
    @apply shadow-float-lg backdrop-blur-5xl;
  }

  /* 深空黑按钮 */
  .btn-primary {
    @apply bg-deep-black text-white;
    @apply px-6 py-3 rounded-xl;
    @apply font-bold tracking-tight;
    @apply shadow-float;
    @apply transition-all duration-200;
    @apply active:scale-[0.98];
  }

  .btn-primary:hover {
    @apply shadow-float-lg;
  }

  /* 纯白次级按钮 */
  .btn-secondary {
    @apply bg-glass-white text-graphite;
    @apply px-6 py-3 rounded-xl;
    @apply font-semibold;
    @apply border border-gray-200/40;
    @apply shadow-float;
    @apply transition-all duration-200;
    @apply active:scale-[0.98];
  }

  .btn-secondary:hover {
    @apply border-white/60 backdrop-blur-3xl;
  }

  /* 输入框 (凹陷效果) */
  .input-inset {
    @apply bg-gray-100/50 text-graphite;
    @apply px-4 py-3 rounded-xl;
    @apply border border-gray-200/40;
    @apply shadow-inset-soft;
    @apply transition-all duration-200;
  }

  .input-inset:focus {
    @apply outline-none border-gray-300/60;
    @apply shadow-inset-soft;
  }

  /* 标签样式 (工业设计感) */
  .tag-label {
    @apply text-tag uppercase tracking-widest font-bold;
    @apply text-gray-500;
  }
}

/* 动画增强 */
@layer utilities {
  .animate-in {
    animation: fadeIn 0.3s ease-out;
  }

  @keyframes fadeIn {
    from {
      opacity: 0;
      transform: translateY(10px);
    }
    to {
      opacity: 1;
      transform: translateY(0);
    }
  }
}
```

### 2.4 更新主入口

修改 `frontend/src/main.ts`:

```typescript
import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import './style.css' // 新增：Tailwind CSS

import App from './App.vue'
import router from './router'

const app = createApp(App)

app.use(createPinia())
app.use(router)
app.use(ElementPlus)

app.mount('#app')
```

---

## 设计Token体系

### 3.1 间距系统

```
微小间距: 8px  (p-2, gap-2)
标准间距: 16px (p-4, gap-4)
舒适间距: 24px (p-6, gap-6) ← 推荐
宽松间距: 32px (p-8, gap-8)
呼吸间距: 40px (p-10, gap-10) ← 大模块
```

### 3.2 文字系统

```
特大标题: text-4xl font-extrabold tracking-tight (36px)
页面标题: text-2xl font-extrabold tracking-tight (24px)
区块标题: text-xl font-bold (20px)
正文内容: text-base font-normal (16px)
次要文字: text-sm text-gray-500 (14px)
标签/元信息: text-tag uppercase tracking-widest font-bold (10px)
```

### 3.3 图标规范

- 使用 `lucide-vue-next` (统一线条粗细)
- 标准尺寸: `w-5 h-5` (20px)
- 大图标: `w-6 h-6` (24px)
- 颜色: `text-gray-500` 或 `text-deep-black`

安装图标库:
```bash
npm install lucide-vue-next
```

---

## 组件重构方案

### 4.1 主布局 (App.vue)

**设计思路**:
- 侧边栏变为半透明玻璃材质悬浮条
- 顶部取消独立Header，融入主内容区
- 内容区背景采用渐变冷灰调

**重构代码**: 见下方 [App.vue 完整代码](#appvue-完整代码)

### 4.2 仪表盘 (Dashboard.vue)

**设计改进**:
- 统计卡片采用玻璃卡片样式
- 图标使用 Lucide 替代 Element Plus
- 移除粗暴的彩色背景，使用灰度+色彩点缀
- 增加悬浮动效

**重构代码**: 见下方 [Dashboard.vue 完整代码](#dashboardvue-完整代码)

### 4.3 文章管理页 (Articles.vue)

**设计改进**:
- 工具栏采用玻璃容器
- 表格背景半透明
- 按钮使用新设计系统
- 状态标签更加精致

**重构代码**: 见下方 [Articles.vue 完整代码](#articlesvue-完整代码)

### 4.4 工作流页面 (新增)

**设计特点**:
- 步骤条采用毛玻璃横条
- 聊天框采用 iOS Messages 风格
- 文档预览采用阴影深度区分层级

---

## App.vue 完整代码

```vue
<template>
  <el-config-provider :locale="zhCn">
    <div class="min-h-screen bg-gradient-to-br from-base via-cold-gray to-base">
      <!-- 侧边栏 - 玻璃悬浮条 -->
      <aside class="fixed left-safe top-safe bottom-safe w-[260px] z-50 animate-in">
        <nav class="glass-container h-full p-6 flex flex-col">
          <!-- Logo -->
          <div class="mb-10">
            <h1 class="text-2xl font-extrabold tracking-tight text-deep-black">
              头条智能
              <span class="block text-sm font-normal text-gray-500 mt-1 tracking-wide">
                AI发文系统
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
  Settings,
} from 'lucide-vue-next'

const route = useRoute()

const menuItems = [
  { path: '/dashboard', label: '仪表盘', icon: LayoutDashboard },
  { path: '/articles', label: '文章管理', icon: FileText },
  { path: '/prompts', label: '提示词管理', icon: MessageSquare },
  { path: '/accounts', label: '账号管理', icon: Users },
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
```

---

## Dashboard.vue 完整代码

```vue
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
        v-for="stat in stats"
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

        <div class="stat-value text-4xl font-extrabold tracking-tight text-deep-black mb-1">
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

      <div class="space-y-3">
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

const stats = reactive([
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
    stats[0].value = res.total || 0
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
```

---

## Articles.vue 完整代码

```vue
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

      <button class="btn-primary flex items-center gap-2" @click="showCreateDialog = true">
        <Plus :size="20" :stroke-width="2" />
        创建文章
      </button>
    </div>

    <!-- 文章列表 -->
    <div class="glass-container p-8">
      <div class="space-y-3">
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
                  <el-dropdown-item divided @click="deleteArticle(article)">删除</el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </div>
        </div>
      </div>

      <!-- 分页 -->
      <div class="mt-8 flex justify-center">
        <el-pagination
          v-model:current-page="pagination.page"
          v-model:page-size="pagination.pageSize"
          :total="pagination.total"
          layout="total, prev, pager, next"
          @current-change="loadArticles"
        />
      </div>
    </div>

    <!-- 创建对话框 (保持Element Plus组件) -->
    <el-dialog v-model="showCreateDialog" title="创建文章" width="600px">
      <!-- ... 原有表单内容 ... -->
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, watch } from 'vue'
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

// ... 原有逻辑保持不变 ...

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

const formatDate = (date: string) => dayjs(date).format('MM-DD HH:mm')
</script>
```

---

## 实施步骤

### Step 1: 安装依赖 (5分钟)

```bash
cd frontend
npm install -D tailwindcss@latest postcss@latest autoprefixer@latest
npm install lucide-vue-next
npx tailwindcss init -p
```

### Step 2: 配置Tailwind (10分钟)

1. 复制上方 `tailwind.config.js` 内容
2. 创建 `src/style.css` 并复制CSS内容
3. 修改 `src/main.ts` 引入样式

### Step 3: 重构主布局 (30分钟)

1. 替换 `App.vue` 内容
2. 测试路由跳转
3. 调整间距和动画

### Step 4: 重构页面组件 (每个页面30分钟)

按优先级重构:
1. Dashboard.vue (仪表盘)
2. Articles.vue (文章管理)
3. Prompts.vue (提示词管理)
4. Accounts.vue (账号管理)
5. Settings.vue (系统设置)
6. Tasks.vue (任务队列)

### Step 5: 适配Element Plus (20分钟)

Element Plus组件需要自定义样式覆盖:

```css
/* 在 style.css 添加 */
@layer components {
  /* 覆盖 el-dialog */
  .el-dialog {
    @apply glass-container shadow-float-lg !important;
  }

  /* 覆盖 el-table */
  .el-table {
    @apply bg-transparent !important;
  }

  .el-table tr {
    @apply bg-white/40 backdrop-blur-3xl !important;
  }
}
```

### Step 6: 测试与优化 (1小时)

- [ ] 测试所有页面路由
- [ ] 检查响应式布局
- [ ] 测试交互动效
- [ ] 优化性能 (backdrop-blur 可能影响性能)
- [ ] 浏览器兼容性测试

---

## 检查清单

### 视觉检查
- [ ] 全局背景色为冷灰调 (#F2F2F7)
- [ ] 所有卡片使用毛玻璃效果
- [ ] 双层描边清晰可见
- [ ] 阴影柔和且扩散
- [ ] 圆角符合iOS连续曲率

### 交互检查
- [ ] 所有按钮有 active:scale 反馈
- [ ] Hover 状态有模糊增强
- [ ] 页面切换动画流畅
- [ ] 表单输入有凹陷效果

### 性能检查
- [ ] backdrop-blur 不影响滚动流畅度
- [ ] 动画帧率稳定在 60fps
- [ ] 首屏加载时间 < 2秒

---

## 后续优化建议

1. **响应式适配**: 添加移动端适配 (当前为桌面优先)
2. **暗色模式**: 基于当前设计系统扩展暗色主题
3. **动效库集成**: 考虑集成 Framer Motion 或 GSAP
4. **性能优化**: 对低端设备降低 backdrop-blur 级别
5. **组件库扩展**: 创建统一的 UI 组件库

---

**文档版本**:
- v1.0 (2025-12-19): 初始设计系统
