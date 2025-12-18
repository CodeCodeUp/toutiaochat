<template>
  <div class="accounts-page">
    <h2 class="page-title">账号管理</h2>

    <el-card class="toolbar">
      <el-row :gutter="20" align="middle">
        <el-col :span="16">
          <el-space>
            <el-button @click="loadAccounts">
              <el-icon><Refresh /></el-icon>
              刷新
            </el-button>
            <el-button type="success" @click="copyCookieScriptAndJump">
              <el-icon><DocumentCopy /></el-icon>
              获取Cookie脚本
            </el-button>
          </el-space>
        </el-col>
        <el-col :span="8" style="text-align: right">
          <el-button type="primary" @click="showAddDialog = true">
            <el-icon><Plus /></el-icon>
            添加账号
          </el-button>
        </el-col>
      </el-row>
    </el-card>

    <el-card>
      <el-table :data="accounts" v-loading="loading" style="width: 100%">
        <el-table-column prop="nickname" label="昵称" width="150" />
        <el-table-column prop="uid" label="UID" width="150" />
        <el-table-column prop="platform" label="平台" width="120" />
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.status === 'active' ? 'success' : 'danger'">
              {{ row.status === 'active' ? '正常' : '已过期' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="last_publish_at" label="最后发布" width="160">
          <template #default="{ row }">
            {{ row.last_publish_at ? formatDate(row.last_publish_at) : '-' }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="250">
          <template #default="{ row }">
            <el-space>
              <el-button size="small" @click="checkStatus(row)">检查状态</el-button>
              <el-button size="small" type="warning" @click="refreshCookie(row)">刷新Cookie</el-button>
              <el-button size="small" type="danger" @click="deleteAccount(row)">删除</el-button>
            </el-space>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 添加账号对话框 -->
    <el-dialog v-model="showAddDialog" title="添加账号" width="500px">
      <el-form :model="addForm" label-width="100px">
        <el-form-item label="昵称" required>
          <el-input v-model="addForm.nickname" placeholder="账号昵称" />
        </el-form-item>
        <el-form-item label="UID" required>
          <el-input v-model="addForm.uid" placeholder="头条号UID" />
        </el-form-item>
        <el-form-item label="平台">
          <el-select v-model="addForm.platform" style="width: 100%">
            <el-option label="头条号" value="头条号" />
            <el-option label="百家号" value="百家号" />
          </el-select>
        </el-form-item>
        <el-form-item label="Cookie" required>
          <el-input
            v-model="addForm.cookies"
            type="textarea"
            :rows="5"
            placeholder="粘贴登录后的Cookie (JSON格式)"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showAddDialog = false">取消</el-button>
        <el-button type="primary" :loading="adding" @click="addAccount">添加</el-button>
      </template>
    </el-dialog>

    <!-- 刷新Cookie对话框 -->
    <el-dialog v-model="showRefreshDialog" title="刷新Cookie" width="500px">
      <el-form label-width="100px">
        <el-form-item label="新Cookie">
          <el-input
            v-model="newCookie"
            type="textarea"
            :rows="5"
            placeholder="粘贴新的Cookie (JSON格式)"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showRefreshDialog = false">取消</el-button>
        <el-button type="primary" :loading="refreshing" @click="doRefreshCookie">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { accountApi } from '@/api'
import dayjs from 'dayjs'

const loading = ref(false)
const adding = ref(false)
const refreshing = ref(false)
const accounts = ref([])
const showAddDialog = ref(false)
const showRefreshDialog = ref(false)
const currentAccount = ref<any>(null)
const newCookie = ref('')

const addForm = reactive({
  nickname: '',
  uid: '',
  platform: '头条号',
  cookies: '',
})

const loadAccounts = async () => {
  loading.value = true
  try {
    const res: any = await accountApi.list()
    accounts.value = res.items || []
  } catch (e) {
    console.error(e)
  } finally {
    loading.value = false
  }
}

const addAccount = async () => {
  if (!addForm.nickname || !addForm.uid || !addForm.cookies) {
    ElMessage.warning('请填写完整信息')
    return
  }

  adding.value = true
  try {
    await accountApi.create(addForm)
    ElMessage.success('添加成功')
    showAddDialog.value = false
    Object.assign(addForm, { nickname: '', uid: '', platform: '头条号', cookies: '' })
    loadAccounts()
  } catch (e) {
    console.error(e)
  } finally {
    adding.value = false
  }
}

const checkStatus = async (row: any) => {
  try {
    const res: any = await accountApi.checkStatus(row.id)
    if (res.is_valid) {
      ElMessage.success('账号状态正常')
    } else {
      ElMessage.warning(`账号异常: ${res.message}`)
    }
    loadAccounts()
  } catch (e) {
    console.error(e)
  }
}

const refreshCookie = (row: any) => {
  currentAccount.value = row
  newCookie.value = ''
  showRefreshDialog.value = true
}

const doRefreshCookie = async () => {
  if (!newCookie.value) {
    ElMessage.warning('请输入新Cookie')
    return
  }

  refreshing.value = true
  try {
    await accountApi.refresh(currentAccount.value.id, newCookie.value)
    ElMessage.success('Cookie已更新')
    showRefreshDialog.value = false
    loadAccounts()
  } catch (e) {
    console.error(e)
  } finally {
    refreshing.value = false
  }
}

const deleteAccount = async (row: any) => {
  await ElMessageBox.confirm('确定要删除这个账号吗？', '确认删除', { type: 'warning' })
  await accountApi.delete(row.id)
  ElMessage.success('删除成功')
  loadAccounts()
}

const formatDate = (date: string) => dayjs(date).format('YYYY-MM-DD HH:mm')

/**
 * 复制获取Cookie的脚本并跳转到头条
 */
const copyCookieScriptAndJump = async () => {
  // 获取Cookie的JavaScript脚本
  const cookieScript = `// ========================================
// 头条Cookie获取脚本
// 使用说明: 在控制台粘贴此脚本并回车执行
// ========================================

(async function() {
  console.clear();
  console.log('%c[Cookie获取脚本] 开始执行...', 'color: #67C23A; font-size: 14px; font-weight: bold;');

  // 兼容性更好的复制函数
  function copyToClipboard(text) {
    // 方法1: 尝试使用 Clipboard API
    if (navigator.clipboard && navigator.clipboard.writeText) {
      return navigator.clipboard.writeText(text)
        .then(() => true)
        .catch(() => false);
    }

    // 方法2: 使用传统的 execCommand 方法
    return new Promise((resolve) => {
      const textarea = document.createElement('textarea');
      textarea.value = text;
      textarea.style.position = 'fixed';
      textarea.style.top = '0';
      textarea.style.left = '0';
      textarea.style.width = '1px';
      textarea.style.height = '1px';
      textarea.style.opacity = '0';
      document.body.appendChild(textarea);
      textarea.focus();
      textarea.select();

      try {
        const success = document.execCommand('copy');
        document.body.removeChild(textarea);
        resolve(success);
      } catch (err) {
        document.body.removeChild(textarea);
        resolve(false);
      }
    });
  }

  try {
    // 获取所有Cookie
    const cookies = document.cookie.split('; ').map(cookieStr => {
      const [name, ...valueParts] = cookieStr.split('=');
      const value = valueParts.join('=');
      return {
        name: name,
        value: value,
        domain: '.toutiao.com',
        path: '/',
        secure: true,
        httpOnly: false
      };
    });

    if (cookies.length === 0 || !cookies[0].name) {
      console.error('%c[Cookie获取失败] 未检测到Cookie,请确保已登录头条号!', 'color: #F56C6C; font-size: 14px;');
      alert('❌ 未检测到Cookie\\n\\n请确保:\\n1. 已登录头条号\\n2. 在头条页面执行此脚本');
      return '执行失败: 未检测到Cookie';
    }

    console.log(\`%c[成功] 检测到 \${cookies.length} 个Cookie\`, 'color: #67C23A; font-size: 13px;');

    // 格式化为JSON
    const cookiesJson = JSON.stringify(cookies, null, 2);

    // 复制到剪贴板
    const copySuccess = await copyToClipboard(cookiesJson);

    if (copySuccess) {
      console.log('%c[成功] Cookie已复制到剪贴板!', 'color: #67C23A; font-size: 14px; font-weight: bold;');
      console.log('%c返回系统粘贴到"添加账号"或"刷新Cookie"对话框中', 'color: #409EFF; font-size: 12px;');
      alert('✅ Cookie已复制到剪贴板!\\n\\n请返回系统粘贴到:\\n• "添加账号" 对话框\\n• "刷新Cookie" 对话框');
      return \`✅ 成功获取 \${cookies.length} 个Cookie,已自动复制到剪贴板\`;
    } else {
      // 备用方案：显示在控制台
      console.error('%c[复制失败] 请手动复制下方数据', 'color: #E6A23C; font-size: 14px;');
      console.log('%c=== Cookie数据开始 ===', 'color: #409EFF; font-size: 12px;');
      console.log(cookiesJson);
      console.log('%c=== Cookie数据结束 ===', 'color: #409EFF; font-size: 12px;');

      // 选中控制台中的文本提示
      prompt('⚠️ 自动复制失败，请手动复制下方数据 (Ctrl+C):', cookiesJson);
      return '⚠️ 自动复制失败，请从弹窗手动复制';
    }
  } catch (error) {
    console.error('%c[错误] 脚本执行失败:', 'color: #F56C6C; font-size: 14px;', error);
    alert('❌ 脚本执行失败\\n\\n错误: ' + error.message);
    return '执行失败: ' + error.message;
  }
})();`

  try {
    // 复制脚本到剪贴板
    await navigator.clipboard.writeText(cookieScript)

    ElMessage.success({
      message: '✅ 脚本已复制! 即将跳转到头条,请登录后按F12打开控制台粘贴执行',
      duration: 5000
    })

    // 1秒后跳转
    setTimeout(() => {
      window.open('https://mp.toutiao.com/profile_v4/graphic/publish', '_blank')
    }, 1000)
  } catch (err) {
    ElMessage.error('复制失败,请手动复制脚本')
    console.error('复制失败:', err)
  }
}

onMounted(loadAccounts)
</script>

<style lang="scss" scoped>
.accounts-page {
  .page-title {
    margin-bottom: 20px;
    font-size: 20px;
    color: #303133;
  }

  .toolbar {
    margin-bottom: 20px;
  }
}
</style>
