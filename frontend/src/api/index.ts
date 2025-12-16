import axios from 'axios'
import { ElMessage } from 'element-plus'

const api = axios.create({
  baseURL: '/api/v1',
  timeout: 30000,
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

export default api
