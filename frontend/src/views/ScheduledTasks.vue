<template>
  <div class="scheduled-tasks max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
    <!-- 页面标题 -->
    <header class="mb-10 flex flex-col md:flex-row md:items-center md:justify-between gap-4">
      <div>
        <h1 class="text-4xl font-extrabold tracking-tight text-deep-black">
          定时任务
        </h1>
        <p class="mt-2 text-sm text-gray-500 font-medium">
          自动化内容生成与发布流水线
        </p>
      </div>
      <div class="flex items-center gap-3">
        <button class="btn-secondary flex items-center gap-2" @click="loadData">
          <RefreshCw :size="18" :stroke-width="2" :class="{ 'animate-spin': loading }" />
          刷新状态
        </button>
        <button class="btn-primary flex items-center gap-2 shadow-lg shadow-deep-black/20" @click="openCreateDialog">
          <Plus :size="20" :stroke-width="2" />
          新建任务
        </button>
      </div>
    </header>

    <!-- 调度器状态概览 -->
    <div class="grid grid-cols-1 md:grid-cols-3 gap-6 mb-10">
      <!-- 运行状态 -->
      <div class="glass-card p-5 flex items-center justify-between relative overflow-hidden group">
        <div class="relative z-10">
          <p class="text-xs font-bold text-gray-400 uppercase tracking-wider mb-1">调度器状态</p>
          <div class="flex items-center gap-2">
            <div
              class="w-3 h-3 rounded-full shadow-sm transition-all duration-500"
              :class="schedulerStatus.running ? 'bg-green-500 shadow-green-500/50' : 'bg-red-400'"
            ></div>
            <span class="text-xl font-bold text-deep-black">
              {{ schedulerStatus.running ? '运行中' : '已停止' }}
            </span>
          </div>
        </div>
        <div class="relative z-10">
          <button
            v-if="schedulerStatus.running"
            class="w-10 h-10 rounded-xl bg-red-50 text-red-500 flex items-center justify-center hover:bg-red-100 transition-colors"
            @click="pauseScheduler"
            title="暂停所有任务"
          >
            <Pause :size="20" :stroke-width="2.5" />
          </button>
          <button
            v-else
            class="w-10 h-10 rounded-xl bg-green-50 text-green-500 flex items-center justify-center hover:bg-green-100 transition-colors"
            @click="resumeScheduler"
            title="恢复所有任务"
          >
            <Play :size="20" :stroke-width="2.5" />
          </button>
        </div>
        <!-- 背景装饰 -->
        <div class="absolute -right-6 -bottom-6 text-gray-50 opacity-10 transform rotate-12 group-hover:scale-110 transition-transform duration-500">
          <Activity :size="100" />
        </div>
      </div>

      <!-- 活跃任务 -->
      <div class="glass-card p-5 relative overflow-hidden group">
        <div class="relative z-10">
          <p class="text-xs font-bold text-gray-400 uppercase tracking-wider mb-1">活跃任务</p>
          <span class="text-3xl font-bold text-deep-black">{{ schedulerStatus.active_tasks }}</span>
          <span class="text-sm text-gray-400 ml-1">个</span>
        </div>
        <div class="absolute -right-6 -bottom-6 text-blue-50 opacity-10 transform rotate-12 group-hover:scale-110 transition-transform duration-500">
          <Zap :size="100" />
        </div>
      </div>

      <!-- 待执行作业 -->
      <div class="glass-card p-5 relative overflow-hidden group">
        <div class="relative z-10">
          <p class="text-xs font-bold text-gray-400 uppercase tracking-wider mb-1">待执行作业</p>
          <span class="text-3xl font-bold text-deep-black">{{ schedulerStatus.pending_jobs }}</span>
          <span class="text-sm text-gray-400 ml-1">个</span>
        </div>
        <div class="absolute -right-6 -bottom-6 text-purple-50 opacity-10 transform rotate-12 group-hover:scale-110 transition-transform duration-500">
          <Clock :size="100" />
        </div>
      </div>
    </div>

    <!-- 任务列表 -->
    <div class="space-y-6">
      <div v-if="loading && tasks.length === 0" class="text-center py-20">
        <div class="animate-spin w-10 h-10 border-4 border-gray-100 border-t-deep-black rounded-full mx-auto"></div>
        <p class="mt-4 text-gray-400 font-medium">正在加载任务配置...</p>
      </div>

      <div v-else-if="tasks.length === 0" class="glass-container p-16 text-center border-dashed border-2 border-gray-200">
        <div class="w-20 h-20 bg-gray-50 rounded-full flex items-center justify-center mx-auto mb-6">
          <Calendar :size="40" class="text-gray-300" />
        </div>
        <h3 class="text-lg font-bold text-gray-900 mb-2">暂无定时任务</h3>
        <p class="text-gray-500 max-w-sm mx-auto mb-8">
          创建一个定时任务来自动生成内容或发布文章。
        </p>
        <button class="btn-primary" @click="openCreateDialog">
          <Plus :size="18" class="mr-2 inline-block" />
          创建第一个任务
        </button>
      </div>

      <transition-group name="list" tag="div" class="space-y-4">
        <div
          v-for="task in tasks"
          :key="task.id"
          class="glass-card p-6 flex items-start gap-6 group transition-all duration-300 hover:shadow-lg hover:border-blue-100/50"
          :class="{ 'opacity-60 grayscale-[0.5]': !task.is_active }"
        >
          <!-- 任务图标 -->
          <div
            class="w-16 h-16 rounded-2xl flex items-center justify-center flex-shrink-0 shadow-inner relative overflow-hidden"
            :class="getTaskTypeStyle(task.type)"
          >
            <component :is="getTaskTypeIcon(task.type)" :size="32" :stroke-width="1.5" class="text-white relative z-10" />
            <div class="absolute inset-0 bg-white/10 opacity-0 group-hover:opacity-100 transition-opacity"></div>
          </div>

          <!-- 任务信息 -->
          <div class="flex-1 min-w-0 py-1">
            <div class="flex items-center gap-3 mb-3">
              <h3 class="text-xl font-bold text-deep-black tracking-tight">
                {{ task.name }}
              </h3>
              <div class="flex items-center gap-2">
                <span
                  class="px-2.5 py-0.5 rounded-md text-xs font-bold uppercase tracking-wider border"
                  :class="task.content_type === 'ARTICLE' 
                    ? 'bg-blue-50 text-blue-600 border-blue-100' 
                    : 'bg-purple-50 text-purple-600 border-purple-100'"
                >
                  {{ task.content_type === 'ARTICLE' ? '文章' : '微头条' }}
                </span>
                <span v-if="!task.is_active" class="px-2.5 py-0.5 rounded-md text-xs font-bold uppercase tracking-wider bg-gray-100 text-gray-500 border border-gray-200">
                  已暂停
                </span>
              </div>
            </div>

            <!-- 任务详情网格 -->
            <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-y-2 gap-x-8 text-sm text-gray-600">
              <div class="flex items-center gap-2">
                <Clock :size="15" class="text-gray-400" />
                <span class="font-medium">频率:</span>
                <span>{{ formatSchedule(task) }}</span>
              </div>
              
              <div v-if="task.active_start_hour !== 0 || task.active_end_hour !== 24" class="flex items-center gap-2">
                <Sun :size="15" class="text-gray-400" />
                <span class="font-medium">时段:</span>
                <span>{{ task.active_start_hour }}:00 - {{ task.active_end_hour }}:00</span>
              </div>

              <div class="flex items-center gap-2">
                <Hash :size="15" class="text-gray-400" />
                <span class="font-medium">已执行:</span>
                <span>{{ task.run_count }} 次</span>
              </div>

              <div class="flex items-center gap-2" v-if="task.next_run_at">
                <Timer :size="15" class="text-blue-400" />
                <span class="font-medium text-blue-600">下次:</span>
                <span class="text-blue-600">{{ formatDate(task.next_run_at) }}</span>
              </div>
            </div>

            <!-- 错误提示 -->
            <div v-if="task.last_error" class="mt-4 bg-red-50 border border-red-100 rounded-lg p-3 flex items-start gap-3">
              <AlertCircle :size="16" class="text-red-500 mt-0.5 flex-shrink-0" />
              <div class="text-xs text-red-600 break-all leading-relaxed">
                <span class="font-bold">上次执行失败:</span> {{ task.last_error }}
              </div>
            </div>
          </div>

          <!-- 状态和操作 -->
          <div class="flex flex-col items-end gap-3 flex-shrink-0 py-1 pl-4 border-l border-gray-100/50">
            <el-switch
              v-model="task.is_active"
              @change="toggleTask(task)"
              :loading="task._toggling"
              style="--el-switch-on-color: #10B981;"
            />

            <el-dropdown trigger="click" placement="bottom-end">
              <button class="w-9 h-9 rounded-xl hover:bg-gray-100 flex items-center justify-center transition-colors text-gray-400 hover:text-gray-600">
                <MoreVertical :size="20" />
              </button>
              <template #dropdown>
                <el-dropdown-menu class="!p-1.5 !rounded-xl !border-gray-100 !shadow-xl">
                  <el-dropdown-item @click="triggerTask(task)" class="!rounded-lg !mb-0.5">
                    <div class="flex items-center gap-2 text-deep-black">
                      <Play :size="14" /> 立即执行
                    </div>
                  </el-dropdown-item>
                  <el-dropdown-item @click="openEditDialog(task)" class="!rounded-lg !mb-0.5">
                    <div class="flex items-center gap-2 text-deep-black">
                      <Edit :size="14" /> 编辑任务
                    </div>
                  </el-dropdown-item>
                  <el-dropdown-item @click="viewLogs(task)" class="!rounded-lg !mb-0.5">
                    <div class="flex items-center gap-2 text-deep-black">
                      <FileText :size="14" /> 查看日志
                    </div>
                  </el-dropdown-item>
                  <div class="h-px bg-gray-100 my-1 mx-2"></div>
                  <el-dropdown-item @click="deleteTask(task)" class="!rounded-lg !text-red-500 hover:!bg-red-50">
                    <div class="flex items-center gap-2">
                      <Trash2 :size="14" /> 删除任务
                    </div>
                  </el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </div>
        </div>
      </transition-group>
    </div>

    <!-- 创建/编辑对话框 -->
    <el-dialog
      v-model="showFormDialog"
      :title="editingTask ? '编辑任务' : '新建任务'"
      width="720px"
      destroy-on-close
      class="custom-dialog"
      :close-on-click-modal="false"
    >
      <el-form :model="form" label-position="top" class="custom-form px-2">
        <!-- 步骤 1: 任务类型 -->
        <div class="mb-8">
          <label class="block text-sm font-bold text-gray-700 mb-3 uppercase tracking-wide">1. 选择任务类型</label>
          <div class="grid grid-cols-3 gap-4">
            <div 
              v-for="type in [
                { val: 'GENERATE', label: '仅生成', icon: FileEdit, desc: '只生成内容草稿' },
                { val: 'PUBLISH', label: '仅发布', icon: Send, desc: '发布现有草稿' },
                { val: 'GENERATE_AND_PUBLISH', label: '生成并发布', icon: Zap, desc: '全自动流水线' }
              ]"
              :key="type.val"
              class="cursor-pointer border-2 rounded-xl p-4 transition-all duration-200 hover:border-blue-200 hover:bg-blue-50/30 flex flex-col items-center text-center gap-2"
              :class="form.type === type.val ? 'border-blue-500 bg-blue-50/50 ring-2 ring-blue-100 ring-offset-2' : 'border-gray-100 bg-white'"
              @click="form.type = type.val"
            >
              <div class="w-10 h-10 rounded-full flex items-center justify-center mb-1 transition-colors"
                :class="form.type === type.val ? 'bg-blue-500 text-white' : 'bg-gray-100 text-gray-400'">
                <component :is="type.icon" :size="20" />
              </div>
              <div class="font-bold text-sm text-deep-black">{{ type.label }}</div>
              <div class="text-xs text-gray-400">{{ type.desc }}</div>
            </div>
          </div>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
          <el-form-item label="任务名称" required>
            <el-input v-model="form.name" placeholder="给任务起个名字，如: 每日财经微头条" class="!w-full" size="large" />
          </el-form-item>

          <el-form-item label="内容类型" required>
            <div class="flex bg-gray-100 p-1 rounded-lg w-full">
              <button 
                type="button"
                v-for="ct in [{val: 'ARTICLE', label: '长文章'}, {val: 'WEITOUTIAO', label: '微头条'}]"
                :key="ct.val"
                class="flex-1 py-2 text-sm font-medium rounded-md transition-all duration-200"
                :class="form.content_type === ct.val ? 'bg-white text-deep-black shadow-sm' : 'text-gray-500 hover:text-gray-700'"
                @click="form.content_type = ct.val"
              >
                {{ ct.label }}
              </button>
            </div>
          </el-form-item>
        </div>

        <!-- 调度配置 -->
        <div class="bg-gray-50/50 rounded-2xl p-6 mb-8 border border-gray-100">
          <label class="block text-sm font-bold text-gray-700 mb-4 uppercase tracking-wide flex items-center gap-2">
            <Clock :size="16" /> 2. 调度配置
          </label>

          <el-form-item label="触发模式">
            <div class="grid grid-cols-3 gap-3 w-full mb-4">
               <div 
                v-for="mode in [
                  { val: 'RANDOM_INTERVAL', label: '随机间隔', desc: '模拟人工操作' },
                  { val: 'INTERVAL', label: '固定间隔', desc: '每隔X分钟' },
                  { val: 'CRON', label: '定时计划', desc: '每天固定时间' }
                ]"
                :key="mode.val"
                class="cursor-pointer border rounded-lg p-3 text-center transition-all"
                :class="form.schedule_mode === mode.val ? 'border-blue-500 bg-white shadow-sm' : 'border-gray-200 hover:border-gray-300 bg-transparent'"
                @click="form.schedule_mode = mode.val"
              >
                <div class="font-medium text-sm">{{ mode.label }}</div>
                <div class="text-[10px] text-gray-400 mt-0.5">{{ mode.desc }}</div>
              </div>
            </div>
          </el-form-item>

          <!-- 随机间隔配置 -->
          <div v-if="form.schedule_mode === 'RANDOM_INTERVAL'" class="animate-in">
             <el-form-item label="间隔范围 (分钟)">
              <div class="flex items-center gap-3">
                <el-input-number v-model="form.schedule_config.min_minutes" :min="1" :max="1440" controls-position="right" class="!w-32" />
                <span class="text-gray-400 font-bold">~</span>
                <el-input-number v-model="form.schedule_config.max_minutes" :min="1" :max="1440" controls-position="right" class="!w-32" />
              </div>
            </el-form-item>
          </div>

          <!-- 固定间隔配置 -->
          <div v-if="form.schedule_mode === 'INTERVAL'" class="animate-in">
            <el-form-item label="间隔时间 (分钟)">
              <el-input-number v-model="form.schedule_config.minutes" :min="1" :max="1440" controls-position="right" class="!w-full" />
            </el-form-item>
          </div>

          <!-- Cron配置 -->
          <div v-if="form.schedule_mode === 'CRON'" class="animate-in">
            <el-form-item label="Cron表达式">
              <el-input v-model="form.schedule_config.cron" placeholder="0 9 * * *" font-family="monospace" />
              <div class="text-xs text-gray-400 mt-1 flex gap-2">
                <span>常用:</span>
                <span class="cursor-pointer text-blue-500 hover:underline" @click="form.schedule_config.cron = '0 9 * * *'">每天9点</span>
                <span class="cursor-pointer text-blue-500 hover:underline" @click="form.schedule_config.cron = '0 */2 * * *'">每2小时</span>
              </div>
            </el-form-item>
          </div>

          <!-- 活跃时段 -->
          <div v-if="form.schedule_mode !== 'CRON'" class="mt-4 pt-4 border-t border-gray-200/60 animate-in">
             <el-form-item label="活跃时段限制">
              <div class="flex items-center gap-3">
                <div class="relative flex-1">
                  <span class="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 text-xs">从</span>
                  <el-input-number v-model="form.active_start_hour" :min="0" :max="23" controls-position="right" class="!w-full pl-8" />
                  <span class="absolute right-8 top-1/2 -translate-y-1/2 text-gray-400 text-xs">:00</span>
                </div>
                <span class="text-gray-300">-</span>
                <div class="relative flex-1">
                  <span class="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 text-xs">到</span>
                  <el-input-number v-model="form.active_end_hour" :min="1" :max="24" controls-position="right" class="!w-full pl-8" />
                  <span class="absolute right-8 top-1/2 -translate-y-1/2 text-gray-400 text-xs">:00</span>
                </div>
              </div>
            </el-form-item>
          </div>
        </div>

        <!-- 话题配置 (生成类型) -->
        <template v-if="form.type !== 'PUBLISH'">
          <div class="mb-8 animate-in">
            <label class="block text-sm font-bold text-gray-700 mb-4 uppercase tracking-wide flex items-center gap-2">
              <FileEdit :size="16" /> 3. 内容与话题
            </label>
            
            <el-tabs v-model="form.topic_mode" type="card" class="custom-tabs">
              <el-tab-pane label="AI 智能选题" name="RANDOM">
                <div class="text-sm text-gray-500 py-2">
                  AI 将根据账号定位和当前热点自动选择话题进行创作。无需配置。
                </div>
              </el-tab-pane>
              <el-tab-pane label="固定话题" name="FIXED">
                 <el-input v-model="topicInput" placeholder="请输入一个固定话题，每次都围绕此生成" size="large" />
              </el-tab-pane>
              <el-tab-pane label="话题库轮播" name="LIST">
                <div class="bg-gray-50 rounded-lg p-3 max-h-40 overflow-y-auto custom-scrollbar">
                  <div v-for="(topic, index) in form.topics" :key="index" class="flex items-center gap-2 mb-2">
                    <span class="text-xs text-gray-400 w-5 text-center">{{ index + 1 }}</span>
                    <el-input v-model="form.topics[index]" placeholder="输入话题" size="small" />
                    <button class="text-gray-400 hover:text-red-500 transition-colors" @click="form.topics.splice(index, 1)">
                      <Minus :size="16" />
                    </button>
                  </div>
                  <button class="w-full py-2 border-2 border-dashed border-gray-300 rounded-lg text-gray-400 text-sm hover:border-blue-400 hover:text-blue-500 transition-colors flex items-center justify-center gap-2" @click="form.topics.push('')">
                    <Plus :size="16" /> 添加话题
                  </button>
                </div>
              </el-tab-pane>
            </el-tabs>
          </div>
        </template>

        <!-- 发布配置 -->
        <template v-if="form.type !== 'GENERATE'">
          <div class="animate-in">
            <label class="block text-sm font-bold text-gray-700 mb-4 uppercase tracking-wide flex items-center gap-2">
              <Send :size="16" /> {{ form.type === 'PUBLISH' ? '2. 发布配置' : '4. 发布配置' }}
            </label>

            <el-form-item label="发布账号" required>
              <el-select v-model="form.account_id" placeholder="选择要发布的头条账号" size="large" class="!w-full">
                <el-option
                  v-for="account in accounts"
                  :key="account.id"
                  :label="account.nickname || account.username"
                  :value="account.id"
                >
                  <div class="flex items-center gap-2">
                     <span class="w-2 h-2 rounded-full" :class="account.platform === 'toutiao' ? 'bg-red-500' : 'bg-gray-400'"></span>
                     <span>{{ account.nickname || account.username }}</span>
                  </div>
                </el-option>
              </el-select>
            </el-form-item>

            <div v-if="form.type === 'PUBLISH'" class="bg-gray-50/50 p-4 rounded-xl border border-gray-100">
              <div class="grid grid-cols-2 gap-4">
                <el-form-item label="发布模式">
                  <el-select v-model="form.publish_mode" class="!w-full">
                    <el-option label="每次一篇" value="ONE" />
                    <el-option label="批量发布" value="BATCH" />
                    <el-option label="全部发布" value="ALL" />
                  </el-select>
                </el-form-item>

                <el-form-item v-if="form.publish_mode === 'BATCH'" label="单次数量">
                  <el-input-number v-model="form.publish_batch_size" :min="1" :max="10" class="!w-full" />
                </el-form-item>
                
                <el-form-item label="选取顺序">
                   <el-select v-model="form.publish_order" class="!w-full">
                    <el-option label="最早创建优先" value="oldest" />
                    <el-option label="最新创建优先" value="newest" />
                    <el-option label="随机选取" value="random" />
                  </el-select>
                </el-form-item>
              </div>
            </div>
          </div>
        </template>
      </el-form>

      <template #footer>
        <div class="flex items-center justify-between">
           <div class="text-xs text-gray-400">
             <span v-if="editingTask">正在编辑: {{ editingTask.name }}</span>
           </div>
           <div class="flex gap-3">
            <el-button @click="showFormDialog = false" round>取消</el-button>
            <el-button type="primary" :loading="saving" @click="saveTask" round class="!px-6">
              {{ editingTask ? '保存修改' : '立即创建' }}
            </el-button>
           </div>
        </div>
      </template>
    </el-dialog>

    <!-- 执行日志对话框 -->
    <el-dialog v-model="showLogsDialog" title="执行日志" width="800px" class="custom-dialog">
      <div v-if="logsLoading" class="text-center py-12">
        <div class="animate-spin w-8 h-8 border-4 border-gray-200 border-t-deep-black rounded-full mx-auto"></div>
        <p class="mt-4 text-gray-400">加载日志记录...</p>
      </div>
      <div v-else class="min-h-[400px]">
        <el-table :data="logs" stripe style="width: 100%" class="!bg-transparent">
          <el-table-column prop="started_at" label="执行时间" width="160">
            <template #default="{ row }">
              <div class="text-gray-900 font-medium">{{ formatDate(row.started_at).split(' ')[0] }}</div>
              <div class="text-xs text-gray-400">{{ formatDate(row.started_at).split(' ')[1] }}</div>
            </template>
          </el-table-column>
          <el-table-column prop="type" label="类型" width="100">
            <template #default="{ row }">
              <span class="text-xs font-medium text-gray-600">{{ formatTaskType(row.type) }}</span>
            </template>
          </el-table-column>
          <el-table-column prop="status" label="状态" width="100">
            <template #default="{ row }">
              <span
                class="px-2 py-1 rounded-full text-xs font-bold inline-flex items-center gap-1"
                :class="{
                  'bg-green-100 text-green-600': row.status === 'completed',
                  'bg-red-100 text-red-600': row.status === 'failed',
                  'bg-yellow-100 text-yellow-600': row.status === 'running',
                }"
              >
                <span class="w-1.5 h-1.5 rounded-full bg-current"></span>
                {{ formatStatus(row.status) }}
              </span>
            </template>
          </el-table-column>
          <el-table-column prop="error_message" label="信息">
             <template #default="{ row }">
               <span v-if="row.error_message" class="text-red-500 text-xs font-mono break-all">{{ row.error_message }}</span>
               <span v-else class="text-gray-400 text-xs italic">无异常</span>
             </template>
          </el-table-column>
        </el-table>
        <div class="mt-6 flex justify-center">
          <el-pagination
            v-model:current-page="logsPage"
            :page-size="10"
            :total="logsTotal"
            layout="prev, pager, next"
            @current-change="loadLogs"
            background
          />
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, computed, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  scheduledTaskApi,
  schedulerApi,
  accountApi,
  type ScheduledTask,
  type ScheduledTaskCreate,
  type SchedulerStatus,
} from '@/api'
import dayjs from 'dayjs'
import {
  Plus,
  Minus,
  RefreshCw,
  Calendar,
  Clock,
  Sun,
  Hash,
  Timer,
  History,
  AlertCircle,
  MoreVertical,
  Play,
  Pause,
  Edit,
  FileText,
  Trash2,
  FileEdit,
  Send,
  Zap,
  Activity
} from 'lucide-vue-next'

