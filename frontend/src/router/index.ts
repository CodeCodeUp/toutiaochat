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
