<template>
  <div class="accounts-redesign">
    <!-- 页面标题 -->
    <header class="mb-10">
      <h1 class="text-4xl font-extrabold tracking-tight text-deep-black">
        账号管理
      </h1>
      <p class="mt-2 text-sm text-gray-500">
        管理发布账号和 Cookie 配置
      </p>
    </header>

    <!-- 工具栏 -->
    <div class="glass-container p-6 mb-8 flex items-center justify-between">
      <div class="flex items-center gap-4">
        <button class="btn-secondary flex items-center gap-2" @click="loadAccounts">
          <RefreshCw :size="18" :stroke-width="2" />
          刷新
        </button>

        <button class="btn-secondary flex items-center gap-2" @click="copyCookieScriptAndJump">
          <Code :size="18" :stroke-width="2" />
          获取Cookie脚本
        </button>
      </div>

      <button class="btn-primary flex items-center gap-2" @click="showAddDialog = true">
        <Plus :size="20" :stroke-width="2" />
        添加账号
      </button>
    </div>

    <!-- 账号列表 -->
    <div class="glass-container p-8">
      <div v-if="loading" class="text-center py-12">
        <div class="animate-spin w-8 h-8 border-4 border-gray-200 border-t-deep-black rounded-full mx-auto"></div>
        <p class="mt-4 text-gray-500">加载中...</p>
      </div>

      <div v-else-if="accounts.length === 0" class="text-center py-12 text-gray-400">
        <Users :size="48" :stroke-width="1.5" class="mx-auto mb-3 opacity-50" />
        <p>暂无账号</p>
      </div>

      <div v-else class="space-y-3">
        <div
          v-for="account in accounts"
          :key="account.id"
          class="glass-card p-6 flex items-start gap-6 group"
        >
          <!-- 账号头像 -->
          <div class="w-12 h-12 rounded-2xl bg-gradient-to-br from-green-500 to-emerald-600 flex items-center justify-center flex-shrink-0">
            <User :size="24" :stroke-width="2" class="text-white" />
          </div>

          <!-- 账号信息 -->
          <div class="flex-1 min-w-0">
            <h3 class="text-lg font-bold text-deep-black mb-2">
              {{ account.nickname }}
            </h3>

            <div class="flex items-center gap-4 text-sm text-gray-500 mb-2">
              <span class="flex items-center gap-1">
                <Hash :size="14" />
                UID: {{ account.uid }}
              </span>
              <span class="flex items-center gap-1">
                <Globe :size="14" />
                {{ account.platform }}
              </span>
            </div>

            <div v-if="account.last_publish_at" class="flex items-center gap-1 text-xs text-gray-400">
              <Clock :size="12" />
              最后发布: {{ formatDate(account.last_publish_at) }}
            </div>
          </div>

          <!-- 状态和操作 -->
          <div class="flex items-center gap-3 flex-shrink-0">
            <span
              class="px-3 py-1 rounded-lg text-xs font-bold uppercase tracking-wider"
              :class="account.status === 'active' ? 'bg-green-100 text-green-600' : 'bg-red-100 text-red-600'"
            >
              {{ account.status === 'active' ? '正常' : '已过期' }}
            </span>

            <el-dropdown trigger="click">
              <button class="w-8 h-8 rounded-lg hover:bg-gray-100/50 flex items-center justify-center transition">
                <MoreVertical :size="18" :stroke-width="2" class="text-gray-500" />
              </button>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item @click="checkStatus(account)">检查状态</el-dropdown-item>
                  <el-dropdown-item @click="refreshCookie(account)">刷新Cookie</el-dropdown-item>
                  <el-dropdown-item divided @click="deleteAccount(account)">删除</el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </div>
        </div>
      </div>
    </div>

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
          <el-select v-model="addForm.platform" style="width: 100%" disabled>
            <el-option label="头条号" value="头条号" />
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
import {
  Plus,
  RefreshCw,
  Code,
  Users,
  User,
  Hash,
  Globe,
  Clock,
  MoreVertical,
} from 'lucide-vue-next'

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

<style scoped>
.accounts-redesign {
  @apply animate-in;
}
</style>
