<script setup lang="ts">
import { h, ref, onMounted } from 'vue'
import { getModelLogs } from '@/api/admin'
import { NDataTable, NTag, NInput, NIcon } from 'naive-ui'
import { SearchOutline } from '@vicons/ionicons5'

interface ModelLog {
  id: string
  timestamp: string
  modelName: string
  promptSnippet: string
  outputSnippet: string
  tokens: number
  latency: number
}

const loading = ref(true)
const logs = ref<ModelLog[]>([])

const columns = [
  {
    title: '时间',
    key: 'timestamp',
    width: 160
  },
  {
    title: '模型名称',
    key: 'modelName',
    width: 120,
    render(row: ModelLog) {
      const typeMap: Record<string, 'info' | 'success' | 'warning' | 'error'> = {
        'gpt-4': 'success',
        'gpt-3.5-turbo': 'info',
        'claude-3-opus': 'warning'
      }
      const tagType = typeMap[row.modelName] || 'default'
      return h(NTag, { type: tagType as any, round: true, size: 'small' }, { default: () => row.modelName })
    }
  },
  {
    title: '用户输入 (Prompt)',
    key: 'promptSnippet',
    ellipsis: { tooltip: true }
  },
  {
    title: '模型输出 (Output)',
    key: 'outputSnippet',
    ellipsis: { tooltip: true }
  },
  {
    title: '消耗 Tokens',
    key: 'tokens',
    width: 100,
    align: 'right' as const
  },
  {
    title: '耗时 (ms)',
    key: 'latency',
    width: 100,
    align: 'right' as const,
    render(row: ModelLog) {
      let colorClass = 'text-green-600'
      if (row.latency > 2000) colorClass = 'text-red-500'
      else if (row.latency > 1000) colorClass = 'text-orange-500'
      
      return h('span', { class: `font-mono ${colorClass}` }, `${row.latency}ms`)
    }
  }
]

const pagination = {
  pageSize: 10
}

const fetchLogs = async () => {
  loading.value = true
  try {
    const res: any = await getModelLogs()
    if (res.data) {
      logs.value = res.data
    }
  } catch (error) {
    console.error('Failed to fetch model logs:', error)
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  fetchLogs()
})
</script>

<template>
  <div class="space-y-8 pb-10">
    <div class="flex flex-col space-y-2 relative">
      <div class="absolute -top-10 -right-10 w-40 h-40 bg-indigo-400/20 blur-3xl rounded-full pointer-events-none"></div>
      <h2 class="text-3xl font-extrabold tracking-tight text-slate-900 dark:text-white relative z-10">
        模型调用监控
      </h2>
      <p class="text-slate-500 dark:text-slate-400 font-medium text-lg relative z-10">
        实时查看不同 LLM 模型的请求记录、消耗及响应延迟
      </p>
    </div>

    <div class="relative bg-white dark:bg-slate-800 rounded-2xl shadow-[0_4px_20px_rgb(0,0,0,0.04)] border border-slate-100 dark:border-slate-700 p-6 overflow-hidden">
      <!-- 搜索和刷新头部 -->
      <div class="mb-6 flex flex-col sm:flex-row justify-between items-center gap-4 relative z-10">
        <div class="w-full sm:w-80 group">
          <n-input placeholder="搜索 Prompt 内容..." clearable size="large" class="shadow-sm group-hover:shadow transition-shadow !rounded-xl">
            <template #prefix>
              <n-icon class="text-slate-400"><SearchOutline /></n-icon>
            </template>
          </n-input>
        </div>
        <button 
          @click="fetchLogs" 
          :disabled="loading"
          class="w-full sm:w-auto px-6 py-2.5 rounded-xl bg-slate-900 hover:bg-slate-800 text-white dark:bg-slate-100 dark:hover:bg-white dark:text-slate-900 font-medium tracking-wide transition-all shadow-md hover:shadow-lg disabled:opacity-50 flex justify-center items-center space-x-2"
        >
          <span v-if="loading" class="animate-spin text-lg block w-5 h-5 border-2 border-white/30 border-t-white dark:border-slate-900/30 dark:border-t-slate-900 rounded-full"></span>
          <span>立刻刷新</span>
        </button>
      </div>
      
      <!-- 表格区域 -->
      <div class="overflow-x-auto relative z-10 rounded-xl border border-slate-100 dark:border-slate-700">
        <n-data-table
          :columns="columns"
          :data="logs"
          :loading="loading"
          :pagination="pagination"
          :bordered="false"
          size="large"
          class="!bg-transparent"
        />
      </div>
    </div>
  </div>
</template>