const loading = ref(false)
const saving = ref(false)
const tasks = ref<(ScheduledTask & { _toggling?: boolean })[]>([])
const accounts = ref<any[]>([])
const schedulerStatus = ref<SchedulerStatus>({
  running: false,
  active_tasks: 0,
  pending_jobs: 0,
})

// 表单相关
const showFormDialog = ref(false)
const editingTask = ref<ScheduledTask | null>(null)
const topicInput = ref('')

const defaultForm = (): ScheduledTaskCreate => ({
  name: '',
  type: 'GENERATE_AND_PUBLISH',
  content_type: 'WEITOUTIAO',
  schedule_mode: 'RANDOM_INTERVAL',
  schedule_config: {
    min_minutes: 80,
    max_minutes: 200,
  },
  active_start_hour: 8,
  active_end_hour: 22,
  topic_mode: 'RANDOM',
  topics: [],
  account_id: undefined,
  publish_mode: 'ONE',
  publish_batch_size: 1,
  publish_order: 'oldest',
  is_active: true,
})

const form = reactive<ScheduledTaskCreate>(defaultForm())

// 日志相关
const showLogsDialog = ref(false)
const logsLoading = ref(false)
const logs = ref<any[]>([])
const logsPage = ref(1)
const logsTotal = ref(0)
const currentTaskId = ref('')

