<template>
  <div class="settings-redesign max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
    <!-- 页面标题 -->
    <header class="mb-10">
      <h1 class="text-4xl font-extrabold tracking-tight text-deep-black">
        系统设置
      </h1>
      <p class="mt-2 text-sm text-gray-500 font-medium">
        全自动流水线配置中心
      </p>
    </header>

    <div class="flex flex-col lg:flex-row gap-8 items-start">
      <!-- 左侧：主要配置区 -->
      <div class="flex-1 w-full space-y-8">
        
        <!-- 工作流配置 -->
        <section>
          <div class="flex items-center gap-2 mb-4 text-gray-400 uppercase tracking-wider text-xs font-bold">
            <Workflow :size="14" />
            <span>Workflow Automation</span>
          </div>
          
          <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
            <!-- 文章工作流 -->
            <div class="bg-white rounded-2xl border border-gray-100 shadow-sm p-6 relative overflow-hidden">
              <div class="absolute top-0 right-0 p-4 opacity-10 pointer-events-none">
                <FileText :size="80" class="text-indigo-500" />
              </div>
              
              <div class="flex items-center gap-3 mb-6 relative z-10">
                <div class="w-10 h-10 rounded-xl bg-indigo-50 text-indigo-600 flex items-center justify-center border border-indigo-100">
                  <FileText :size="20" :stroke-width="2.5" />
                </div>
                <div>
                  <h3 class="text-lg font-bold text-gray-900">文章工作流</h3>
                  <p class="text-xs text-gray-500">长内容自动生成配置</p>
                </div>
              </div>

              <div class="space-y-1 relative z-10">
                <div class="setting-item">
                  <div class="setting-label">
                    <span>自定义话题</span>
                    <p>创建时手动输入话题</p>
                  </div>
                  <el-switch v-model="workflowConfigs.article.enable_custom_topic" style="--el-switch-on-color: #6366f1;" />
                </div>

                <div class="setting-item">
                  <div class="setting-label">
                    <span>内容优化</span>
                    <p>AI 润色与去痕迹</p>
                  </div>
                  <el-switch v-model="workflowConfigs.article.enable_optimize" style="--el-switch-on-color: #6366f1;" />
                </div>

                <div class="setting-item">
                  <div class="setting-label">
                    <span>自动配图</span>
                    <p>根据内容生成封面/插图</p>
                  </div>
                  <el-switch v-model="workflowConfigs.article.enable_image_gen" style="--el-switch-on-color: #6366f1;" />
                </div>

                <div class="setting-item">
                  <div class="setting-label">
                    <span>自动发布</span>
                    <p>生成完毕后直接推送</p>
                  </div>
                  <el-switch v-model="workflowConfigs.article.enable_auto_publish" style="--el-switch-on-color: #6366f1;" />
                </div>
              </div>

              <div class="mt-6 pt-4 border-t border-gray-50 relative z-10">
                <button
                  class="w-full py-2.5 rounded-xl bg-indigo-50 text-indigo-600 font-bold text-sm hover:bg-indigo-100 transition-colors flex items-center justify-center gap-2"
                  :disabled="savingWorkflow.article"
                  @click="saveWorkflowConfig('article')"
                >
                  <Save v-if="!savingWorkflow.article" :size="16" />
                  <div v-else class="animate-spin w-4 h-4 border-2 border-current border-t-transparent rounded-full"></div>
                  {{ savingWorkflow.article ? '保存中...' : '保存配置' }}
                </button>
              </div>
            </div>

            <!-- 微头条工作流 -->
            <div class="bg-white rounded-2xl border border-gray-100 shadow-sm p-6 relative overflow-hidden">
              <div class="absolute top-0 right-0 p-4 opacity-10 pointer-events-none">
                <MessageCircle :size="80" class="text-orange-500" />
              </div>

              <div class="flex items-center gap-3 mb-6 relative z-10">
                <div class="w-10 h-10 rounded-xl bg-orange-50 text-orange-600 flex items-center justify-center border border-orange-100">
                  <MessageCircle :size="20" :stroke-width="2.5" />
                </div>
                <div>
                  <h3 class="text-lg font-bold text-gray-900">微头条工作流</h3>
                  <p class="text-xs text-gray-500">短内容自动生成配置</p>
                </div>
              </div>

              <div class="space-y-1 relative z-10">
                <div class="setting-item">
                  <div class="setting-label">
                    <span>自定义话题</span>
                    <p>创建时手动输入话题</p>
                  </div>
                  <el-switch v-model="workflowConfigs.weitoutiao.enable_custom_topic" style="--el-switch-on-color: #f97316;" />
                </div>

                <div class="setting-item">
                  <div class="setting-label">
                    <span>内容优化</span>
                    <p>AI 润色与去痕迹</p>
                  </div>
                  <el-switch v-model="workflowConfigs.weitoutiao.enable_optimize" style="--el-switch-on-color: #f97316;" />
                </div>

                <div class="setting-item">
                  <div class="setting-label">
                    <span>自动配图</span>
                    <p>根据内容生成封面/插图</p>
                  </div>
                  <el-switch v-model="workflowConfigs.weitoutiao.enable_image_gen" style="--el-switch-on-color: #f97316;" />
                </div>

                <div class="setting-item">
                  <div class="setting-label">
                    <span>自动发布</span>
                    <p>生成完毕后直接推送</p>
                  </div>
                  <el-switch v-model="workflowConfigs.weitoutiao.enable_auto_publish" style="--el-switch-on-color: #f97316;" />
                </div>
              </div>

               <div class="mt-6 pt-4 border-t border-gray-50 relative z-10">
                <button
                  class="w-full py-2.5 rounded-xl bg-orange-50 text-orange-600 font-bold text-sm hover:bg-orange-100 transition-colors flex items-center justify-center gap-2"
                  :disabled="savingWorkflow.weitoutiao"
                  @click="saveWorkflowConfig('weitoutiao')"
                >
                  <Save v-if="!savingWorkflow.weitoutiao" :size="16" />
                  <div v-else class="animate-spin w-4 h-4 border-2 border-current border-t-transparent rounded-full"></div>
                  {{ savingWorkflow.weitoutiao ? '保存中...' : '保存配置' }}
                </button>
              </div>
            </div>
          </div>
        </section>

        <!-- AI API 配置 -->
        <section>
          <div class="flex items-center gap-2 mb-4 text-gray-400 uppercase tracking-wider text-xs font-bold">
            <Cpu :size="14" />
            <span>AI Model Connections</span>
          </div>

          <div class="space-y-4">
            <!-- 文章生成 API -->
            <div class="bg-white rounded-xl border border-gray-200 p-6 flex flex-col md:flex-row md:items-start gap-6">
              <div class="flex items-center gap-3 w-48 flex-shrink-0">
                <div class="w-10 h-10 rounded-lg bg-blue-100 text-blue-600 flex items-center justify-center">
                  <Sparkles :size="20" />
                </div>
                <div>
                   <h4 class="font-bold text-gray-900 text-sm">文章生成</h4>
                   <span class="text-[10px] bg-gray-100 text-gray-500 px-1.5 py-0.5 rounded">Primary</span>
                </div>
              </div>
              
              <div class="flex-1 grid grid-cols-1 md:grid-cols-2 gap-4 w-full">
                <div class="col-span-2">
                   <label class="text-xs font-bold text-gray-500 uppercase mb-1.5 block">API Endpoint</label>
                   <input v-model="configs.article_generate.api_url" type="text" class="input-inset w-full text-sm font-mono" placeholder="https://api.openai.com/v1" />
                </div>
                <div>
                   <label class="text-xs font-bold text-gray-500 uppercase mb-1.5 block">Model Name</label>
                   <input v-model="configs.article_generate.model" type="text" class="input-inset w-full text-sm font-mono" placeholder="gpt-4" />
                </div>
                <div>
                   <label class="text-xs font-bold text-gray-500 uppercase mb-1.5 block">API Key</label>
                   <input v-model="configs.article_generate.api_key" type="password" class="input-inset w-full text-sm font-mono" placeholder="sk-..." />
                </div>
                <div class="col-span-2 flex justify-end">
                  <button 
                    class="btn-secondary py-2 px-4 text-xs"
                    :disabled="saving.article_generate"
                    @click="saveConfig('article_generate')"
                  >
                    {{ saving.article_generate ? '保存中...' : '保存更改' }}
                  </button>
                </div>
              </div>
            </div>

            <!-- 优化 API -->
            <div class="bg-white rounded-xl border border-gray-200 p-6 flex flex-col md:flex-row md:items-start gap-6">
              <div class="flex items-center gap-3 w-48 flex-shrink-0">
                <div class="w-10 h-10 rounded-lg bg-emerald-100 text-emerald-600 flex items-center justify-center">
                  <Wand2 :size="20" />
                </div>
                <div>
                   <h4 class="font-bold text-gray-900 text-sm">内容优化</h4>
                   <span class="text-[10px] bg-gray-100 text-gray-500 px-1.5 py-0.5 rounded">Humanize</span>
                </div>
              </div>
              
              <div class="flex-1 grid grid-cols-1 md:grid-cols-2 gap-4 w-full">
                <div class="col-span-2">
                   <label class="text-xs font-bold text-gray-500 uppercase mb-1.5 block">API Endpoint</label>
                   <input v-model="configs.article_humanize.api_url" type="text" class="input-inset w-full text-sm font-mono" placeholder="https://api.openai.com/v1" />
                </div>
                <div>
                   <label class="text-xs font-bold text-gray-500 uppercase mb-1.5 block">Model Name</label>
                   <input v-model="configs.article_humanize.model" type="text" class="input-inset w-full text-sm font-mono" placeholder="gpt-4" />
                </div>
                <div>
                   <label class="text-xs font-bold text-gray-500 uppercase mb-1.5 block">API Key</label>
                   <input v-model="configs.article_humanize.api_key" type="password" class="input-inset w-full text-sm font-mono" placeholder="sk-..." />
                </div>
                <div class="col-span-2 flex justify-end">
                  <button 
                    class="btn-secondary py-2 px-4 text-xs"
                    :disabled="saving.article_humanize"
                    @click="saveConfig('article_humanize')"
                  >
                    {{ saving.article_humanize ? '保存中...' : '保存更改' }}
                  </button>
                </div>
              </div>
            </div>
            
             <!-- 图片 API -->
            <div class="bg-white rounded-xl border border-gray-200 p-6 flex flex-col md:flex-row md:items-start gap-6">
              <div class="flex items-center gap-3 w-48 flex-shrink-0">
                <div class="w-10 h-10 rounded-lg bg-purple-100 text-purple-600 flex items-center justify-center">
                  <ImageIcon :size="20" />
                </div>
                <div>
                   <h4 class="font-bold text-gray-900 text-sm">图片生成</h4>
                   <span class="text-[10px] bg-gray-100 text-gray-500 px-1.5 py-0.5 rounded">SD / DALL-E</span>
                </div>
              </div>
              
              <div class="flex-1 grid grid-cols-1 md:grid-cols-2 gap-4 w-full">
                <div class="col-span-2">
                   <label class="text-xs font-bold text-gray-500 uppercase mb-1.5 block">API Endpoint</label>
                   <input v-model="configs.image_generate.api_url" type="text" class="input-inset w-full text-sm font-mono" placeholder="http://localhost:7860" />
                </div>
                <div>
                   <label class="text-xs font-bold text-gray-500 uppercase mb-1.5 block">Model Name</label>
                   <input v-model="configs.image_generate.model" type="text" class="input-inset w-full text-sm font-mono" placeholder="sdxl" />
                </div>
                <div>
                   <label class="text-xs font-bold text-gray-500 uppercase mb-1.5 block">API Key</label>
                   <input v-model="configs.image_generate.api_key" type="password" class="input-inset w-full text-sm font-mono" placeholder="Optional" />
                </div>
                <div class="col-span-2 flex justify-end">
                  <button 
                    class="btn-secondary py-2 px-4 text-xs"
                    :disabled="saving.image_generate"
                    @click="saveConfig('image_generate')"
                  >
                    {{ saving.image_generate ? '保存中...' : '保存更改' }}
                  </button>
                </div>
              </div>
            </div>

          </div>
        </section>
      </div>

      <!-- 右侧：系统信息 -->
      <div class="lg:w-80 flex-shrink-0 space-y-6">
        <section>
          <div class="flex items-center gap-2 mb-4 text-gray-400 uppercase tracking-wider text-xs font-bold">
            <Activity :size="14" />
            <span>System Status</span>
          </div>

          <div class="bg-white rounded-2xl border border-gray-100 shadow-sm p-5 space-y-5">
            <div class="text-center pb-4 border-b border-gray-100">
              <div class="text-xs text-gray-400 uppercase font-bold mb-1">Backend Connection</div>
              <div class="flex items-center justify-center gap-2">
                <div class="w-2.5 h-2.5 rounded-full" :class="backendStatus ? 'bg-green-500 animate-pulse' : 'bg-red-500'"></div>
                <span class="font-bold text-gray-800">{{ backendStatus ? 'Online' : 'Offline' }}</span>
              </div>
            </div>

            <div class="grid grid-cols-2 gap-3">
              <div class="bg-gray-50 rounded-lg p-3 text-center">
                 <div class="text-[10px] text-gray-400 uppercase font-bold">Version</div>
                 <div class="font-mono font-bold text-gray-700">v1.2.0</div>
              </div>
              <div class="bg-gray-50 rounded-lg p-3 text-center">
                 <div class="text-[10px] text-gray-400 uppercase font-bold">Database</div>
                 <div class="font-bold text-gray-700 text-sm">Postgres</div>
              </div>
            </div>

            <div class="text-xs text-center text-gray-400">
               <p>ToutiaoChat Pro</p>
               <p class="mt-1">Designed with Zen-iOS</p>
            </div>
          </div>
        </section>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import api, { aiConfigApi, workflowConfigApi } from '@/api'
