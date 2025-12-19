<template>
  <div class="settings-redesign">
    <!-- 页面标题 -->
    <header class="mb-10">
      <h1 class="text-4xl font-extrabold tracking-tight text-deep-black">
        系统设置
      </h1>
      <p class="mt-2 text-sm text-gray-500">
        配置 AI 服务和系统参数
      </p>
    </header>

    <div class="grid grid-cols-2 gap-6">
      <!-- 左侧：API配置 -->
      <div class="space-y-6">
        <!-- 文章生成配置 -->
        <div class="glass-container p-8">
          <div class="flex items-center gap-3 mb-6">
            <div class="w-10 h-10 rounded-xl bg-blue-500 flex items-center justify-center">
              <Sparkles :size="20" :stroke-width="2" class="text-white" />
            </div>
            <div>
              <div class="tag-label">Article Generate</div>
              <h3 class="text-lg font-bold text-deep-black mt-1">文章生成 API</h3>
            </div>
          </div>

          <div class="space-y-4">
            <div>
              <label class="text-sm font-semibold text-gray-700 mb-2 block">API Key</label>
              <input
                v-model="configs.article_generate.api_key"
                type="password"
                class="input-inset w-full"
                placeholder="sk-..."
              />
            </div>
            <div>
              <label class="text-sm font-semibold text-gray-700 mb-2 block">API URL</label>
              <input
                v-model="configs.article_generate.api_url"
                type="text"
                class="input-inset w-full"
                placeholder="https://api.openai.com"
              />
            </div>
            <div>
              <label class="text-sm font-semibold text-gray-700 mb-2 block">Model</label>
              <input
                v-model="configs.article_generate.model"
                type="text"
                class="input-inset w-full"
                placeholder="gpt-4"
              />
            </div>
            <button
              class="btn-primary w-full flex items-center justify-center gap-2"
              :disabled="saving.article_generate"
              @click="saveConfig('article_generate')"
            >
              <Save v-if="!saving.article_generate" :size="18" :stroke-width="2" />
              <div v-else class="animate-spin w-4 h-4 border-2 border-white border-t-transparent rounded-full"></div>
              {{ saving.article_generate ? '保存中...' : '保存配置' }}
            </button>
          </div>
        </div>

        <!-- 文章优化配置 -->
        <div class="glass-container p-8">
          <div class="flex items-center gap-3 mb-6">
            <div class="w-10 h-10 rounded-xl bg-green-500 flex items-center justify-center">
              <Wand2 :size="20" :stroke-width="2" class="text-white" />
            </div>
            <div>
              <div class="tag-label">Article Humanize</div>
              <h3 class="text-lg font-bold text-deep-black mt-1">文章优化 API</h3>
            </div>
          </div>

          <div class="space-y-4">
            <div>
              <label class="text-sm font-semibold text-gray-700 mb-2 block">API Key</label>
              <input
                v-model="configs.article_humanize.api_key"
                type="password"
                class="input-inset w-full"
                placeholder="sk-..."
              />
            </div>
            <div>
              <label class="text-sm font-semibold text-gray-700 mb-2 block">API URL</label>
              <input
                v-model="configs.article_humanize.api_url"
                type="text"
                class="input-inset w-full"
                placeholder="https://api.openai.com"
              />
            </div>
            <div>
              <label class="text-sm font-semibold text-gray-700 mb-2 block">Model</label>
              <input
                v-model="configs.article_humanize.model"
                type="text"
                class="input-inset w-full"
                placeholder="gpt-4"
              />
            </div>
            <button
              class="btn-primary w-full flex items-center justify-center gap-2"
              :disabled="saving.article_humanize"
              @click="saveConfig('article_humanize')"
            >
              <Save v-if="!saving.article_humanize" :size="18" :stroke-width="2" />
              <div v-else class="animate-spin w-4 h-4 border-2 border-white border-t-transparent rounded-full"></div>
              {{ saving.article_humanize ? '保存中...' : '保存配置' }}
            </button>
          </div>
        </div>
      </div>

      <!-- 右侧：图片生成 + 系统信息 -->
      <div class="space-y-6">
        <!-- 图片生成配置 -->
        <div class="glass-container p-8">
          <div class="flex items-center gap-3 mb-6">
            <div class="w-10 h-10 rounded-xl bg-purple-500 flex items-center justify-center">
              <ImageIcon :size="20" :stroke-width="2" class="text-white" />
            </div>
            <div>
              <div class="tag-label">Image Generate</div>
              <h3 class="text-lg font-bold text-deep-black mt-1">图片生成 API</h3>
            </div>
          </div>

          <div class="space-y-4">
            <div>
              <label class="text-sm font-semibold text-gray-700 mb-2 block">API Key</label>
              <input
                v-model="configs.image_generate.api_key"
                type="password"
                class="input-inset w-full"
                placeholder="Optional"
              />
            </div>
            <div>
              <label class="text-sm font-semibold text-gray-700 mb-2 block">API URL</label>
              <input
                v-model="configs.image_generate.api_url"
                type="text"
                class="input-inset w-full"
                placeholder="http://116.205.244.106:9006"
              />
            </div>
            <div>
              <label class="text-sm font-semibold text-gray-700 mb-2 block">Model</label>
              <input
                v-model="configs.image_generate.model"
                type="text"
                class="input-inset w-full"
                placeholder="gemini-3.0-pro"
              />
            </div>
            <button
              class="btn-primary w-full flex items-center justify-center gap-2"
              :disabled="saving.image_generate"
              @click="saveConfig('image_generate')"
            >
              <Save v-if="!saving.image_generate" :size="18" :stroke-width="2" />
              <div v-else class="animate-spin w-4 h-4 border-2 border-white border-t-transparent rounded-full"></div>
              {{ saving.image_generate ? '保存中...' : '保存配置' }}
            </button>
          </div>
        </div>

        <!-- 系统信息 -->
        <div class="glass-container p-8">
          <div class="tag-label mb-4">System Information</div>
          <h3 class="text-lg font-bold text-deep-black mb-6">系统信息</h3>

          <div class="space-y-4">
            <div class="flex items-center justify-between p-4 rounded-xl bg-gray-50/50">
              <span class="text-sm font-semibold text-gray-600">系统版本</span>
              <span class="text-sm font-bold text-deep-black">1.0.0</span>
            </div>

            <div class="flex items-center justify-between p-4 rounded-xl bg-gray-50/50">
              <span class="text-sm font-semibold text-gray-600">后端状态</span>
              <span
                class="px-3 py-1 rounded-lg text-xs font-bold uppercase tracking-wider"
                :class="backendStatus ? 'bg-green-100 text-green-600' : 'bg-red-100 text-red-600'"
              >
                {{ backendStatus ? '正常' : '异常' }}
              </span>
            </div>

            <div class="flex items-center justify-between p-4 rounded-xl bg-gray-50/50">
              <span class="text-sm font-semibold text-gray-600">数据库</span>
              <span class="text-sm font-bold text-deep-black">PostgreSQL</span>
            </div>

            <div class="flex items-center justify-between p-4 rounded-xl bg-gray-50/50">
              <span class="text-sm font-semibold text-gray-600">设计系统</span>
              <span class="text-sm font-bold text-deep-black">Zen-iOS Hybrid</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import api, { aiConfigApi } from '@/api'
import {
  Sparkles,
  Wand2,
  Image as ImageIcon,
  Save,
} from 'lucide-vue-next'

const backendStatus = ref(true)
const loading = ref(false)

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

const saveConfig = async (type: keyof typeof configs) => {
  saving[type] = true
  try {
    await aiConfigApi.update(type, configs[type])
    ElMessage.success('保存成功')
  } catch (e) {
    console.error('Save config failed:', e)
  } finally {
    saving[type] = false
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
})
</script>

<style scoped>
.settings-redesign {
  @apply animate-in;
}
</style>
