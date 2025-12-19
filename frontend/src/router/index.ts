import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      redirect: '/dashboard',
    },
    {
      path: '/dashboard',
      name: 'Dashboard',
      component: () => import('@/views/Dashboard.vue'),
      meta: { title: '仪表盘' },
    },
    {
      path: '/articles',
      name: 'Articles',
      component: () => import('@/views/Articles.vue'),
      meta: { title: '文章管理' },
    },
    {
      path: '/articles/workflow',
      name: 'ArticleWorkflow',
      component: () => import('@/views/ArticleWorkflow.vue'),
      meta: { title: '创建文章' },
    },
    {
      path: '/prompts',
      name: 'Prompts',
      component: () => import('@/views/Prompts.vue'),
      meta: { title: '提示词管理' },
    },
    {
      path: '/accounts',
      name: 'Accounts',
      component: () => import('@/views/Accounts.vue'),
      meta: { title: '账号管理' },
    },
    {
      path: '/tasks',
      name: 'Tasks',
      component: () => import('@/views/Tasks.vue'),
      meta: { title: '任务队列' },
    },
    {
      path: '/settings',
      name: 'Settings',
      component: () => import('@/views/Settings.vue'),
      meta: { title: '系统设置' },
    },
  ],
})

export default router