// 监听话题模式变化
watch(() => form.topic_mode, (mode) => {
  if (mode === 'FIXED') {
    form.topics = topicInput.value ? [topicInput.value] : []
  }
})

watch(topicInput, (val) => {
  if (form.topic_mode === 'FIXED') {
    form.topics = val ? [val] : []
  }
})

const loadData = async () => {
  loading.value = true
  try {
    const [tasksRes, statusRes, accountsRes] = await Promise.all([
      scheduledTaskApi.list(),
      schedulerApi.status(),
      accountApi.list(),
    ])
    tasks.value = (tasksRes as any).items || []
    schedulerStatus.value = statusRes as SchedulerStatus
    accounts.value = (accountsRes as any).items || []
  } catch (e) {
    console.error(e)
  } finally {
    loading.value = false
  }
}

const openCreateDialog = () => {
  editingTask.value = null
  Object.assign(form, defaultForm())
  topicInput.value = ''
  showFormDialog.value = true
}

const openEditDialog = (task: ScheduledTask) => {
  editingTask.value = task
  Object.assign(form, {
    name: task.name,
    type: task.type,
    content_type: task.content_type,
    schedule_mode: task.schedule_mode,
    schedule_config: { ...task.schedule_config },
    active_start_hour: task.active_start_hour,
    active_end_hour: task.active_end_hour,
    topic_mode: task.topic_mode,
    topics: [...(task.topics || [])],
    account_id: task.account_id,
    publish_mode: task.publish_mode,
    publish_batch_size: task.publish_batch_size,
    publish_order: task.publish_order,
    is_active: task.is_active,
  })
  topicInput.value = task.topics?.[0] || ''
  showFormDialog.value = true
}