import {
  Sparkles,
  Wand2,
  Image as ImageIcon,
  Save,
  FileText,
  MessageCircle,
  Workflow,
  Cpu,
  Activity
} from 'lucide-vue-next'

const backendStatus = ref(true)
const loading = ref(false)

// AI 配置
const configs = reactive({
  article_generate: { api_key: '', api_url: '', model: '' },
  article_humanize: { api_key: '', api_url: '', model: '' },
  image_generate: { api_key: '', api_url: '', model: '' },
})

const saving = reactive({
  article_generate: false,
  article_humanize: false,
  image_generate: false,
})

// 工作流配置
const workflowConfigs = reactive({
  article: {
    enable_custom_topic: false,
    enable_optimize: true,
    enable_image_gen: true,
    enable_auto_publish: false,
  },
  weitoutiao: {
    enable_custom_topic: false,
    enable_optimize: true,
    enable_image_gen: true,
    enable_auto_publish: false,
  },
})

const savingWorkflow = reactive({
  article: false,
  weitoutiao: false,
})

const loadConfigs = async () => {
  loading.value = true
  try {
    const res: any = await aiConfigApi.getAll()
    if (res.configs) {
      for (const key of ['article_generate', 'article_humanize', 'image_generate']) {
        if (res.configs[key]) {
          configs[key as keyof typeof configs] = {
            api_key: res.configs[key].api_key || '',
            api_url: res.configs[key].api_url || '',
            model: res.configs[key].model || '',
          }
        }
      }
    }
  } catch (e) {
    console.error('Load configs failed:', e)
  } finally {
    loading.value = false
  }
}

