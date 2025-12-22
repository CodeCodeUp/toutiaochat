<template>
  <div class="prompts-redesign">
    <!-- 页面标题 -->
    <header class="mb-10">
      <div class="flex items-center justify-between">
        <div>
          <h1 class="text-4xl font-extrabold tracking-tight text-deep-black">
            提示词管理
          </h1>
          <p class="mt-2 text-sm text-gray-500">
            管理 AI 生成和优化的提示词模板
          </p>
        </div>
        <button class="btn-primary flex items-center gap-2" @click="showCreateDialog">
          <Plus :size="20" :stroke-width="2" />
          新建提示词
        </button>
      </div>
    </header>

    <!-- 提示词列表 -->
    <div class="glass-container p-8">
      <div v-if="prompts.length === 0" class="text-center py-12 text-gray-400">
        <MessageSquare :size="48" :stroke-width="1.5" class="mx-auto mb-3 opacity-50" />
        <p>暂无提示词</p>
      </div>

      <div v-else class="space-y-3">
        <div
          v-for="prompt in prompts"
          :key="prompt.id"
          class="glass-card p-6 flex items-start gap-6 group"
        >
          <!-- 类型图标 -->
          <div
            class="w-12 h-12 rounded-2xl flex items-center justify-center flex-shrink-0"
            :class="getTypeIconBg(prompt.type)"
          >
            <component :is="getTypeIcon(prompt.type)" :size="24" :stroke-width="2" class="text-white" />
          </div>

          <!-- 提示词信息 -->
          <div class="flex-1 min-w-0">
            <div class="flex items-center gap-3 mb-2">
              <h3 class="text-lg font-bold text-deep-black truncate">
                {{ prompt.name }}
              </h3>
              <span
                class="px-2 py-1 rounded-lg text-xs font-bold uppercase tracking-wider flex-shrink-0"
                :class="getTypeClass(prompt.type)"
              >
                {{ getTypeText(prompt.type) }}
              </span>
              <span
                class="px-2 py-1 rounded-lg text-xs font-bold tracking-wider flex-shrink-0"
                :class="prompt.content_type === 'weitoutiao' ? 'bg-orange-100 text-orange-600' : 'bg-cyan-100 text-cyan-600'"
              >
                {{ prompt.content_type === 'weitoutiao' ? '微头条' : '文章' }}
              </span>
            </div>

            <p v-if="prompt.description" class="text-sm text-gray-500 mb-3 line-clamp-2">
              {{ prompt.description }}
            </p>

            <div class="flex items-center gap-4 text-xs text-gray-400">
              <span class="flex items-center gap-1">
                <FileText :size="12" />
                {{ prompt.content?.length || 0 }} 字符
              </span>
            </div>
          </div>

          <!-- 状态和操作 -->
          <div class="flex items-center gap-3 flex-shrink-0">
            <span
              class="px-3 py-1 rounded-lg text-xs font-bold uppercase tracking-wider"
              :class="prompt.is_active === 'true' ? 'bg-green-100 text-green-600' : 'bg-gray-100 text-gray-500'"
            >
              {{ prompt.is_active === 'true' ? '已启用' : '未启用' }}
            </span>

            <button
              class="w-8 h-8 rounded-lg hover:bg-gray-100/50 flex items-center justify-center transition"
              @click="editPrompt(prompt)"
            >
              <Edit2 :size="18" :stroke-width="2" class="text-gray-500" />
            </button>

            <button
              class="w-8 h-8 rounded-lg hover:bg-red-100/50 flex items-center justify-center transition"
              @click="deletePrompt(prompt.id)"
            >
              <Trash2 :size="18" :stroke-width="2" class="text-red-500" />
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- 编辑对话框 -->
    <el-dialog
      v-model="dialogVisible"
      :title="editingPrompt ? '编辑提示词' : '新建提示词'"
      width="900px"
      destroy-on-close
    >
      <el-form :model="formData" label-width="100px">
        <el-form-item label="名称">
          <el-input v-model="formData.name" placeholder="请输入提示词名称" />
        </el-form-item>
        <el-form-item label="类型">
          <el-select v-model="formData.type" placeholder="请选择类型" style="width: 100%">
            <el-option label="文章生成" value="generate" />
            <el-option label="文章优化" value="humanize" />
            <el-option label="图片生成" value="image" />
          </el-select>
        </el-form-item>
        <el-form-item label="内容类型">
          <el-select v-model="formData.content_type" placeholder="请选择内容类型" style="width: 100%">
            <el-option label="文章" value="article" />
            <el-option label="微头条" value="weitoutiao" />
          </el-select>
        </el-form-item>
        <el-form-item label="是否启用">
          <el-switch
            v-model="formData.is_active"
            active-value="true"
            inactive-value="false"
          />
        </el-form-item>
        <el-form-item label="描述">
          <el-input
            v-model="formData.description"
            type="textarea"
            :rows="2"
            placeholder="请输入提示词描述"
          />
        </el-form-item>
        <el-form-item label="提示词内容">
          <div v-if="formData.type" class="mb-2 text-xs text-gray-500 bg-gray-50 p-3 rounded-lg">
            <template v-if="formData.type === 'generate'">
              <strong>文章生成提示词</strong> - 需要求 AI 返回 JSON 格式：
              <code class="block mt-1 text-blue-600">{"title": "标题", "content": "正文", "image_prompts": [{"description": "图片描述", "position": "cover|after_paragraph:N|end"}]}</code>
            </template>
            <template v-else-if="formData.type === 'image'">
              <strong>图片描述生成提示词</strong> - 需要求 AI 返回 JSON 格式：
              <code class="block mt-1 text-purple-600">{"prompts": [{"description": "图片描述", "position": "cover|after_paragraph:N|end"}]}</code>
            </template>
            <template v-else-if="formData.type === 'humanize'">
              <strong>文章优化提示词</strong> - 用于降低 AI 痕迹、优化文章可读性
            </template>
          </div>
          <el-input
            v-model="formData.content"
            type="textarea"
            :rows="15"
            placeholder="请输入提示词内容"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="savePrompt">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { promptApi } from '@/api'
