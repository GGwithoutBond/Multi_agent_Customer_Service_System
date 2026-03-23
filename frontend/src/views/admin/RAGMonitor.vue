<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { getRAGStatus, getRAGRetrievalLogs } from '@/api/admin'
import { NGrid, NGridItem, NDescriptions, NDescriptionsItem, NDataTable, NTag } from 'naive-ui'
import { h } from 'vue'

interface RAGStatus {
  vector_store: {
    status: string;
    collection_name: string;
    dimension: number;
    total_vectors: number;
  };
  graph_store: {
    status: string;
    total_nodes: number;
    total_relations: number;
  };
}

interface RetrievalLog {
  timestamp: string;
  query: string;
  top_k: number;
  vector_hits: number;
  graph_hits: number;
  total_results: number;
  reranker_used: boolean;
  avg_score: number;
  top_score: number;
  latency_ms: number;
  sources: string[];
  top_contents: string[];
}

interface RetrievalSummary {
  total_queries: number;
  avg_relevance_score: number;
  avg_latency_ms: number;
  avg_results_per_query: number;
  total_vector_hits: number;
  total_graph_hits: number;
  reranker_usage_percent: number;
}

const status = ref<RAGStatus>({
  vector_store: { status: 'unhealthy', collection_name: '-', dimension: 0, total_vectors: 0 },
  graph_store: { status: 'unhealthy', total_nodes: 0, total_relations: 0 }
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

const loading = ref(true)
const logsLoading = ref(true)

// Score quality label
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
    title: 'Query',
    key: 'query',
    ellipsis: { tooltip: true },
  },
  {
    title: '向量召回',
    key: 'vector_hits',
    width: 85,
    align: 'center' as const,
  },
  {
    title: '图谱召回',
    key: 'graph_hits',
    width: 85,
    align: 'center' as const,
  },
  {
    title: '总结果',
    key: 'total_results',
    width: 70,
    align: 'center' as const,
  },
  {
    title: '平均分',
    key: 'avg_score',
    width: 80,
    align: 'right' as const,
    render(row: RetrievalLog) {
      let colorClass = 'text-emerald-600'
      if (row.avg_score < 0.4) colorClass = 'text-rose-500'
      else if (row.avg_score < 0.6) colorClass = 'text-amber-500'
      return h('span', { class: `font-mono font-semibold ${colorClass}` }, row.avg_score.toFixed(3))
    }
  },
  {
    title: '最高分',
    key: 'top_score',
    width: 80,
    align: 'right' as const,
    render(row: RetrievalLog) {
      return h('span', { class: 'font-mono font-semibold text-indigo-600 dark:text-indigo-400' }, row.top_score.toFixed(3))
    }
  },
  {
    title: '精排',
    key: 'reranker_used',
    width: 60,
    align: 'center' as const,
    render(row: RetrievalLog) {
      return h(NTag, { type: row.reranker_used ? 'success' : 'default', round: true, size: 'small' },
        { default: () => row.reranker_used ? '✓' : '✗' })
    }
  },
  {
    title: '耗时',
    key: 'latency_ms',
    width: 80,
    align: 'right' as const,
    render(row: RetrievalLog) {
      let colorClass = 'text-emerald-600'
      if (row.latency_ms > 2000) colorClass = 'text-rose-500'
      else if (row.latency_ms > 500) colorClass = 'text-amber-500'
      return h('span', { class: `font-mono ${colorClass}` }, `${row.latency_ms}ms`)
    }
  },
]

const pagination = { pageSize: 15 }

const fetchStatus = async () => {
  loading.value = true
  try {
    const res: any = await getRAGStatus()
    if (res.data) status.value = res.data
  } catch (err) {
    console.error('Failed to fetch RAG status:', err)
  } finally {
    loading.value = false
  }
}

const fetchLogs = async () => {
  logsLoading.value = true
  try {
    const res: any = await getRAGRetrievalLogs()
    if (res.data) {
      logs.value = res.data.logs || []
      summary.value = res.data.summary || summary.value
    }
  } catch (err) {
    console.error('Failed to fetch retrieval logs:', err)
  } finally {
    logsLoading.value = false
  }
}

onMounted(() => {
  fetchStatus()
  fetchLogs()
})
</script>

