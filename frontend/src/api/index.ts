import axios from 'axios'
import { ElMessage } from 'element-plus'

const api = axios.create({
  baseURL: '/api/v1',
  timeout: 120000, // 2分钟，AI 生成需要较长时间
})

// 响应拦截器
api.interceptors.response.use(
  (response) => response.data,
  (error) => {
    const message = error.response?.data?.detail || '请求失败'
    ElMessage.error(message)
    return Promise.reject(error)
  }
)

// 文章相关
export const articleApi = {
  list: (params?: any) => api.get('/articles', { params }),
  get: (id: string) => api.get(`/articles/${id}`),
  create: (data: any) => api.post('/articles', data),
  update: (id: string, data: any) => api.put(`/articles/${id}`, data),
  delete: (id: string) => api.delete(`/articles/${id}`),
  publish: (id: string) => api.post(`/articles/${id}/publish`),
  regenerate: (id: string) => api.post(`/articles/${id}/regenerate`),
}

// 账号相关
export const accountApi = {
  list: (params?: any) => api.get('/accounts', { params }),
  get: (id: string) => api.get(`/accounts/${id}`),
  create: (data: any) => api.post('/accounts', data),
  update: (id: string, data: any) => api.put(`/accounts/${id}`, data),
  delete: (id: string) => api.delete(`/accounts/${id}`),
  checkStatus: (id: string) => api.get(`/accounts/${id}/status`),
  refresh: (id: string, cookies: string) => api.post(`/accounts/${id}/refresh`, null, { params: { cookies } }),
}

// 任务相关
export const taskApi = {
  list: (params?: any) => api.get('/tasks', { params }),
  get: (id: string) => api.get(`/tasks/${id}`),
  retry: (id: string) => api.post(`/tasks/${id}/retry`),
  cancel: (id: string) => api.delete(`/tasks/${id}`),
}

// 提示词相关
export const promptApi = {
  list: (params?: any) => api.get('/prompts', { params }),
  get: (id: string) => api.get(`/prompts/${id}`),
  create: (data: any) => api.post('/prompts', data),
  update: (id: string, data: any) => api.put(`/prompts/${id}`, data),
  delete: (id: string) => api.delete(`/prompts/${id}`),
  getActiveByType: (type: string) => api.get(`/prompts/active/${type}`),
}

// AI配置相关
export const aiConfigApi = {
  getAll: () => api.get('/ai-configs'),
  get: (type: string) => api.get(`/ai-configs/${type}`),
  update: (type: string, data: any) => api.put(`/ai-configs/${type}`, data),
}

// 工作流配置相关
export interface WorkflowConfigData {
  enable_custom_topic: boolean
  enable_optimize: boolean
  enable_image_gen: boolean
  enable_auto_publish: boolean
  custom_topic: string
}

export const workflowConfigApi = {
  getAll: () => api.get('/workflow-configs'),
  get: (contentType: 'article' | 'weitoutiao') => api.get(`/workflow-configs/${contentType}`),
  update: (contentType: 'article' | 'weitoutiao', data: Partial<WorkflowConfigData>) =>
    api.put(`/workflow-configs/${contentType}`, data),
}

// 工作流相关
export interface WorkflowCreateParams {
  mode: 'auto' | 'manual'
  content_type: 'article' | 'weitoutiao'
  custom_topic?: string  // 自定义话题（全自动模式）
}

export interface WorkflowMessageParams {
  message: string
  use_prompt_id?: string
}

export const workflowApi = {
  // 创建工作流会话
  createSession: (data: WorkflowCreateParams) =>
    api.post('/workflows/sessions', data),

  // 发送消息（半自动模式）
  sendMessage: (sessionId: string, data: WorkflowMessageParams) =>
    api.post(`/workflows/sessions/${sessionId}/messages`, data),

  // 进入下一阶段
  nextStage: (sessionId: string) =>
    api.post(`/workflows/sessions/${sessionId}/next-stage`),

  // 执行全自动流程
  executeAuto: (sessionId: string) =>
    api.post(`/workflows/sessions/${sessionId}/execute-auto`),

  // 查询会话状态
  getStatus: (sessionId: string) =>
    api.get(`/workflows/sessions/${sessionId}/status`),

  // 获取会话详情
  getDetail: (sessionId: string) =>
    api.get(`/workflows/sessions/${sessionId}`),

  // 获取对话历史
  getMessages: (sessionId: string, stage?: string, limit?: number) =>
    api.get(`/workflows/sessions/${sessionId}/messages`, {
      params: { stage, limit },
    }),
}

// 定时任务相关
export type ScheduledTaskType = 'GENERATE' | 'PUBLISH' | 'GENERATE_AND_PUBLISH'
export type ScheduleMode = 'CRON' | 'INTERVAL' | 'RANDOM_INTERVAL'
export type TopicMode = 'RANDOM' | 'FIXED' | 'LIST'
export type PublishMode = 'ALL' | 'ONE' | 'BATCH'
export type ContentType = 'ARTICLE' | 'WEITOUTIAO'

export interface ScheduledTaskCreate {
  name: string
  type: ScheduledTaskType
  content_type: ContentType
  schedule_mode: ScheduleMode
  schedule_config: {
    cron?: string
    minutes?: number
    min_minutes?: number
    max_minutes?: number
  }
  active_start_hour?: number
  active_end_hour?: number
  topic_mode?: TopicMode
  topics?: string[]
  account_id?: string
  publish_mode?: PublishMode
  publish_batch_size?: number
  publish_order?: 'oldest' | 'newest' | 'random'
  is_active?: boolean
}

export interface ScheduledTask extends ScheduledTaskCreate {
  id: string
  current_topic_index: number
  last_run_at: string | null
  next_run_at: string | null
  run_count: number
  last_error: string | null
  created_at: string
  updated_at: string
}

export interface SchedulerStatus {
  running: boolean
  active_tasks: number
  pending_jobs: number
}

export const scheduledTaskApi = {
  // 列表
  list: (params?: { type?: ScheduledTaskType; content_type?: ContentType; is_active?: boolean; skip?: number; limit?: number }) =>
    api.get('/scheduled-tasks', { params }),

  // 详情
  get: (id: string) => api.get(`/scheduled-tasks/${id}`),

  // 创建
  create: (data: ScheduledTaskCreate) => api.post('/scheduled-tasks', data),

  // 更新
  update: (id: string, data: Partial<ScheduledTaskCreate>) => api.put(`/scheduled-tasks/${id}`, data),

  // 删除
  delete: (id: string) => api.delete(`/scheduled-tasks/${id}`),

  // 启用/禁用
  toggle: (id: string) => api.post(`/scheduled-tasks/${id}/toggle`),

  // 立即执行
  trigger: (id: string) => api.post(`/scheduled-tasks/${id}/trigger`),

  // 执行日志
  logs: (id: string, params?: { skip?: number; limit?: number }) =>
    api.get(`/scheduled-tasks/${id}/logs`, { params }),
}

export const schedulerApi = {
  // 调度器状态
  status: () => api.get('/scheduler/status'),

  // 暂停所有
  pause: () => api.post('/scheduler/pause'),

  // 恢复所有
  resume: () => api.post('/scheduler/resume'),
}

export default api
