<template>
  <div class="prompts-redesign max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
    <!-- 页面标题 -->
    <header class="mb-10 flex flex-col md:flex-row md:items-center md:justify-between gap-4">
      <div>
        <h1 class="text-4xl font-extrabold tracking-tight text-deep-black">
          提示词管理
        </h1>
        <p class="mt-2 text-sm text-gray-500 font-medium">
          管理用于 AI 生成、优化和绘画的指令模板
        </p>
      </div>
      <button class="btn-primary flex items-center gap-2 shadow-lg shadow-deep-black/20" @click="showCreateDialog">
        <Plus :size="20" :stroke-width="2" />
        新建提示词
      </button>
    </header>

    <!-- 提示词列表 -->
    <div>
      <div v-if="prompts.length === 0" class="text-center py-20 bg-white/50 border-2 border-dashed border-gray-200 rounded-3xl">
        <div class="w-20 h-20 bg-gray-50 rounded-full flex items-center justify-center mx-auto mb-6">
          <MessageSquare :size="40" class="text-gray-300" />
        </div>
        <h3 class="text-lg font-bold text-gray-900 mb-2">暂无提示词</h3>
        <p class="text-gray-500 max-w-sm mx-auto mb-8">
          创建一个提示词模板来指导 AI 生成内容。
        </p>
        <button class="btn-primary" @click="showCreateDialog">
          <Plus :size="18" class="mr-2 inline-block" />
          创建第一个
        </button>
      </div>

      <div v-else class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        <div
          v-for="prompt in prompts"
          :key="prompt.id"
          class="bg-white rounded-2xl border border-gray-100 shadow-sm hover:shadow-xl hover:-translate-y-1 transition-all duration-300 flex flex-col overflow-hidden group"
        >
          <!-- 卡片头部 -->
          <div class="p-5 border-b border-gray-50 bg-gradient-to-b from-gray-50/50 to-white">
            <div class="flex items-start justify-between mb-4">
               <div
                class="w-12 h-12 rounded-xl flex items-center justify-center flex-shrink-0 shadow-sm"
                :class="getTypeIconBg(prompt.type)"
              >
                <component :is="getTypeIcon(prompt.type)" :size="24" :stroke-width="2" class="text-white" />
              </div>
              <div class="flex gap-2">
                 <button 
                  class="p-2 rounded-lg hover:bg-gray-100 text-gray-400 hover:text-blue-500 transition-colors" 
                  title="编辑"
                  @click="editPrompt(prompt)"
                 >
                   <Edit2 :size="18" />
                 </button>
                 <button 
                  class="p-2 rounded-lg hover:bg-red-50 text-gray-400 hover:text-red-500 transition-colors"
                  title="删除" 
                  @click="deletePrompt(prompt.id)"
                 >
                   <Trash2 :size="18" />
                 </button>
              </div>
            </div>

            <h3 class="text-lg font-bold text-gray-900 mb-2 truncate" :title="prompt.name">
              {{ prompt.name }}
            </h3>

            <div class="flex flex-wrap gap-2">
              <span
                class="px-2 py-0.5 rounded-md text-[10px] font-bold uppercase tracking-wider border"
                :class="getTypeClass(prompt.type)"
              >
                {{ getTypeText(prompt.type) }}
              </span>
              <span
                class="px-2 py-0.5 rounded-md text-[10px] font-bold tracking-wider border"
                :class="prompt.content_type === 'weitoutiao' ? 'bg-orange-50 text-orange-600 border-orange-100' : 'bg-cyan-50 text-cyan-600 border-cyan-100'"
              >
                {{ prompt.content_type === 'weitoutiao' ? '微头条' : '文章' }}
              </span>
               <span
                class="px-2 py-0.5 rounded-md text-[10px] font-bold uppercase tracking-wider border ml-auto"
                :class="prompt.is_active === 'true' ? 'bg-green-50 text-green-600 border-green-100' : 'bg-gray-100 text-gray-500 border-gray-200'"
              >
                {{ prompt.is_active === 'true' ? '已启用' : '已停用' }}
              </span>
            </div>
          </div>

          <!-- 卡片内容预览 -->
          <div class="p-5 flex-1 bg-white relative">
            <div class="text-sm text-gray-500 leading-relaxed line-clamp-4 font-mono bg-gray-50 p-3 rounded-lg border border-gray-100 min-h-[100px]">
               {{ prompt.content }}
            </div>
            
            <p v-if="prompt.description" class="mt-3 text-xs text-gray-400 line-clamp-1 flex items-center gap-1">
              <Info :size="12" />
              {{ prompt.description }}
            </p>
          </div>
          
          <!-- 底部数据 -->
          <div class="px-5 py-3 bg-gray-50/50 border-t border-gray-100 text-xs text-gray-400 flex justify-between items-center">
             <span class="flex items-center gap-1 font-mono">
                <FileText :size="12" /> {{ prompt.content?.length || 0 }} chars
             </span>
             <span class="font-mono text-[10px] opacity-50">ID: {{ prompt.id.substring(0, 8) }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- 编辑对话框 -->
    <el-dialog
      v-model="dialogVisible"
      :title="editingPrompt ? '编辑提示词' : '新建提示词'"
      width="800px"
      class="custom-dialog"
      destroy-on-close
      top="5vh"
    >
      <div class="px-2 max-h-[75vh] overflow-y-auto custom-scrollbar">
        <el-form :model="formData" label-position="top">
          <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
            <el-form-item label="名称" required>
              <el-input v-model="formData.name" placeholder="例如: 爆款微头条生成器" size="large" />
            </el-form-item>
            
            <div class="grid grid-cols-2 gap-4">
              <el-form-item label="类型">
                <el-select v-model="formData.type" placeholder="选择类型" style="width: 100%">
                  <el-option label="文章生成" value="generate" />
                  <el-option label="文章优化" value="humanize" />
                  <el-option label="图片生成" value="image" />
                </el-select>
              </el-form-item>
              <el-form-item label="适用内容">
                <el-select v-model="formData.content_type" placeholder="选择内容" style="width: 100%">
                  <el-option label="长文章" value="article" />
                  <el-option label="微头条" value="weitoutiao" />
                </el-select>
              </el-form-item>
            </div>
          </div>

          <el-form-item label="描述 (可选)">
            <el-input
              v-model="formData.description"
              placeholder="简要描述此提示词的用途和特点"
            />
          </el-form-item>
          
          <div class="flex items-center justify-between py-2">
            <label class="text-sm font-bold text-gray-700">提示词内容</label>
            <div class="flex items-center gap-4">
               <span class="text-xs text-gray-500">启用状态</span>
               <el-switch
                v-model="formData.is_active"
                active-value="true"
                inactive-value="false"
                inline-prompt
                active-text="开"
                inactive-text="关"
              />
            </div>
          </div>

          <!-- 格式提示 -->
          <div v-if="formData.type" class="mb-4 text-sm bg-blue-50 border border-blue-100 rounded-xl p-4">
            <div class="flex items-start gap-3">
               <Info :size="20" class="text-blue-500 mt-0.5 flex-shrink-0" />
               <div class="flex-1">
                 <h4 class="font-bold text-blue-800 mb-1">
                   {{ formData.type === 'generate' ? 'JSON 输出要求' : formData.type === 'image' ? '生图 JSON 格式' : '优化指令说明' }}
                 </h4>
                 
                 <template v-if="formData.type === 'generate'">
                    <p class="text-blue-600 text-xs mb-2">生成类提示词必须强制 AI 返回严格的 JSON 格式，否则系统无法解析。（image_prompts如果没有则会采用生图提示词在生图阶段重新生成，tags没有则发布文章不带tag）</p>
                    <div class="bg-white rounded-lg border border-blue-100 p-3 font-mono text-xs text-gray-600 relative group space-y-1">
                      <code class="block">{"title": "标题",</code>
                      <code class="block">&nbsp;"content": "正文(支持HTML)",</code>
                      <code class="block">&nbsp;"tags": ["标签1", "标签2"],</code>
                      <code class="block">&nbsp;"image_prompts": [{"description": "画面描述", "position": "cover"}]}</code>
                    </div>
                    <p class="text-blue-500 text-xs mt-2">
                      <strong>tags</strong>: 文章标签(最多5个)，发布时自动填入头条标签栏
                    </p>
                 </template>
                 
                 <template v-else-if="formData.type === 'image'">
                    <p class="text-purple-600 text-xs mb-2">生图提示词用于将文章内容转换为绘画指令。</p>
                    <div class="bg-white rounded-lg border border-purple-100 p-2 font-mono text-xs text-gray-600">
                      <code>{"prompts": [{"description": "画面描述", "position": "cover|end"}]}</code>
                    </div>
                 </template>
                 
                 <p v-else class="text-green-600 text-xs">优化类提示词应接收用户输入的内容，并返回修改后的纯文本，无需特定 JSON 格式。</p>
               </div>
            </div>
          </div>

          <el-form-item>
            <el-input
              v-model="formData.content"
              type="textarea"
              :rows="12"
              placeholder="在这里编写您的 Prompt..."
              class="font-mono text-sm leading-relaxed"
              resize="vertical"
            />
          </el-form-item>
        </el-form>
      </div>
      <template #footer>
        <div class="flex justify-between items-center">
           <div class="text-xs text-gray-400 flex items-center gap-1">
             支持使用 <code class="bg-gray-100 px-1 rounded font-mono text-gray-600" v-pre>{{ variable }}</code> 变量
           </div>
           <div class="flex gap-3">
            <el-button @click="dialogVisible = false" round>取消</el-button>
            <el-button type="primary" @click="savePrompt" round class="!px-6">保存提示词</el-button>
           </div>
        </div>
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
  Info
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
  if (!formData.value.name || !formData.value.content) {
    ElMessage.warning('名称和内容不能为空')
    return
  }
  
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
    await ElMessageBox.confirm('确定要删除这个提示词吗？此操作不可恢复。', '确认删除', {
      confirmButtonText: '删除',
      cancelButtonText: '取消',
      type: 'warning',
      confirmButtonClass: 'el-button--danger'
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
    generate: 'bg-gradient-to-br from-blue-500 to-indigo-600',
    humanize: 'bg-gradient-to-br from-emerald-500 to-green-600',
    image: 'bg-gradient-to-br from-purple-500 to-fuchsia-600',
  }
  return map[type] || 'bg-gray-500'
}

const getTypeClass = (type: string) => {
  const map: Record<string, string> = {
    generate: 'bg-blue-50 text-blue-600 border-blue-100',
    humanize: 'bg-emerald-50 text-emerald-600 border-emerald-100',
    image: 'bg-purple-50 text-purple-600 border-purple-100',
  }
  return map[type] || 'bg-gray-100 text-gray-600'
}

const getTypeText = (type: string) => {
  const map: Record<string, string> = {
    generate: '文章生成',
    humanize: '内容优化',
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

.custom-scrollbar::-webkit-scrollbar {
  width: 6px;
}
.custom-scrollbar::-webkit-scrollbar-track {
  background: transparent;
}
.custom-scrollbar::-webkit-scrollbar-thumb {
  background-color: #e5e7eb;
  border-radius: 20px;
}
</style>
