<script setup lang="ts">
import { computed, ref, onMounted } from 'vue'
import { getDashboardMetrics } from '@/api/admin'
import { NGrid, NGridItem, NIcon } from 'naive-ui'
import {
  PeopleOutline,
  ServerOutline,
  PulseOutline,
  TimeOutline,
} from '@vicons/ionicons5'
import UIState from '@/components/common/UIState.vue'
import type { UIStateType } from '@/types/ui-state'

interface DashboardMetrics {
  totalRequests: number
  activeUsers: number
  averageLatency: string
  activeModels: number
}

const metrics = ref<DashboardMetrics>({
  totalRequests: 0,
  activeUsers: 0,
  averageLatency: '0ms',
  activeModels: 0,
})

const pageState = ref<UIStateType>('loading')

const hasData = computed(() => {
  return metrics.value.totalRequests > 0 || metrics.value.activeUsers > 0 || metrics.value.activeModels > 0
})

const fetchMetrics = async () => {
  pageState.value = 'loading'
  try {
    const res: any = await getDashboardMetrics()
    if (res?.data) {
      metrics.value = res.data
    }
    pageState.value = hasData.value ? 'retry' : 'empty'
  } catch (error) {
    console.error('Failed to fetch metrics:', error)
    pageState.value = 'error'
  }
}

onMounted(() => {
  fetchMetrics()
})
</script>

<template>
  <div class="space-y-8 pb-10">
    <div class="flex flex-col space-y-2 relative">
      <div class="absolute -top-10 -left-10 w-40 h-40 bg-blue-400/20 blur-3xl rounded-full pointer-events-none"></div>
      <h2 class="text-3xl font-extrabold tracking-tight text-slate-900 relative z-10">数据总览</h2>
      <p class="text-slate-500 font-medium text-lg relative z-10">查看系统总体请求量、活跃用户、响应耗时和模型活跃情况。</p>
    </div>

    <UIState
      v-if="pageState === 'loading'"
      type="loading"
      title="正在加载指标数据"
      description="请稍候，我们正在同步最新统计。"
      action-text=""
    />

    <UIState
      v-else-if="pageState === 'error'"
      type="error"
      title="数据加载失败"
      description="暂时无法获取监控指标，请稍后重试。"
      action-text="重试"
      @action="fetchMetrics"
    />

    <UIState
      v-else-if="pageState === 'empty'"
      type="empty"
      title="暂无统计数据"
      description="当前还没有可展示的指标，稍后刷新看看。"
      action-text="刷新"
      @action="fetchMetrics"
    />

    <template v-else>
      <n-grid cols="1 s:2 m:4" responsive="screen" :x-gap="24" :y-gap="24" class="relative z-10">
        <n-grid-item>
          <div class="metric-card">
            <div class="metric-card-glow bg-blue-50"></div>
            <div class="metric-card-content">
              <div class="metric-icon bg-gradient-to-br from-blue-500 to-indigo-600 shadow-blue-500/30">
                <n-icon size="24"><ServerOutline /></n-icon>
              </div>
              <div>
                <p class="metric-label">总请求量</p>
                <h3 class="metric-value">{{ metrics.totalRequests.toLocaleString() }}</h3>
              </div>
            </div>
          </div>
        </n-grid-item>

        <n-grid-item>
          <div class="metric-card">
            <div class="metric-card-glow bg-emerald-50"></div>
            <div class="metric-card-content">
              <div class="metric-icon bg-gradient-to-br from-emerald-400 to-teal-500 shadow-emerald-500/30">
                <n-icon size="24"><PeopleOutline /></n-icon>
              </div>
              <div>
                <p class="metric-label">活跃用户</p>
                <h3 class="metric-value">{{ metrics.activeUsers.toLocaleString() }}</h3>
              </div>
            </div>
          </div>
        </n-grid-item>

        <n-grid-item>
          <div class="metric-card">
            <div class="metric-card-glow bg-purple-50"></div>
            <div class="metric-card-content">
              <div class="metric-icon bg-gradient-to-br from-purple-500 to-fuchsia-500 shadow-purple-500/30">
                <n-icon size="24"><TimeOutline /></n-icon>
              </div>
              <div>
                <p class="metric-label">平均响应耗时</p>
                <h3 class="metric-value">{{ metrics.averageLatency }}</h3>
              </div>
            </div>
          </div>
        </n-grid-item>

        <n-grid-item>
          <div class="metric-card">
            <div class="metric-card-glow bg-amber-50"></div>
            <div class="metric-card-content">
              <div class="metric-icon bg-gradient-to-br from-amber-400 to-orange-500 shadow-amber-500/30">
                <n-icon size="24"><PulseOutline /></n-icon>
              </div>
              <div>
                <p class="metric-label">活跃模型数</p>
                <h3 class="metric-value">{{ metrics.activeModels }}</h3>
              </div>
            </div>
          </div>
        </n-grid-item>
      </n-grid>

      <div class="mt-8 rounded-3xl overflow-hidden relative shadow-[0_8px_30px_rgb(0,0,0,0.06)] bg-white border border-slate-200/60">
        <div class="absolute inset-0 bg-gradient-to-br from-indigo-50/50 via-white to-blue-50/80 opacity-50 z-0 pointer-events-none"></div>
        <div class="relative z-10 p-10 sm:p-14 flex flex-col md:flex-row items-center justify-between">
          <div class="flex-1 text-center md:text-left">
            <div class="inline-flex items-center space-x-2 px-3 py-1 rounded-full bg-blue-100/80 text-blue-700 text-sm font-semibold mb-6 shadow-sm border border-blue-200">
              <span class="relative flex h-2 w-2">
                <span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-blue-400 opacity-75"></span>
                <span class="relative inline-flex rounded-full h-2 w-2 bg-blue-500"></span>
              </span>
              <span>系统运行健康</span>
            </div>

            <h3 class="text-3xl md:text-4xl font-extrabold text-slate-800 tracking-tight leading-tight">
              欢迎来到 <span class="text-transparent bg-clip-text bg-gradient-to-r from-blue-600 to-indigo-600">客服控制中心</span>
            </h3>
            <p class="text-slate-500 mt-6 text-lg max-w-xl mx-auto md:mx-0 leading-relaxed">
              你可以通过左侧导航查看模型调用日志、中间件健康状态和 RAG 检索质量，快速定位异常并优化服务体验。
            </p>
          </div>

          <div class="mt-10 md:mt-0 flex-shrink-0 relative">
            <div class="absolute inset-0 bg-blue-500/20 blur-3xl rounded-full scale-150 animate-pulse"></div>
            <div class="w-48 h-48 md:w-64 md:h-64 relative z-10 flex items-center justify-center">
              <div class="w-full h-full bg-gradient-to-tr from-blue-100 to-indigo-50 rounded-[2rem] shadow-2xl rotate-3 hover:rotate-6 transition-transform duration-500 flex flex-col items-center justify-center border border-white">
                <n-icon size="80" class="text-blue-500 drop-shadow-md mb-4"><PulseOutline /></n-icon>
                <div class="w-24 h-3 bg-blue-200 rounded-full mb-2"></div>
                <div class="w-16 h-3 bg-indigo-200 rounded-full"></div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<style scoped>
