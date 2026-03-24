<script setup lang="ts">
import { computed, h, onMounted, ref } from 'vue'
import { getRAGStatus, getRAGRetrievalLogs } from '@/api/admin'
import { NGrid, NGridItem, NDescriptions, NDescriptionsItem, NDataTable, NTag } from 'naive-ui'
import UIState from '@/components/common/UIState.vue'
import type { UIStateType } from '@/types/ui-state'

interface RAGStatus {
  vector_store: {
    status: string
    collection_name: string
    dimension: number
    total_vectors: number
  }
  graph_store: {
    status: string
    total_nodes: number
    total_relations: number
  }
}

interface RetrievalLog {
  timestamp: string
  query: string
  top_k: number
  vector_hits: number
  graph_hits: number
  total_results: number
  reranker_used: boolean
  avg_score: number
  top_score: number
  latency_ms: number
  sources: string[]
  top_contents: string[]
}

interface RetrievalSummary {
  total_queries: number
  avg_relevance_score: number
  avg_latency_ms: number
  avg_results_per_query: number
  total_vector_hits: number
  total_graph_hits: number
  reranker_usage_percent: number
}

const status = ref<RAGStatus>({
  vector_store: { status: 'unhealthy', collection_name: '-', dimension: 0, total_vectors: 0 },
  graph_store: { status: 'unhealthy', total_nodes: 0, total_relations: 0 },
})

const logs = ref<RetrievalLog[]>([])
const summary = ref<RetrievalSummary>({
  total_queries: 0,
  avg_relevance_score: 0,
  avg_latency_ms: 0,
  avg_results_per_query: 0,
  total_vector_hits: 0,
  total_graph_hits: 0,
  reranker_usage_percent: 0,
})

const statusState = ref<UIStateType>('loading')
const logsState = ref<UIStateType>('loading')
const descriptionLabelStyle = 'font-weight: 600; color: var(--ds-text-secondary);'

const scoreQualityLabel = computed(() => {
  const s = summary.value.avg_relevance_score
  if (s >= 0.8) return { text: '优秀', color: 'text-emerald-500' }
  if (s >= 0.6) return { text: '良好', color: 'text-sky-500' }
  if (s >= 0.4) return { text: '一般', color: 'text-amber-500' }
  return { text: '较低', color: 'text-rose-500' }
})

const columns = [
  {
    title: '时间',
    key: 'timestamp',
    width: 150,
  },
  {
    title: '查询内容',
    key: 'query',
    ellipsis: { tooltip: true },
  },
  {
    title: '向量召回',
    key: 'vector_hits',
    width: 90,
    align: 'center' as const,
  },
  {
    title: '图谱召回',
    key: 'graph_hits',
    width: 90,
    align: 'center' as const,
  },
  {
    title: '结果数',
    key: 'total_results',
    width: 80,
    align: 'center' as const,
  },
  {
    title: '平均分',
    key: 'avg_score',
    width: 90,
    align: 'right' as const,
    render(row: RetrievalLog) {
      let colorClass = 'text-emerald-600'
      if (row.avg_score < 0.4) colorClass = 'text-rose-500'
      else if (row.avg_score < 0.6) colorClass = 'text-amber-500'
      return h('span', { class: `font-mono font-semibold ${colorClass}` }, row.avg_score.toFixed(3))
    },
  },
  {
    title: '最高分',
    key: 'top_score',
    width: 90,
    align: 'right' as const,
    render(row: RetrievalLog) {
      return h('span', { class: 'font-mono font-semibold text-indigo-600' }, row.top_score.toFixed(3))
    },
  },
  {
    title: '重排',
    key: 'reranker_used',
    width: 70,
    align: 'center' as const,
    render(row: RetrievalLog) {
      return h(
        NTag,
        { type: row.reranker_used ? 'success' : 'default', round: true, size: 'small' },
        { default: () => (row.reranker_used ? '开启' : '关闭') },
      )
    },
  },
  {
    title: '耗时',
    key: 'latency_ms',
    width: 90,
    align: 'right' as const,
    render(row: RetrievalLog) {
      let colorClass = 'text-emerald-600'
      if (row.latency_ms > 2000) colorClass = 'text-rose-500'
      else if (row.latency_ms > 500) colorClass = 'text-amber-500'
      return h('span', { class: `font-mono ${colorClass}` }, `${row.latency_ms}ms`)
    },
  },
]

const pagination = { pageSize: 15 }

