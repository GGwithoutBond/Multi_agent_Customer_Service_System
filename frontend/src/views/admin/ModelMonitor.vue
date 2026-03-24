<script setup lang="ts">
import { computed, h, ref, onMounted } from 'vue'
import { getModelLogs } from '@/api/admin'
import { NDataTable, NTag, NInput, NIcon } from 'naive-ui'
import { SearchOutline } from '@vicons/ionicons5'
import UIState from '@/components/common/UIState.vue'
import type { UIStateType } from '@/types/ui-state'

interface ModelLog {
  id: string
  timestamp: string
  modelName: string
  conversationId: string
  intent: string
  workerType: string
  traceId: string
  promptSnippet: string
  outputSnippet: string
  tokens: number
  latency: number
}

const pageState = ref<UIStateType>('loading')
const logs = ref<ModelLog[]>([])
const query = ref('')

const filteredLogs = computed(() => {
  if (!query.value.trim()) return logs.value
  const keyword = query.value.toLowerCase()
  return logs.value.filter((row) => {
    return (
      row.modelName?.toLowerCase().includes(keyword) ||
      row.conversationId?.toLowerCase().includes(keyword) ||
      row.intent?.toLowerCase().includes(keyword) ||
      row.workerType?.toLowerCase().includes(keyword) ||
      row.promptSnippet?.toLowerCase().includes(keyword)
    )
  })
})

const columns = [
  {
    title: '时间',
    key: 'timestamp',
    width: 170,
  },
  {
    title: '模型名称',
    key: 'modelName',
    width: 130,
    render(row: ModelLog) {
      const typeMap: Record<string, 'info' | 'success' | 'warning' | 'error'> = {
        'gpt-4': 'success',
        'gpt-3.5-turbo': 'info',
        'claude-3-opus': 'warning',
      }
      const tagType = typeMap[row.modelName] || 'default'
      return h(NTag, { type: tagType as any, round: true, size: 'small' }, { default: () => row.modelName })
    },
  },
  {
    title: '会话 ID',
    key: 'conversationId',
    width: 160,
    ellipsis: { tooltip: true },
  },
  {
    title: '意图 / Worker',
    key: 'workerType',
    width: 170,
    render(row: ModelLog) {
      return h('div', { class: 'flex flex-col gap-0.5' }, [
        h('span', { class: 'text-xs text-slate-600' }, row.intent || '-'),
        h('span', { class: 'text-xs text-slate-400' }, row.workerType || '-'),
      ])
    },
  },
  {
    title: '用户输入',
    key: 'promptSnippet',
    ellipsis: { tooltip: true },
  },
  {
    title: '模型输出',
    key: 'outputSnippet',
    ellipsis: { tooltip: true },
  },
  {
    title: 'Tokens',
    key: 'tokens',
    width: 100,
    align: 'right' as const,
  },
  {
    title: '耗时 (ms)',
    key: 'latency',
    width: 110,
    align: 'right' as const,
    render(row: ModelLog) {
      let colorClass = 'text-green-600'
      if (row.latency > 2000) colorClass = 'text-red-500'
      else if (row.latency > 1000) colorClass = 'text-orange-500'

      return h('span', { class: `font-mono ${colorClass}` }, `${row.latency}ms`)
    },
  },
  {
    title: 'Trace ID',
    key: 'traceId',
    width: 140,
    ellipsis: { tooltip: true },
  },
]

const pagination = {
  pageSize: 10,
}

const fetchLogs = async () => {
  pageState.value = 'loading'
  try {
    const res: any = await getModelLogs()
    logs.value = res?.data || []
    pageState.value = logs.value.length ? 'retry' : 'empty'
  } catch (error) {
    console.error('Failed to fetch model logs:', error)
    pageState.value = 'error'
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
      <h2 class="text-3xl font-extrabold tracking-tight text-slate-900 relative z-10">模型调用监控</h2>
      <p class="text-slate-500 font-medium text-lg relative z-10">实时查看不同 LLM 模型的请求日志、消耗和响应时延。</p>
    </div>

    <div class="relative bg-white rounded-2xl shadow-[0_4px_20px_rgb(0,0,0,0.04)] border border-slate-100 p-6 overflow-hidden">
      <div class="mb-6 flex flex-col sm:flex-row justify-between items-center gap-4 relative z-10">
        <div class="w-full sm:w-80 group">
          <n-input v-model:value="query" placeholder="搜索模型名、会话 ID 或输入内容" clearable size="large" class="shadow-sm group-hover:shadow transition-shadow !rounded-xl">
            <template #prefix>
              <n-icon class="text-slate-400"><SearchOutline /></n-icon>
            </template>
          </n-input>
        </div>
        <button
          @click="fetchLogs"
          :disabled="pageState === 'loading'"
          class="w-full sm:w-auto px-6 py-2.5 rounded-xl bg-slate-900 hover:bg-slate-800 text-white font-medium tracking-wide transition-all shadow-md hover:shadow-lg disabled:opacity-50 flex justify-center items-center space-x-2"
        >
          <span
            v-if="pageState === 'loading'"
            class="animate-spin text-lg block w-5 h-5 border-2 border-white/30 border-t-white rounded-full"
          ></span>
          <span>{{ pageState === 'loading' ? '刷新中...' : '刷新数据' }}</span>
        </button>
      </div>

      <UIState
        v-if="pageState === 'loading'"
        type="loading"
        title="正在加载模型日志"
        description="请稍候，我们正在同步最新调用记录。"
        compact
      />

      <UIState
        v-else-if="pageState === 'error'"
        type="error"
        title="模型日志加载失败"
        description="网络或服务异常，请点击重试。"
        action-text="重试"
        compact
        @action="fetchLogs"
      />

      <UIState
        v-else-if="filteredLogs.length === 0"
        type="empty"
        :title="query ? '没有匹配日志' : '暂无模型调用日志'"
        :description="query ? '请尝试更换关键词。' : '暂无可展示数据，稍后刷新看看。'"
        compact
      />

      <div v-else class="overflow-x-auto relative z-10 rounded-xl border border-slate-100">
        <n-data-table
          :columns="columns"
          :data="filteredLogs"
          :pagination="pagination"
          :bordered="false"
          size="large"
          class="!bg-transparent"
        />
      </div>
    </div>
  </div>
</template>
