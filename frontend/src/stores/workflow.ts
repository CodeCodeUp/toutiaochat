/**
 * 工作流状态管理
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { workflowApi, type WorkflowCreateParams } from '@/api'

// 工作流阶段
export type WorkflowStage = 'generate' | 'optimize' | 'image' | 'edit' | 'completed'

// 工作流状态
export type WorkflowStatus = 'idle' | 'processing' | 'completed' | 'failed'

// 内容类型
export type ContentType = 'article' | 'weitoutiao'

// 消息类型
export interface Message {
  id: string
  role: 'user' | 'assistant' | 'system'
  content: string
  stage: string
  created_at: string
  extra_data?: Record<string, any>
}

// 图片提示词
export interface ImagePrompt {
  description: string
  position: string
}

// 已生成图片
export interface GeneratedImage {
  url: string
  path: string
  position: string
  prompt?: string
  index: number
}

// 文章预览
export interface ArticlePreview {
  title: string
  content: string
  full_content?: string
  image_prompts?: ImagePrompt[]
  images?: GeneratedImage[]
}

export const useWorkflowStore = defineStore('workflow', () => {
  // 状态
  const sessionId = ref<string | null>(null)
  const articleId = ref<string | null>(null)
  const mode = ref<'auto' | 'manual'>('manual')
  const contentType = ref<ContentType>('article')
  const currentStage = ref<WorkflowStage>('generate')
  const messages = ref<Message[]>([])
  const articlePreview = ref<ArticlePreview | null>(null)
  const suggestions = ref<string[]>([])
  const progress = ref(0)
  const status = ref<WorkflowStatus>('idle')
  const error = ref<string | null>(null)
  const loading = ref(false)

  // 轮询定时器
  let pollTimer: ReturnType<typeof setInterval> | null = null

  // 计算属性
  const isAutoMode = computed(() => mode.value === 'auto')
  const isWeitoutiao = computed(() => contentType.value === 'weitoutiao')
  const isCompleted = computed(() => currentStage.value === 'completed')
  const isSessionActive = computed(() => sessionId.value !== null)  // 用于判断是否在创建状态
  const canProceed = computed(() => {
    return articlePreview.value?.title && articlePreview.value?.content
  })

  // 阶段显示名称
  const stageLabels: Record<WorkflowStage, string> = {
    generate: '生成文章',
    optimize: '优化润色',
    image: '配图生成',
    edit: '编辑预览',
    completed: '完成',
  }

  const currentStageLabel = computed(() => stageLabels[currentStage.value])

  // 创建工作流会话
  async function createSession(params: WorkflowCreateParams) {
    loading.value = true
    error.value = null

    try {
      const result: any = await workflowApi.createSession(params)
      sessionId.value = result.session_id
      articleId.value = result.article_id
      mode.value = params.mode
      contentType.value = params.content_type
      currentStage.value = result.stage as WorkflowStage
      status.value = 'processing'
      messages.value = []
      articlePreview.value = null
      suggestions.value = []
      progress.value = 0

      return result
    } catch (e: any) {
      error.value = e.message || '创建会话失败'
      throw e
    } finally {
      loading.value = false
    }
  }

  // 发送消息
  async function sendMessage(message: string, promptId?: string) {
    if (!sessionId.value) {
      throw new Error('会话未创建')
    }

    loading.value = true
    error.value = null

    // 先添加用户消息，确保用户能看到自己发送的内容
    const userMsgId = `user-${Date.now()}`
    messages.value.push({
      id: userMsgId,
      role: 'user',
      content: message,
      stage: currentStage.value,
      created_at: new Date().toISOString(),
    })

    try {
      const result: any = await workflowApi.sendMessage(sessionId.value, {
        message,
        use_prompt_id: promptId,
      })

      // 添加助手回复
      messages.value.push({
        id: `assistant-${Date.now()}`,
        role: 'assistant',
        content: result.assistant_reply,
        stage: currentStage.value,
        created_at: new Date().toISOString(),
      })

      // 更新文章预览
      if (result.article_preview) {
        articlePreview.value = result.article_preview
      }

      // 更新建议
      if (result.suggestions) {
        suggestions.value = result.suggestions
      }

      return result
    } catch (e: any) {
      // 添加错误消息
      const errMsg = e.response?.data?.detail || e.message || '发送消息失败'
      error.value = errMsg

      // 检查是否是超时错误
      const isTimeout = e.code === 'ECONNABORTED' || errMsg.includes('timeout')
      if (isTimeout && sessionId.value) {
        // 超时时尝试加载会话状态（后端可能已处理成功）
        messages.value.push({
          id: `error-${Date.now()}`,
          role: 'assistant',
          content: `⏱️ 请求超时，正在检查处理结果...`,
          stage: currentStage.value,
          created_at: new Date().toISOString(),
          extra_data: { is_error: true },
        })
        // 尝试加载会话详情
        try {
          await loadSessionDetail()
          if (articlePreview.value?.title) {
            // 移除超时消息，添加成功消息
            messages.value.pop()
            messages.value.push({
              id: `recovered-${Date.now()}`,
              role: 'assistant',
              content: `✅ 文章已生成《${articlePreview.value.title}》`,
              stage: currentStage.value,
              created_at: new Date().toISOString(),
            })
            error.value = null
            return // 不抛出错误
          }
        } catch (loadErr) {
          console.error('加载会话状态失败', loadErr)
        }
      } else {
        messages.value.push({
          id: `error-${Date.now()}`,
          role: 'assistant',
          content: `❌ 处理失败：${errMsg}`,
          stage: currentStage.value,
          created_at: new Date().toISOString(),
          extra_data: { is_error: true },
        })
      }
      throw e
    } finally {
      loading.value = false
    }
  }

  // 进入下一阶段
  async function nextStage() {
    if (!sessionId.value) {
      throw new Error('会话未创建')
    }

    loading.value = true
    error.value = null

    try {
      const result: any = await workflowApi.nextStage(sessionId.value)
      currentStage.value = result.current_stage as WorkflowStage

      // 清空建议
      suggestions.value = []

      // 如果后端返回了初始提示，显示它
      if (result.initial_reply) {
        messages.value.push({
          id: `assistant-${Date.now()}`,
          role: 'assistant',
          content: result.initial_reply,
          stage: result.current_stage,
          created_at: new Date().toISOString(),
        })

        // 更新文章预览和建议
        if (result.article_preview) {
          articlePreview.value = result.article_preview
        }
        if (result.suggestions) {
          suggestions.value = result.suggestions
        }
      }

      return result
    } catch (e: any) {
      error.value = e.message || '切换阶段失败'
      throw e
    } finally {
      loading.value = false
    }
  }

  // 执行全自动流程
  async function executeAuto() {
    if (!sessionId.value) {
      throw new Error('会话未创建')
    }

    loading.value = true
    error.value = null
    status.value = 'processing'

    // 先开始轮询状态（这样可以实时看到进度）
    startPolling()

    // 然后发起后台任务（不等待返回，让轮询来跟踪进度）
    workflowApi.executeAuto(sessionId.value).catch((e: any) => {
      error.value = e.message || '执行失败'
      status.value = 'failed'
      stopPolling()
    })
  }

  // 开始轮询状态
  function startPolling() {
    if (pollTimer) {
      clearInterval(pollTimer)
    }

    pollTimer = setInterval(async () => {
      if (!sessionId.value) {
        stopPolling()
        return
      }

      try {
        const result: any = await workflowApi.getStatus(sessionId.value)
        progress.value = result.progress
        currentStage.value = result.stage as WorkflowStage

        if (result.status === 'completed') {
          status.value = 'completed'
          stopPolling()

          // 获取最终结果
          await loadSessionDetail()
        } else if (result.status === 'failed') {
          status.value = 'failed'
          error.value = result.error || '执行失败'
          stopPolling()
        }
      } catch (e) {
        console.error('轮询状态失败', e)
      }
    }, 1000)  // 每秒轮询一次，实时跟踪进度
  }

  // 停止轮询
  function stopPolling() {
    if (pollTimer) {
      clearInterval(pollTimer)
      pollTimer = null
    }
    loading.value = false
  }

  // 加载会话详情
  async function loadSessionDetail() {
    if (!sessionId.value) return

    try {
      const result: any = await workflowApi.getDetail(sessionId.value)

      if (result.article) {
        articlePreview.value = {
          title: result.article.title,
          content: result.article.content,
          full_content: result.article.content,
          image_prompts: result.article.image_prompts,
          images: result.article.images,
        }
      }

      if (result.messages) {
        messages.value = result.messages
      }

      currentStage.value = result.stage as WorkflowStage
      progress.value = result.progress
    } catch (e) {
      console.error('加载会话详情失败', e)
    }
  }

  // 重置状态
  function reset() {
    stopPolling()
    sessionId.value = null
    articleId.value = null
    mode.value = 'manual'
    contentType.value = 'article'
    currentStage.value = 'generate'
    messages.value = []
    articlePreview.value = null
    suggestions.value = []
    progress.value = 0
    status.value = 'idle'
    error.value = null
    loading.value = false
  }

  return {
    // 状态
    sessionId,
    articleId,
    mode,
    contentType,
    currentStage,
    messages,
    articlePreview,
    suggestions,
    progress,
    status,
    error,
    loading,

    // 计算属性
    isAutoMode,
    isWeitoutiao,
    isCompleted,
    isSessionActive,
    canProceed,
    currentStageLabel,
    stageLabels,

    // 方法
    createSession,
    sendMessage,
    nextStage,
    executeAuto,
    loadSessionDetail,
    reset,
    stopPolling,
  }
})
