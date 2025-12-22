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

// 工作流相关
export interface WorkflowCreateParams {
  mode: 'auto' | 'manual'
  content_type: 'article' | 'weitoutiao'
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

export default api
