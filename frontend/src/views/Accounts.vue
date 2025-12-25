<template>
  <div class="accounts-redesign max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
    <!-- 页面标题 -->
    <header class="mb-10 flex flex-col md:flex-row md:items-center md:justify-between gap-4">
      <div>
        <h1 class="text-4xl font-extrabold tracking-tight text-deep-black">
          账号管理
        </h1>
        <p class="mt-2 text-sm text-gray-500 font-medium">
          管理发布渠道授权与状态
        </p>
      </div>
      <div class="flex items-center gap-3">
        <button class="btn-secondary flex items-center gap-2" @click="copyCookieScriptAndJump">
          <Code :size="18" :stroke-width="2" class="text-blue-500" />
          <span class="hidden sm:inline">获取 Cookie 脚本</span>
          <span class="sm:hidden">脚本</span>
        </button>
        <button class="btn-primary flex items-center gap-2 shadow-lg shadow-deep-black/20" @click="showAddDialog = true">
          <Plus :size="20" :stroke-width="2" />
          添加账号
        </button>
      </div>
    </header>

    <!-- 账号列表 -->
    <div>
      <div v-if="loading && accounts.length === 0" class="text-center py-20">
        <div class="animate-spin w-10 h-10 border-4 border-gray-100 border-t-deep-black rounded-full mx-auto"></div>
        <p class="mt-4 text-gray-400 font-medium">正在加载账号信息...</p>
      </div>

      <div v-else-if="accounts.length === 0" class="glass-container p-16 text-center border-dashed border-2 border-gray-200">
        <div class="w-20 h-20 bg-gray-50 rounded-full flex items-center justify-center mx-auto mb-6">
          <Users :size="40" class="text-gray-300" />
        </div>
        <h3 class="text-lg font-bold text-gray-900 mb-2">暂无已授权账号</h3>
        <p class="text-gray-500 max-w-sm mx-auto mb-8">
          添加头条号等平台账号，开始自动发布内容。
        </p>
        <button class="btn-primary" @click="showAddDialog = true">
          <Plus :size="18" class="mr-2 inline-block" />
          立即添加
        </button>
      </div>

      <div v-else class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        <transition-group name="list">
          <div
            v-for="account in accounts"
            :key="account.id"
            class="glass-card relative overflow-hidden group hover:-translate-y-1 hover:shadow-xl transition-all duration-300"
            :class="account.status === 'active' ? 'border-gray-100' : 'border-red-100 bg-red-50/10'"
          >
            <!-- 顶部装饰条 -->
            <div class="h-1.5 w-full absolute top-0 left-0" 
                 :class="account.status === 'active' ? 'bg-gradient-to-r from-green-400 to-emerald-500' : 'bg-gradient-to-r from-red-400 to-red-500'">
            </div>

            <div class="p-6">
              <div class="flex items-start justify-between mb-4">
                <!-- 头像/Logo -->
                <div class="w-16 h-16 rounded-2xl bg-gradient-to-br from-gray-100 to-gray-200 p-1 shadow-inner">
                  <div class="w-full h-full rounded-xl bg-white flex items-center justify-center text-2xl font-bold text-gray-700">
                     {{ (account.nickname || 'U').charAt(0).toUpperCase() }}
                  </div>
                </div>
                
                <!-- 操作菜单 -->
                <el-dropdown trigger="click">
                  <button class="p-2 rounded-lg hover:bg-gray-100 transition-colors text-gray-400">
                    <MoreVertical :size="20" />
                  </button>
                  <template #dropdown>
                    <el-dropdown-menu class="!rounded-xl !p-1.5">
                      <el-dropdown-item @click="checkStatus(account)" class="!rounded-lg">
                        <div class="flex items-center gap-2"><Activity :size="14"/> 检查状态</div>
                      </el-dropdown-item>
                      <el-dropdown-item @click="refreshCookie(account)" class="!rounded-lg">
                        <div class="flex items-center gap-2"><RefreshCw :size="14"/> 更新 Cookie</div>
                      </el-dropdown-item>
                      <el-dropdown-item divided @click="deleteAccount(account)" class="!rounded-lg !text-red-500 hover:!bg-red-50">
                        <div class="flex items-center gap-2"><Trash2 :size="14"/> 删除账号</div>
                      </el-dropdown-item>
                    </el-dropdown-menu>
                  </template>
                </el-dropdown>
              </div>

              <!-- 主要信息 -->
              <h3 class="text-xl font-bold text-deep-black mb-1 truncate" :title="account.nickname">
                {{ account.nickname }}
              </h3>
              <div class="flex items-center gap-2 text-xs text-gray-500 font-mono mb-4">
                <span class="px-1.5 py-0.5 bg-gray-100 rounded text-gray-600">{{ account.platform }}</span>
                <span class="truncate">UID: {{ account.uid }}</span>
              </div>

              <!-- 状态和统计 -->
              <div class="flex items-center justify-between pt-4 border-t border-gray-100">
                <div class="flex flex-col">
                  <span class="text-[10px] uppercase tracking-wider text-gray-400 font-bold mb-0.5">状态</span>
                  <div class="flex items-center gap-1.5">
                    <div class="w-2 h-2 rounded-full" :class="account.status === 'active' ? 'bg-green-500' : 'bg-red-500'"></div>
                    <span class="text-sm font-medium" :class="account.status === 'active' ? 'text-green-600' : 'text-red-600'">
                      {{ account.status === 'active' ? '运行正常' : '需要更新' }}
                    </span>
                  </div>
                </div>

                <div class="flex flex-col items-end" v-if="account.last_publish_at">
                  <span class="text-[10px] uppercase tracking-wider text-gray-400 font-bold mb-0.5">上次发布</span>
                  <span class="text-xs text-gray-600">{{ formatDate(account.last_publish_at) }}</span>
                </div>
              </div>
            </div>
            
            <!-- 过期提示遮罩 -->
            <div v-if="account.status !== 'active'" class="absolute inset-0 bg-white/60 backdrop-blur-[1px] flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none">
                <div class="bg-red-500 text-white px-4 py-2 rounded-full text-sm font-bold shadow-lg transform translate-y-4 group-hover:translate-y-0 transition-transform">
                  Cookie 已过期
                </div>
            </div>
          </div>
        </transition-group>
      </div>
    </div>

    <!-- 添加账号对话框 -->
    <el-dialog 
      v-model="showAddDialog" 
      title="添加新账号" 
      width="500px"
      class="custom-dialog"
    >
      <div class="px-2">
        <el-alert
          title="需要获取 Cookie"
          type="info"
          :closable="false"
          show-icon
          class="!mb-6 !rounded-xl"
        >
          <template #default>
            请使用页面顶部的"获取 Cookie 脚本"工具来提取您的账号凭证。
          </template>
        </el-alert>

        <el-form :model="addForm" label-position="top">
          <div class="grid grid-cols-2 gap-4">
            <el-form-item label="账号昵称" required>
              <el-input v-model="addForm.nickname" placeholder="例如: 科技观察者" />
            </el-form-item>
            <el-form-item label="平台 UID" required>
              <el-input v-model="addForm.uid" placeholder="头条号数字ID" />
            </el-form-item>
          </div>
          
          <el-form-item label="目标平台">
            <div class="w-full p-3 bg-gray-50 border border-gray-200 rounded-xl flex items-center gap-3">
               <div class="w-8 h-8 bg-red-500 rounded-full flex items-center justify-center text-white font-bold text-xs">T</div>
               <div class="font-medium text-gray-700">今日头条 (头条号)</div>
            </div>
          </el-form-item>

          <el-form-item label="Cookie 凭证" required>
            <el-input
              v-model="addForm.cookies"
              type="textarea"
              :rows="6"
              placeholder='[{"name": "...", "value": "..."}]'
              class="font-mono text-xs"
              resize="none"
            />
          </el-form-item>
        </el-form>
      </div>
      <template #footer>
        <div class="flex justify-end gap-3">
           <el-button @click="showAddDialog = false" round>取消</el-button>
           <el-button type="primary" :loading="adding" @click="addAccount" round class="!px-6">确认添加</el-button>
        </div>
      </template>
    </el-dialog>

    <!-- 刷新Cookie对话框 -->
    <el-dialog 
      v-model="showRefreshDialog" 
      title="更新 Cookie" 
      width="500px"
      class="custom-dialog"
    >
      <div class="px-2">
        <div class="flex items-center gap-3 mb-6 p-4 bg-blue-50 text-blue-700 rounded-xl border border-blue-100">
          <RefreshCw :size="20" />
          <div class="text-sm">
            正在为 <strong>{{ currentAccount?.nickname }}</strong> 更新凭证
          </div>
        </div>

        <el-form label-position="top">
          <el-form-item label="新 Cookie 内容">
            <el-input
              v-model="newCookie"
              type="textarea"
              :rows="6"
              placeholder="粘贴最新的 Cookie JSON..."
              class="font-mono text-xs"
              resize="none"
            />
          </el-form-item>
        </el-form>
      </div>
      <template #footer>
        <div class="flex justify-end gap-3">
          <el-button @click="showRefreshDialog = false" round>取消</el-button>
          <el-button type="primary" :loading="refreshing" @click="doRefreshCookie" round class="!px-6">保存更新</el-button>
        </div>
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
  Activity,
  Trash2,
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
  await ElMessageBox.confirm('确定要删除这个账号吗？', '确认删除', { 
    type: 'warning',
    confirmButtonText: '删除',
    cancelButtonText: '取消',
    confirmButtonClass: 'el-button--danger'
  })
  try {
    await accountApi.delete(row.id)
    ElMessage.success('删除成功')
    loadAccounts()
  } catch (e) {
    console.error(e)
  }
}

const formatDate = (date: string) => dayjs(date).format('YYYY-MM-DD')

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

.list-enter-active,
.list-leave-active {
  transition: all 0.5s ease;
}
.list-enter-from,
.list-leave-to {
  opacity: 0;
  transform: translateY(20px);
}
</style>