.metric-card {
  position: relative;
  height: 100%;
  border-radius: 1rem;
  background: #fff;
  border: 1px solid rgba(226, 232, 240, 0.8);
  box-shadow: 0 1px 4px rgba(15, 23, 42, 0.05);
  padding: 1.5rem;
  overflow: hidden;
  transition: all var(--ds-duration-base) var(--ds-ease-standard);
}

.metric-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 14px 28px rgba(15, 23, 42, 0.12);
}

.metric-card-glow {
  position: absolute;
  width: 6rem;
  height: 6rem;
  top: -1.5rem;
  right: -1.2rem;
  border-radius: 999px;
  filter: blur(30px);
  transition: transform var(--ds-duration-slow) var(--ds-ease-standard);
}

.metric-card:hover .metric-card-glow {
  transform: scale(1.4);
}

.metric-card-content {
  position: relative;
  z-index: 1;
  display: flex;
  align-items: center;
  gap: 1rem;
}

.metric-icon {
  width: 3rem;
  height: 3rem;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 1rem;
  color: #fff;
  box-shadow: 0 10px 20px;
}

.metric-label {
  font-size: 0.75rem;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: #64748b;
}

.metric-value {
  margin-top: 0.25rem;
  font-size: 1.9rem;
  font-weight: 900;
  color: #0f172a;
  font-variant-numeric: tabular-nums;
}
</style>