<template>
  <div class="space-y-8 pb-10">
    <!-- Header -->
    <div class="flex flex-col space-y-2 relative">
      <div class="absolute -top-10 -right-10 w-40 h-40 bg-purple-400/20 blur-3xl rounded-full pointer-events-none"></div>
      <h2 class="text-3xl font-extrabold tracking-tight text-slate-900 dark:text-white relative z-10">
        RAG 知识引擎质量面板
      </h2>
      <p class="text-slate-500 dark:text-slate-400 font-medium text-lg relative z-10">
        量化追踪每一次检索召回的相关性评分、延迟及来源分布
      </p>
    </div>

    <!-- ══ 1. Quality Summary Cards ══ -->
    <div class="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-7 gap-4 relative z-10">
      <!-- Total Queries -->
      <div class="rounded-2xl bg-white dark:bg-slate-800 border border-slate-200/60 dark:border-slate-700 p-5 shadow-[0_2px_12px_rgb(0,0,0,0.04)] transition-all hover:shadow-lg hover:-translate-y-0.5">
        <div class="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">累计检索</div>
        <div class="text-2xl font-extrabold text-slate-800 dark:text-white font-mono tabular-nums">{{ summary.total_queries }}</div>
      </div>
      <!-- Avg Score -->
      <div class="rounded-2xl bg-white dark:bg-slate-800 border border-slate-200/60 dark:border-slate-700 p-5 shadow-[0_2px_12px_rgb(0,0,0,0.04)] transition-all hover:shadow-lg hover:-translate-y-0.5">
        <div class="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">平均相关度</div>
        <div class="flex items-baseline space-x-2">
          <span class="text-2xl font-extrabold font-mono tabular-nums" :class="scoreQualityLabel.color">{{ summary.avg_relevance_score.toFixed(3) }}</span>
          <span class="text-xs font-bold px-1.5 py-0.5 rounded-full" :class="`${scoreQualityLabel.color} bg-opacity-10`">{{ scoreQualityLabel.text }}</span>
        </div>
      </div>
      <!-- Avg Latency -->
      <div class="rounded-2xl bg-white dark:bg-slate-800 border border-slate-200/60 dark:border-slate-700 p-5 shadow-[0_2px_12px_rgb(0,0,0,0.04)] transition-all hover:shadow-lg hover:-translate-y-0.5">
        <div class="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">平均耗时</div>
        <div class="text-2xl font-extrabold text-slate-800 dark:text-white font-mono tabular-nums">{{ summary.avg_latency_ms }}<span class="text-sm text-slate-400 ml-0.5">ms</span></div>
      </div>
      <!-- Avg Results -->
      <div class="rounded-2xl bg-white dark:bg-slate-800 border border-slate-200/60 dark:border-slate-700 p-5 shadow-[0_2px_12px_rgb(0,0,0,0.04)] transition-all hover:shadow-lg hover:-translate-y-0.5">
        <div class="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">平均结果数</div>
        <div class="text-2xl font-extrabold text-slate-800 dark:text-white font-mono tabular-nums">{{ summary.avg_results_per_query }}</div>
      </div>
      <!-- Vector Hits -->
      <div class="rounded-2xl bg-white dark:bg-slate-800 border border-slate-200/60 dark:border-slate-700 p-5 shadow-[0_2px_12px_rgb(0,0,0,0.04)] transition-all hover:shadow-lg hover:-translate-y-0.5">
        <div class="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">向量命中</div>
        <div class="text-2xl font-extrabold text-emerald-600 dark:text-emerald-400 font-mono tabular-nums">{{ summary.total_vector_hits }}</div>
      </div>
      <!-- Graph Hits -->
      <div class="rounded-2xl bg-white dark:bg-slate-800 border border-slate-200/60 dark:border-slate-700 p-5 shadow-[0_2px_12px_rgb(0,0,0,0.04)] transition-all hover:shadow-lg hover:-translate-y-0.5">
        <div class="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">图谱命中</div>
        <div class="text-2xl font-extrabold text-purple-600 dark:text-purple-400 font-mono tabular-nums">{{ summary.total_graph_hits }}</div>
      </div>
      <!-- Reranker Usage -->
      <div class="rounded-2xl bg-white dark:bg-slate-800 border border-slate-200/60 dark:border-slate-700 p-5 shadow-[0_2px_12px_rgb(0,0,0,0.04)] transition-all hover:shadow-lg hover:-translate-y-0.5">
        <div class="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">精排率</div>
        <div class="text-2xl font-extrabold text-indigo-600 dark:text-indigo-400 font-mono tabular-nums">{{ summary.reranker_usage_percent }}<span class="text-sm text-slate-400 ml-0.5">%</span></div>
      </div>
    </div>

    <!-- ══ 2. Infrastructure Status (Milvus + Neo4j) ══ -->
    <n-grid cols="1 l:2" responsive="screen" :x-gap="24" :y-gap="24" class="relative z-10">
      <!-- Milvus Card -->
      <n-grid-item>
        <div class="h-full rounded-2xl bg-white dark:bg-slate-800 border border-slate-200/60 dark:border-slate-700 shadow-[0_4px_20px_rgb(0,0,0,0.04)] hover:shadow-xl hover:-translate-y-1 transition-all duration-300 overflow-hidden flex flex-col relative group">
          <div class="absolute top-0 right-0 w-32 h-32 bg-emerald-50 dark:bg-emerald-900/20 rounded-full blur-3xl opacity-50 group-hover:scale-150 transition-transform duration-700 pointer-events-none"></div>
          <div class="p-6 border-b border-slate-100 dark:border-slate-700/50 flex justify-between items-center relative z-10">
             <div class="flex items-center space-x-3">
               <div class="w-10 h-10 rounded-xl bg-gradient-to-br from-emerald-400 to-teal-500 flex items-center justify-center text-white shadow-lg shadow-emerald-500/30">
                 <svg class="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" /></svg>
               </div>
               <h3 class="text-xl font-bold text-slate-800 dark:text-slate-100">Milvus 向量引擎</h3>
             </div>
             <div class="flex items-center space-x-2 bg-slate-50 dark:bg-slate-900 px-3 py-1.5 rounded-full shadow-inner border border-slate-200/50 dark:border-slate-700/50">
               <span class="relative flex h-2.5 w-2.5">
                 <span v-if="!loading && status.vector_store.status === 'healthy'" class="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                 <span class="relative inline-flex rounded-full h-2.5 w-2.5" :class="status.vector_store.status === 'healthy' ? 'bg-emerald-500' : 'bg-rose-500'"></span>
               </span>
               <span class="text-sm font-semibold tracking-wide capitalize" :class="status.vector_store.status === 'healthy' ? 'text-emerald-600' : 'text-rose-500'">{{ status.vector_store.status }}</span>
             </div>
          </div>
          <div class="p-6 flex-1 bg-slate-50/30 dark:bg-slate-900/30">
            <div v-if="loading" class="animate-pulse space-y-5">
              <div class="h-4 bg-slate-200 dark:bg-slate-700 rounded w-full"></div>
              <div class="h-4 bg-slate-200 dark:bg-slate-700 rounded w-5/6"></div>
            </div>
            <div v-else>
              <n-descriptions :column="1" bordered size="large" class="!bg-transparent *:!bg-transparent">
                <n-descriptions-item label="集合名称" label-style="font-weight: 600; color: #64748b;">
                  <span class="text-lg font-medium text-slate-800 dark:text-slate-200">{{ status.vector_store.collection_name }}</span>
                </n-descriptions-item>
                <n-descriptions-item label="特征维度" label-style="font-weight: 600; color: #64748b;">
                  <span class="text-lg font-medium text-slate-800 dark:text-slate-200">{{ status.vector_store.dimension }}</span>
                </n-descriptions-item>
                <n-descriptions-item label="已索引向量数" label-style="font-weight: 600; color: #64748b;">
                  <span class="text-2xl font-extrabold text-emerald-600 dark:text-emerald-400 font-mono tracking-tight">{{ status.vector_store.total_vectors.toLocaleString() }}</span>
                </n-descriptions-item>
              </n-descriptions>
            </div>
          </div>
        </div>
      </n-grid-item>

      <!-- Neo4j Card -->
      <n-grid-item>
        <div class="h-full rounded-2xl bg-white dark:bg-slate-800 border border-slate-200/60 dark:border-slate-700 shadow-[0_4px_20px_rgb(0,0,0,0.04)] hover:shadow-xl hover:-translate-y-1 transition-all duration-300 overflow-hidden flex flex-col relative group">
          <div class="absolute top-0 right-0 w-32 h-32 bg-purple-50 dark:bg-purple-900/20 rounded-full blur-3xl opacity-50 group-hover:scale-150 transition-transform duration-700 pointer-events-none"></div>
          <div class="p-6 border-b border-slate-100 dark:border-slate-700/50 flex justify-between items-center relative z-10">
             <div class="flex items-center space-x-3">
               <div class="w-10 h-10 rounded-xl bg-gradient-to-br from-purple-400 to-indigo-500 flex items-center justify-center text-white shadow-lg shadow-purple-500/30">
                 <svg class="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14 10l-2 1m0 0l-2-1m2 1v2.5M20 7l-2 1m2-1l-2-1m2 1v2.5M14 4l-2-1-2 1M4 7l2-1M4 7l2 1M4 7v2.5M12 21l-2-1m2 1l2-1m-2 1v-2.5M6 18l-2-1v-2.5M18 18l2-1v-2.5" /></svg>
               </div>
               <h3 class="text-xl font-bold text-slate-800 dark:text-slate-100">Neo4j 图数据库</h3>
             </div>
             <div class="flex items-center space-x-2 bg-slate-50 dark:bg-slate-900 px-3 py-1.5 rounded-full shadow-inner border border-slate-200/50 dark:border-slate-700/50">
               <span class="relative flex h-2.5 w-2.5">
                 <span v-if="!loading && status.graph_store.status === 'healthy'" class="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                 <span class="relative inline-flex rounded-full h-2.5 w-2.5" :class="status.graph_store.status === 'healthy' ? 'bg-emerald-500' : 'bg-rose-500'"></span>
               </span>
               <span class="text-sm font-semibold tracking-wide capitalize" :class="status.graph_store.status === 'healthy' ? 'text-emerald-600' : 'text-rose-500'">{{ status.graph_store.status }}</span>
             </div>
          </div>
          <div class="p-6 flex-1 bg-slate-50/30 dark:bg-slate-900/30">
            <div v-if="loading" class="animate-pulse space-y-5">
              <div class="h-4 bg-slate-200 dark:bg-slate-700 rounded w-full"></div>
              <div class="h-4 bg-slate-200 dark:bg-slate-700 rounded w-1/2"></div>
            </div>
            <div v-else>
              <n-descriptions :column="1" bordered size="large" class="!bg-transparent *:!bg-transparent">
                <n-descriptions-item label="实体节点 (Nodes)" label-style="font-weight: 600; color: #64748b;">
                  <span class="text-2xl font-extrabold text-purple-600 dark:text-purple-400 font-mono tracking-tight">{{ status.graph_store.total_nodes.toLocaleString() }}</span>
                </n-descriptions-item>
                <n-descriptions-item label="关联关系 (Edges)" label-style="font-weight: 600; color: #64748b;">
                  <span class="text-2xl font-extrabold text-indigo-600 dark:text-indigo-400 font-mono tracking-tight">{{ status.graph_store.total_relations.toLocaleString() }}</span>
                </n-descriptions-item>
              </n-descriptions>
            </div>
          </div>
        </div>
      </n-grid-item>
    </n-grid>

    <!-- ══ 3. Retrieval Quality Logs Table ══ -->
    <div class="relative bg-white dark:bg-slate-800 rounded-2xl shadow-[0_4px_20px_rgb(0,0,0,0.04)] border border-slate-100 dark:border-slate-700 p-6 overflow-hidden">
      <div class="mb-6 flex justify-between items-center relative z-10">
        <div>
          <h3 class="text-xl font-bold text-slate-800 dark:text-white">检索质量流水</h3>
          <p class="text-sm text-slate-400 mt-1">每一次 RAG 调用的「Query → 召回数量 → 相关度评分 → 耗时」全维度记录</p>
        </div>
        <button
          @click="fetchLogs"
          :disabled="logsLoading"
          class="px-5 py-2 rounded-xl bg-slate-900 hover:bg-slate-800 text-white dark:bg-slate-100 dark:hover:bg-white dark:text-slate-900 font-medium tracking-wide transition-all shadow-md hover:shadow-lg disabled:opacity-50 flex items-center space-x-2"
        >
          <span v-if="logsLoading" class="animate-spin block w-4 h-4 border-2 border-white/30 border-t-white dark:border-slate-900/30 dark:border-t-slate-900 rounded-full"></span>
          <span>刷新</span>
        </button>
      </div>
      
      <div v-if="logs.length === 0 && !logsLoading" class="py-16 text-center">
        <div class="w-16 h-16 mx-auto mb-4 rounded-2xl bg-slate-100 dark:bg-slate-700 flex items-center justify-center">
          <svg class="w-8 h-8 text-slate-300 dark:text-slate-500" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" /></svg>
        </div>
        <p class="text-slate-400 font-medium">暂无检索记录</p>
        <p class="text-sm text-slate-300 dark:text-slate-500 mt-1">当用户发起对话并触发 RAG 检索后，此表格将自动填充每次召回的完整细节。</p>
      </div>

      <div v-else class="overflow-x-auto rounded-xl border border-slate-100 dark:border-slate-700">
        <n-data-table
          :columns="columns"
          :data="logs"
          :loading="logsLoading"
          :pagination="pagination"
          :bordered="false"
          size="large"
          class="!bg-transparent"
        />
      </div>
    </div>
  </div>
</template>