const saveTask = async () => {
  if (!form.name) {
    ElMessage.warning('请输入任务名称')
    return
  }

  if (form.type !== 'GENERATE' && !form.account_id) {
    ElMessage.warning('请选择发布账号')
    return
  }

  saving.value = true
  try {
    if (editingTask.value) {
      await scheduledTaskApi.update(editingTask.value.id, form)
      ElMessage.success('保存成功')
    } else {
      await scheduledTaskApi.create(form)
      ElMessage.success('创建成功')
    }
    showFormDialog.value = false
    loadData()
  } catch (e) {
    console.error(e)
  } finally {
    saving.value = false
  }
}

const toggleTask = async (task: ScheduledTask & { _toggling?: boolean }) => {
  task._toggling = true
  try {
    await scheduledTaskApi.toggle(task.id)
    ElMessage.success(task.is_active ? '已启用' : '已禁用')
    // 稍候刷新以获取最新状态（如下次运行时间）
    setTimeout(loadData, 500)
  } catch (e) {
    task.is_active = !task.is_active
    console.error(e)
  } finally {
    task._toggling = false
  }
}

const triggerTask = async (task: ScheduledTask) => {
  await ElMessageBox.confirm('确定要立即执行此任务吗？', '确认执行', { 
    type: 'info',
    confirmButtonText: '立即执行',
    cancelButtonText: '取消'
  })
  try {
    await scheduledTaskApi.trigger(task.id)
    ElMessage.success('任务已触发，正在后台执行')
  } catch (e) {
    console.error(e)
  }
}