const loadWorkflowConfigs = async () => {
  try {
    const res: any = await workflowConfigApi.getAll()
    if (res.configs) {
      for (const key of ['article', 'weitoutiao'] as const) {
        if (res.configs[key]) {
          workflowConfigs[key] = {
            enable_custom_topic: res.configs[key].enable_custom_topic ?? false,
            enable_optimize: res.configs[key].enable_optimize ?? true,
            enable_image_gen: res.configs[key].enable_image_gen ?? true,
            enable_auto_publish: res.configs[key].enable_auto_publish ?? false,
          }
        }
      }
    }
  } catch (e) {
    console.error('Load workflow configs failed:', e)
  }
}

const saveConfig = async (type: keyof typeof configs) => {
  saving[type] = true
  try {
    await aiConfigApi.update(type, configs[type])
    ElMessage.success('API配置保存成功')
  } catch (e) {
    console.error('Save config failed:', e)
  } finally {
    saving[type] = false
  }
}

const saveWorkflowConfig = async (type: 'article' | 'weitoutiao') => {
  savingWorkflow[type] = true
  try {
    await workflowConfigApi.update(type, workflowConfigs[type])
    ElMessage.success('工作流配置已更新')
  } catch (e) {
    console.error('Save workflow config failed:', e)
  } finally {
    savingWorkflow[type] = false
  }
}

const checkBackend = async () => {
  try {
    await api.get('/health')
    backendStatus.value = true
  } catch {
    backendStatus.value = false
  }
}

onMounted(() => {
  checkBackend()
  loadConfigs()
  loadWorkflowConfigs()
})
</script>

<style scoped>
.settings-redesign {
  @apply animate-in;
}

.setting-item {
  @apply flex items-center justify-between p-3 rounded-lg hover:bg-gray-50 transition-colors;
}

.setting-label span {
  @apply text-sm font-semibold text-gray-700 block;
}

.setting-label p {
  @apply text-xs text-gray-400 mt-0.5;
}
</style>
