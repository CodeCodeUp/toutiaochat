<template>
  <div class="prompts-page">
    <div class="page-header">
      <h2>提示词管理</h2>
      <el-button type="primary" @click="showCreateDialog">
        <el-icon><Plus /></el-icon>
        新建提示词
      </el-button>
    </div>

    <!-- 提示词列表 -->
    <el-table :data="prompts" border style="width: 100%">
      <el-table-column prop="name" label="名称" width="200" />
      <el-table-column prop="type" label="类型" width="120">
        <template #default="{ row }">
          <el-tag v-if="row.type === 'generate'" type="primary">文章生成</el-tag>
          <el-tag v-else-if="row.type === 'humanize'" type="success">文章优化</el-tag>
          <el-tag v-else-if="row.type === 'image'" type="warning">图片生成</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="description" label="描述" show-overflow-tooltip />
      <el-table-column prop="is_active" label="状态" width="100">
        <template #default="{ row }">
          <el-tag v-if="row.is_active === 'true'" type="success">已启用</el-tag>
          <el-tag v-else type="info">未启用</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="200" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" @click="editPrompt(row)">编辑</el-button>
          <el-button link type="danger" @click="deletePrompt(row.id)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

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
          <el-select v-model="formData.type" placeholder="请选择类型">
            <el-option label="文章生成" value="generate" />
            <el-option label="文章优化" value="humanize" />
            <el-option label="图片生成" value="image" />
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

const prompts = ref<any[]>([])
const dialogVisible = ref(false)
const editingPrompt = ref<any>(null)
const formData = ref({
  name: '',
  type: 'generate',
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

onMounted(() => {
  loadPrompts()
})
</script>

<style scoped lang="scss">
.prompts-page {
  .page-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 20px;

    h2 {
      margin: 0;
      font-size: 24px;
      font-weight: 500;
    }
  }
}
</style>