import {
  Plus,
  MessageSquare,
  FileText,
  Edit2,
  Trash2,
  Sparkles,
  Wand2,
  Image as ImageIcon,
} from 'lucide-vue-next'

const prompts = ref<any[]>([])
const dialogVisible = ref(false)
const editingPrompt = ref<any>(null)
const formData = ref({
  name: '',
  type: 'generate',
  content_type: 'article',
  content: '',
  is_active: 'true',
  description: '',
})

// 加载提示词列表
const loadPrompts = async () => {
  try {
    const data: any = await promptApi.list()
    prompts.value = data
  } catch (error) {
    console.error('加载提示词失败:', error)
  }
}

// 显示创建对话框
const showCreateDialog = () => {
  editingPrompt.value = null
  formData.value = {
    name: '',
    type: 'generate',
    content_type: 'article',
    content: '',
    is_active: 'true',
    description: '',
  }
  dialogVisible.value = true
}

// 编辑提示词
const editPrompt = (prompt: any) => {
  editingPrompt.value = prompt
  formData.value = {
    name: prompt.name,
    type: prompt.type,
    content_type: prompt.content_type || 'article',
    content: prompt.content,
    is_active: prompt.is_active,
    description: prompt.description || '',
  }
  dialogVisible.value = true
}

// 保存提示词
const savePrompt = async () => {
  try {
    if (editingPrompt.value) {
      await promptApi.update(editingPrompt.value.id, formData.value)
      ElMessage.success('更新成功')
    } else {
      await promptApi.create(formData.value)
      ElMessage.success('创建成功')
    }
    dialogVisible.value = false
    loadPrompts()
  } catch (error) {
    console.error('保存失败:', error)
  }
}

// 删除提示词
const deletePrompt = async (id: string) => {
  try {
    await ElMessageBox.confirm('确定要删除这个提示词吗？', '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning',
    })
    await promptApi.delete(id)
    ElMessage.success('删除成功')
    loadPrompts()
  } catch (error: any) {
    if (error !== 'cancel') {
      console.error('删除失败:', error)
    }
  }
}

const getTypeIcon = (type: string) => {
  const map: Record<string, any> = {
    generate: Sparkles,
    humanize: Wand2,
    image: ImageIcon,
  }
  return map[type] || FileText
}

const getTypeIconBg = (type: string) => {
  const map: Record<string, string> = {
    generate: 'bg-blue-500',
    humanize: 'bg-green-500',
    image: 'bg-purple-500',
  }
  return map[type] || 'bg-gray-500'
}

const getTypeClass = (type: string) => {
  const map: Record<string, string> = {
    generate: 'bg-blue-100 text-blue-600',
    humanize: 'bg-green-100 text-green-600',
    image: 'bg-purple-100 text-purple-600',
  }
  return map[type] || 'bg-gray-100 text-gray-600'
}

const getTypeText = (type: string) => {
  const map: Record<string, string> = {
    generate: '文章生成',
    humanize: '文章优化',
    image: '图片生成',
  }
  return map[type] || type
}

onMounted(() => {
  loadPrompts()
})
</script>

<style scoped>
.prompts-redesign {
  @apply animate-in;
}

.line-clamp-2 {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
</style>