const fetchStatus = async () => {
  statusState.value = 'loading'
  try {
    const res: any = await getRAGStatus()
    if (res?.data) status.value = res.data
    statusState.value = 'retry'
  } catch (err) {
    console.error('Failed to fetch RAG status:', err)
    statusState.value = 'error'
  }
}

const fetchLogs = async () => {
  logsState.value = 'loading'
  try {
    const res: any = await getRAGRetrievalLogs()
    if (res?.data) {
      logs.value = res.data.logs || []
      summary.value = res.data.summary || summary.value
    }
    logsState.value = logs.value.length > 0 ? 'retry' : 'empty'
  } catch (err) {
    console.error('Failed to fetch retrieval logs:', err)
    logsState.value = 'error'
  }
}

const refreshAll = async () => {
  await Promise.all([fetchStatus(), fetchLogs()])
}

onMounted(() => {
  refreshAll()
})
</script>

<template>
  <div class="space-y-8 pb-10">
    <div class="flex flex-col space-y-2 relative">
      <div class="absolute -top-10 -right-10 w-40 h-40 bg-purple-400/20 blur-3xl rounded-full pointer-events-none"></div>
      <h2 class="text-3xl font-extrabold tracking-tight text-slate-900 relative z-10">RAG 检索质量看板</h2>
      <p class="text-slate-500 font-medium text-lg relative z-10">量化追踪每次检索的相关性评分、延迟和来源覆盖情况。</p>
    </div>

    <UIState
      v-if="statusState === 'loading' && logsState === 'loading'"
      type="loading"
      title="正在加载 RAG 数据"
      description="请稍候，我们正在同步检索引擎状态和日志。"
    />

    <UIState
      v-else-if="statusState === 'error' && logsState === 'error'"
      type="error"
      title="RAG 数据加载失败"
      description="状态与日志都暂时不可用，请稍后重试。"
      action-text="重试"
      @action="refreshAll"
    />

    <template v-else>
      <div class="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-7 gap-4 relative z-10">
        <div class="summary-card">
          <div class="summary-label">累计检索</div>
          <div class="summary-value">{{ summary.total_queries }}</div>
        </div>
        <div class="summary-card">
          <div class="summary-label">平均相关度</div>
          <div class="flex items-baseline space-x-2">
            <span class="summary-value" :class="scoreQualityLabel.color">{{ summary.avg_relevance_score.toFixed(3) }}</span>
            <span class="text-xs font-bold">{{ scoreQualityLabel.text }}</span>
          </div>
        </div>
        <div class="summary-card">
          <div class="summary-label">平均耗时</div>
          <div class="summary-value">{{ summary.avg_latency_ms }}<span class="text-sm text-slate-400">ms</span></div>
        </div>
        <div class="summary-card">
          <div class="summary-label">平均结果数</div>
          <div class="summary-value">{{ summary.avg_results_per_query }}</div>
        </div>
        <div class="summary-card">
          <div class="summary-label">向量命中</div>
          <div class="summary-value text-emerald-600">{{ summary.total_vector_hits }}</div>
        </div>
        <div class="summary-card">
          <div class="summary-label">图谱命中</div>
          <div class="summary-value text-purple-600">{{ summary.total_graph_hits }}</div>
        </div>
        <div class="summary-card">
          <div class="summary-label">重排使用率</div>
          <div class="summary-value text-indigo-600">{{ summary.reranker_usage_percent }}<span class="text-sm text-slate-400">%</span></div>
        </div>
      </div>

      <UIState
        v-if="statusState === 'error'"
        type="error"
        title="基础设施状态加载失败"
        description="Milvus / Neo4j 状态暂时不可用，可单独重试。"
        action-text="重试状态"
        @action="fetchStatus"
      />

      <n-grid v-else cols="1 l:2" responsive="screen" :x-gap="24" :y-gap="24" class="relative z-10">
        <n-grid-item>
          <div class="infra-card">
            <h3 class="infra-title">Milvus 向量引擎</h3>
            <n-descriptions :column="1" bordered size="large" class="!bg-transparent *:!bg-transparent">
              <n-descriptions-item label="状态" :label-style="descriptionLabelStyle">
                <span class="font-semibold" :class="status.vector_store.status === 'healthy' ? 'text-emerald-600' : 'text-rose-500'">{{ status.vector_store.status }}</span>
              </n-descriptions-item>
              <n-descriptions-item label="集合名称" :label-style="descriptionLabelStyle">{{ status.vector_store.collection_name }}</n-descriptions-item>
              <n-descriptions-item label="向量维度" :label-style="descriptionLabelStyle">{{ status.vector_store.dimension }}</n-descriptions-item>
              <n-descriptions-item label="向量总量" :label-style="descriptionLabelStyle">{{ status.vector_store.total_vectors.toLocaleString() }}</n-descriptions-item>
            </n-descriptions>
          </div>
        </n-grid-item>

        <n-grid-item>
          <div class="infra-card">
            <h3 class="infra-title">Neo4j 图数据库</h3>
            <n-descriptions :column="1" bordered size="large" class="!bg-transparent *:!bg-transparent">
              <n-descriptions-item label="状态" :label-style="descriptionLabelStyle">
                <span class="font-semibold" :class="status.graph_store.status === 'healthy' ? 'text-emerald-600' : 'text-rose-500'">{{ status.graph_store.status }}</span>
              </n-descriptions-item>
              <n-descriptions-item label="节点数量" :label-style="descriptionLabelStyle">{{ status.graph_store.total_nodes.toLocaleString() }}</n-descriptions-item>
              <n-descriptions-item label="关系数量" :label-style="descriptionLabelStyle">{{ status.graph_store.total_relations.toLocaleString() }}</n-descriptions-item>
            </n-descriptions>
          </div>
        </n-grid-item>
      </n-grid>

      <div class="relative bg-white rounded-2xl shadow-[0_4px_20px_rgb(0,0,0,0.04)] border border-slate-100 p-6 overflow-hidden">
        <div class="mb-6 flex justify-between items-center relative z-10">
          <div>
            <h3 class="text-xl font-bold text-slate-800">检索质量日志</h3>
            <p class="text-sm text-slate-400 mt-1">记录每次检索的召回数量、得分和响应耗时。</p>
          </div>
          <button
            @click="fetchLogs"
            :disabled="logsState === 'loading'"
            class="px-5 py-2 rounded-xl bg-slate-900 hover:bg-slate-800 text-white font-medium tracking-wide transition-all shadow-md hover:shadow-lg disabled:opacity-50 flex items-center space-x-2"
          >
            <span v-if="logsState === 'loading'" class="animate-spin block w-4 h-4 border-2 border-white/30 border-t-white rounded-full"></span>
            <span>{{ logsState === 'loading' ? '刷新中...' : '刷新' }}</span>
          </button>
        </div>

        <UIState
          v-if="logsState === 'loading'"
          type="loading"
          title="正在加载检索日志"
          description="请稍候，我们正在获取最新记录。"
          compact
        />

        <UIState
          v-else-if="logsState === 'error'"
          type="error"
          title="检索日志加载失败"
          description="无法获取日志数据，请重试。"
          action-text="重试"
          compact
          @action="fetchLogs"
        />

        <UIState
          v-else-if="logs.length === 0"
          type="empty"
          title="暂无检索日志"
          description="当会话触发 RAG 检索后，这里将展示详细记录。"
          compact
        />

        <div v-else class="overflow-x-auto rounded-xl border border-slate-100">
          <n-data-table
            :columns="columns"
            :data="logs"
            :pagination="pagination"
            :bordered="false"
            size="large"
            class="!bg-transparent"
          />
        </div>
      </div>
    </template>
  </div>
</template>

<style scoped>
.summary-card {
  border-radius: 1rem;
  background: #fff;
  border: 1px solid rgba(226, 232, 240, 0.8);
  padding: 1.25rem;
  box-shadow: 0 2px 12px rgba(15, 23, 42, 0.04);
  transition: all var(--ds-duration-base) var(--ds-ease-standard);
}

.summary-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 12px 24px rgba(15, 23, 42, 0.12);
}

.summary-label {
  font-size: 0.75rem;
  font-weight: 700;
  color: #94a3b8;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  margin-bottom: 0.5rem;
}

.summary-value {
  font-size: 1.6rem;
  font-weight: 800;
  color: #0f172a;
  font-variant-numeric: tabular-nums;
}

.infra-card {
  height: 100%;
  border-radius: 1rem;
  background: #fff;
  border: 1px solid rgba(226, 232, 240, 0.7);
  box-shadow: 0 4px 20px rgba(15, 23, 42, 0.04);
  padding: 1.5rem;
}

.infra-title {
  font-size: 1.1rem;
  font-weight: 700;
  color: #1e293b;
  margin-bottom: 1rem;
}
</style>
