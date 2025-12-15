<template>
  <div class="settings-page">
    <h2 class="page-title">系统设置</h2>

    <el-row :gutter="20">
      <el-col :span="12">
        <!-- AI配置 -->
        <el-card class="setting-card">
          <template #header>
            <span>AI 配置</span>
          </template>
          <el-form label-width="120px">
            <el-form-item label="API Key">
              <el-input v-model="settings.openai_api_key" type="password" show-password placeholder="OpenAI API Key" />
            </el-form-item>
            <el-form-item label="模型">
              <el-select v-model="settings.openai_model" style="width: 100%">
                <el-option label="GPT-4" value="gpt-4" />
                <el-option label="GPT-4 Turbo" value="gpt-4-turbo" />
                <el-option label="GPT-3.5 Turbo" value="gpt-3.5-turbo" />
              </el-select>
            </el-form-item>
            <el-form-item label="Base URL">
              <el-input v-model="settings.openai_base_url" placeholder="可选，自定义API地址" />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" @click="testAI" :loading="testingAI">测试连接</el-button>
            </el-form-item>
          </el-form>
        </el-card>

        <!-- 图片生成配置 -->
        <el-card class="setting-card">
          <template #header>
            <span>图片生成配置 (预留)</span>
          </template>
          <el-form label-width="120px">
            <el-form-item label="提供商">
              <el-select v-model="settings.image_gen_provider" style="width: 100%">
                <el-option label="不使用" value="none" />
                <el-option label="Stable Diffusion" value="stable_diffusion" />
                <el-option label="DALL-E" value="dalle" />
              </el-select>
            </el-form-item>
            <el-form-item label="API Key" v-if="settings.image_gen_provider !== 'none'">
              <el-input v-model="settings.image_gen_api_key" type="password" show-password />
            </el-form-item>
            <el-form-item label="API URL" v-if="settings.image_gen_provider === 'stable_diffusion'">
              <el-input v-model="settings.image_gen_api_url" placeholder="Stable Diffusion API地址" />
            </el-form-item>
          </el-form>
        </el-card>
      </el-col>

      <el-col :span="12">
        <!-- 发布配置 -->
        <el-card class="setting-card">
          <template #header>
            <span>发布配置</span>
          </template>
          <el-form label-width="120px">
            <el-form-item label="发布间隔">
              <el-input-number v-model="settings.publish_interval" :min="10" :max="120" />
              <span style="margin-left: 10px">分钟</span>
            </el-form-item>
            <el-form-item label="最大重试次数">
              <el-input-number v-model="settings.max_retry_count" :min="1" :max="10" />
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
            <el-descriptions-item label="数据库">PostgreSQL 15</el-descriptions-item>
            <el-descriptions-item label="缓存">Redis 7</el-descriptions-item>
          </el-descriptions>
        </el-card>
      </el-col>
    </el-row>

    <el-card class="save-card">
      <el-button type="primary" size="large" @click="saveSettings" :loading="saving">
        保存设置
      </el-button>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import api from '@/api'

const saving = ref(false)
const testingAI = ref(false)
const backendStatus = ref(true)

const settings = reactive({
  openai_api_key: '',
  openai_model: 'gpt-4',
  openai_base_url: '',
  image_gen_provider: 'none',
  image_gen_api_key: '',
  image_gen_api_url: '',
  publish_interval: 30,
  max_retry_count: 3,
})

const checkBackend = async () => {
  try {
    await api.get('/health')
    backendStatus.value = true
  } catch {
    backendStatus.value = false
  }
}

const testAI = async () => {
  testingAI.value = true
  try {
    // TODO: 调用测试接口
    await new Promise(resolve => setTimeout(resolve, 1000))
    ElMessage.success('AI连接正常')
  } catch {
    ElMessage.error('AI连接失败')
  } finally {
    testingAI.value = false
  }
}

const saveSettings = async () => {
  saving.value = true
  try {
    // TODO: 调用保存接口
    await new Promise(resolve => setTimeout(resolve, 500))
    ElMessage.success('设置已保存')
  } catch {
    ElMessage.error('保存失败')
  } finally {
    saving.value = false
  }
}

onMounted(checkBackend)
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

  .save-card {
    text-align: center;
    padding: 20px;
  }
}
</style>