const deleteTask = async (task: ScheduledTask) => {
  await ElMessageBox.confirm('确定要删除此任务吗？此操作不可恢复。', '确认删除', { 
    type: 'warning',
    confirmButtonText: '确认删除',
    cancelButtonText: '取消',
    confirmButtonClass: 'el-button--danger'
  })
  try {
    await scheduledTaskApi.delete(task.id)
    ElMessage.success('删除成功')
    loadData()
  } catch (e) {
    console.error(e)
  }
}

const viewLogs = async (task: ScheduledTask) => {
  currentTaskId.value = task.id
  logsPage.value = 1
  showLogsDialog.value = true
  await loadLogs()
}

const loadLogs = async () => {
  logsLoading.value = true
  try {
    const res: any = await scheduledTaskApi.logs(currentTaskId.value, {
      skip: (logsPage.value - 1) * 10,
      limit: 10,
    })
    logs.value = res.items || []
    logsTotal.value = res.total || 0
  } catch (e) {
    console.error(e)
  } finally {
    logsLoading.value = false
  }
}

const pauseScheduler = async () => {
  try {
    await schedulerApi.pause()
    ElMessage.success('调度器已暂停')
    loadData()
  } catch (e) {
    console.error(e)
  }
}

const resumeScheduler = async () => {
  try {
    await schedulerApi.resume()
    ElMessage.success('调度器已恢复')
    loadData()
  } catch (e) {
    console.error(e)
  }
}

