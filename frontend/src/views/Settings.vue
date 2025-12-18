<template>
  <div class="settings-page">
    <h2 class="page-title">系统设置</h2>

    <el-row :gutter="20">
      <el-col :span="12">
        <!-- 文章生成配置 -->
        <el-card class="setting-card">
          <template #header>
            <span>文章生成 API</span>
          </template>
          <el-form label-width="100px">
            <el-form-item label="API Key">
              <el-input v-model="configs.article_generate.api_key" type="password" show-password placeholder="API Key" />
            </el-form-item>
            <el-form-item label="API URL">
              <el-input v-model="configs.article_generate.api_url" placeholder="https://api.openai.com" />
            </el-form-item>
            <el-form-item label="Model">
              <el-input v-model="configs.article_generate.model" placeholder="gpt-4" />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" @click="saveConfig('article_generate')" :loading="saving.article_generate">
                保存
              </el-button>
            </el-form-item>
          </el-form>
        </el-card>

        <!-- 文章优化配置 -->
        <el-card class="setting-card">
          <template #header>
            <span>文章优化 API</span>
          </template>
          <el-form label-width="100px">
            <el-form-item label="API Key">
              <el-input v-model="configs.article_humanize.api_key" type="password" show-password placeholder="API Key" />
            </el-form-item>
            <el-form-item label="API URL">
              <el-input v-model="configs.article_humanize.api_url" placeholder="https://api.openai.com" />
            </el-form-item>
            <el-form-item label="Model">
              <el-input v-model="configs.article_humanize.model" placeholder="gpt-4" />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" @click="saveConfig('article_humanize')" :loading="saving.article_humanize">
                保存
              </el-button>
            </el-form-item>
          </el-form>
        </el-card>
      </el-col>

      <el-col :span="12">
        <!-- 图片生成配置 -->
        <el-card class="setting-card">
          <template #header>
            <span>图片生成 API</span>
          </template>
          <el-form label-width="100px">
            <el-form-item label="API Key">
              <el-input v-model="configs.image_generate.api_key" type="password" show-password placeholder="API Key" />
            </el-form-item>
            <el-form-item label="API URL">
              <el-input v-model="configs.image_generate.api_url" placeholder="http://116.205.244.106:9006" />
            </el-form-item>
            <el-form-item label="Model">
              <el-input v-model="configs.image_generate.model" placeholder="gemini-3.0-pro" />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" @click="saveConfig('image_generate')" :loading="saving.image_generate">
                保存
              </el-button>
            </el-form-item>
          </el-form>
        </el-card>

        <!-- 系统信息 -->
        <el-card class="setting-card">
          <template #header>
            <span>系统信息</span>
          </template>
          <el-descriptions :column="1" border>
            <el-descriptions-item label="版本">1.0.0</el-descriptions-item>
            <el-descriptions-item label="后端状态">
              <el-tag :type="backendStatus ? 'success' : 'danger'">
                {{ backendStatus ? '正常' : '异常' }}
              </el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="数据库">PostgreSQL</el-descriptions-item>
          </el-descriptions>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import api, { aiConfigApi } from '@/api'

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

<style lang="scss" scoped>
.settings-page {
  .page-title {
    margin-bottom: 20px;
    font-size: 20px;
    color: #303133;
  }

  .setting-card {
    margin-bottom: 20px;
  }
}
</style>