// 格式化函数
const formatDate = (date: string) => dayjs(date).format('MM-DD HH:mm')

const formatSchedule = (task: ScheduledTask) => {
  if (task.schedule_mode === 'CRON') {
    return `Cron: ${task.schedule_config.cron}`
  } else if (task.schedule_mode === 'INTERVAL') {
    return `每 ${task.schedule_config.minutes} 分钟`
  } else {
    return `${task.schedule_config.min_minutes}-${task.schedule_config.max_minutes} 分钟随机`
  }
}

const formatTaskType = (type: string) => {
  const map: Record<string, string> = {
    GENERATE: '生成',
    PUBLISH: '发布',
    GENERATE_AND_PUBLISH: '生成+发布',
    SCHEDULED_GENERATE: '定时生成',
    SCHEDULED_PUBLISH: '定时发布',
    SCHEDULED_GENERATE_PUBLISH: '定时生成发布',
  }
  return map[type] || type
}

const formatStatus = (status: string) => {
  const map: Record<string, string> = {
    pending: '等待',
    running: '执行中',
    completed: '成功',
    failed: '失败',
  }
  return map[status] || status
}

const getTaskTypeStyle = (type: string) => {
  const styles: Record<string, string> = {
    GENERATE: 'bg-gradient-to-br from-blue-500 to-indigo-600 shadow-blue-500/30',
    PUBLISH: 'bg-gradient-to-br from-green-500 to-emerald-600 shadow-green-500/30',
    GENERATE_AND_PUBLISH: 'bg-gradient-to-br from-purple-500 to-pink-600 shadow-purple-500/30',
  }
  return styles[type] || 'bg-gradient-to-br from-gray-500 to-gray-600'
}

const getTaskTypeIcon = (type: string) => {
  const icons: Record<string, any> = {
    GENERATE: FileEdit,
    PUBLISH: Send,
    GENERATE_AND_PUBLISH: Zap,
  }
  return icons[type] || Calendar
}

onMounted(loadData)
</script>

<style scoped>
.scheduled-tasks {
  @apply animate-in;
}

.list-enter-active,
.list-leave-active {
  transition: all 0.5s ease;
}
.list-enter-from,
.list-leave-to {
  opacity: 0;
  transform: translateX(-30px);
}

.custom-scrollbar::-webkit-scrollbar {
  width: 4px;
}
.custom-scrollbar::-webkit-scrollbar-thumb {
  background-color: #e5e7eb;
  border-radius: 4px;
}
</style>
