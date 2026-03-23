<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { getDashboardMetrics } from '@/api/admin'
import { NGrid, NGridItem, NIcon } from 'naive-ui'
import {
  PeopleOutline,
  ServerOutline,
  PulseOutline,
  TimeOutline
} from '@vicons/ionicons5'

// 模拟数据接口
interface DashboardMetrics {
  totalRequests: number;
  activeUsers: number;
  averageLatency: string;
  activeModels: number;
}

const metrics = ref<DashboardMetrics>({
  totalRequests: 0,
  activeUsers: 0,
  averageLatency: '0ms',
  activeModels: 0
})

const loading = ref(true)

const fetchMetrics = async () => {
  loading.value = true
  try {
    const res: any = await getDashboardMetrics()
    if (res.data) {
      metrics.value = res.data
    }
  } catch (error) {
    console.error('Failed to fetch metrics:', error)
  } finally {
    loading.value = false
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
      <h2 class="text-3xl font-extrabold tracking-tight text-slate-900 dark:text-white relative z-10">
        数据概览
      </h2>
      <p class="text-slate-500 dark:text-slate-400 font-medium text-lg relative z-10">
        在此监控系统的宏观运行指标与核心模型活跃情况
      </p>
    </div>

    <!-- 顶层指标卡片 -->
    <n-grid cols="1 s:2 m:4" responsive="screen" :x-gap="24" :y-gap="24" class="relative z-10">
      <n-grid-item>
        <div class="relative group h-full rounded-2xl bg-white dark:bg-slate-800 border border-slate-200/60 dark:border-slate-700 shadow-sm hover:shadow-xl hover:-translate-y-1 transition-all duration-300 p-6 overflow-hidden">
          <div class="absolute -right-4 -top-4 w-24 h-24 bg-blue-50 dark:bg-blue-900/20 rounded-full blur-2xl group-hover:scale-150 transition-transform duration-500"></div>
          <div class="flex items-center space-x-4 relative z-10">
            <div class="w-12 h-12 flex items-center justify-center rounded-2xl bg-gradient-to-br from-blue-500 to-indigo-600 text-white shadow-lg shadow-blue-500/30">
              <n-icon size="24"><ServerOutline /></n-icon>
            </div>
            <div>
              <p class="text-sm font-semibold tracking-wide text-slate-500 dark:text-slate-400 uppercase">总请求量</p>
              <h3 class="text-3xl font-black mt-1 text-slate-800 dark:text-slate-100 tabular-nums">
                <span v-if="!loading">{{ metrics.totalRequests.toLocaleString() }}</span>
                <div v-else class="h-8 bg-slate-200 dark:bg-slate-700 w-24 rounded mt-1 animate-pulse"></div>
              </h3>
            </div>
          </div>
        </div>
      </n-grid-item>
      
      <n-grid-item>
        <div class="relative group h-full rounded-2xl bg-white dark:bg-slate-800 border border-slate-200/60 dark:border-slate-700 shadow-sm hover:shadow-xl hover:-translate-y-1 transition-all duration-300 p-6 overflow-hidden">
          <div class="absolute -right-4 -top-4 w-24 h-24 bg-emerald-50 dark:bg-emerald-900/20 rounded-full blur-2xl group-hover:scale-150 transition-transform duration-500"></div>
          <div class="flex items-center space-x-4 relative z-10">
            <div class="w-12 h-12 flex items-center justify-center rounded-2xl bg-gradient-to-br from-emerald-400 to-teal-500 text-white shadow-lg shadow-emerald-500/30">
              <n-icon size="24"><PeopleOutline /></n-icon>
            </div>
            <div>
              <p class="text-sm font-semibold tracking-wide text-slate-500 dark:text-slate-400 uppercase">活跃用户</p>
              <h3 class="text-3xl font-black mt-1 text-slate-800 dark:text-slate-100 tabular-nums">
                <span v-if="!loading">{{ metrics.activeUsers.toLocaleString() }}</span>
                <div v-else class="h-8 bg-slate-200 dark:bg-slate-700 w-16 rounded mt-1 animate-pulse"></div>
              </h3>
            </div>
          </div>
        </div>
      </n-grid-item>

      <n-grid-item>
        <div class="relative group h-full rounded-2xl bg-white dark:bg-slate-800 border border-slate-200/60 dark:border-slate-700 shadow-sm hover:shadow-xl hover:-translate-y-1 transition-all duration-300 p-6 overflow-hidden">
          <div class="absolute -right-4 -top-4 w-24 h-24 bg-purple-50 dark:bg-purple-900/20 rounded-full blur-2xl group-hover:scale-150 transition-transform duration-500"></div>
          <div class="flex items-center space-x-4 relative z-10">
            <div class="w-12 h-12 flex items-center justify-center rounded-2xl bg-gradient-to-br from-purple-500 to-fuchsia-500 text-white shadow-lg shadow-purple-500/30">
              <n-icon size="24"><TimeOutline /></n-icon>
            </div>
            <div>
              <p class="text-sm font-semibold tracking-wide text-slate-500 dark:text-slate-400 uppercase">平均响应延迟</p>
              <h3 class="text-3xl font-black mt-1 text-slate-800 dark:text-slate-100 tabular-nums">
                <span v-if="!loading">{{ metrics.averageLatency }}</span>
                <div v-else class="h-8 bg-slate-200 dark:bg-slate-700 w-20 rounded mt-1 animate-pulse"></div>
              </h3>
            </div>
          </div>
        </div>
      </n-grid-item>

      <n-grid-item>
        <div class="relative group h-full rounded-2xl bg-white dark:bg-slate-800 border border-slate-200/60 dark:border-slate-700 shadow-sm hover:shadow-xl hover:-translate-y-1 transition-all duration-300 p-6 overflow-hidden">
          <div class="absolute -right-4 -top-4 w-24 h-24 bg-amber-50 dark:bg-amber-900/20 rounded-full blur-2xl group-hover:scale-150 transition-transform duration-500"></div>
          <div class="flex items-center space-x-4 relative z-10">
            <div class="w-12 h-12 flex items-center justify-center rounded-2xl bg-gradient-to-br from-amber-400 to-orange-500 text-white shadow-lg shadow-amber-500/30">
              <n-icon size="24"><PulseOutline /></n-icon>
            </div>
            <div>
              <p class="text-sm font-semibold tracking-wide text-slate-500 dark:text-slate-400 uppercase">活跃模型数</p>
              <h3 class="text-3xl font-black mt-1 text-slate-800 dark:text-slate-100 tabular-nums">
                <span v-if="!loading">{{ metrics.activeModels }}</span>
                <div v-else class="h-8 bg-slate-200 dark:bg-slate-700 w-12 rounded mt-1 animate-pulse"></div>
              </h3>
            </div>
          </div>
        </div>
      </n-grid-item>
    </n-grid>

    <div class="mt-8 rounded-3xl overflow-hidden relative shadow-[0_8px_30px_rgb(0,0,0,0.06)] bg-white dark:bg-slate-800 border border-slate-200/60 dark:border-slate-700">
      <div class="absolute inset-0 bg-gradient-to-br from-indigo-50/50 via-white to-blue-50/80 dark:from-slate-800 dark:via-slate-800 dark:to-indigo-900/20 mix-blend-multiply opacity-50 z-0 pointer-events-none"></div>
      
      <div class="relative z-10 p-10 sm:p-14 flex flex-col md:flex-row items-center justify-between">
        <div class="flex-1 text-center md:text-left">
          <div class="inline-flex items-center space-x-2 px-3 py-1 rounded-full bg-blue-100/80 dark:bg-blue-900/40 text-blue-700 dark:text-blue-300 text-sm font-semibold mb-6 shadow-sm border border-blue-200 dark:border-blue-800">
            <span class="relative flex h-2 w-2">
              <span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-blue-400 opacity-75"></span>
              <span class="relative inline-flex rounded-full h-2 w-2 bg-blue-500"></span>
            </span>
            <span>系统运行健康</span>
          </div>
          
          <h3 class="text-3xl md:text-4xl font-extrabold text-slate-800 dark:text-slate-100 tracking-tight leading-tight">
            欢迎来到<span class="text-transparent bg-clip-text bg-gradient-to-r from-blue-600 to-indigo-600 ml-2">客服控制中心</span>
          </h3>
          <p class="text-slate-500 dark:text-slate-400 mt-6 text-lg max-w-xl mx-auto md:mx-0 leading-relaxed">
            为您呈现智能客服大模型的全景数据视图。请利用左侧导航探索<span class="font-semibold text-indigo-500 dark:text-indigo-400 bg-indigo-50 dark:bg-indigo-900/30 px-2 py-0.5 rounded-md mx-1 shadow-sm">对话日志</span>与深层的<span class="font-semibold text-blue-500 dark:text-blue-400 bg-blue-50 dark:bg-blue-900/30 px-2 py-0.5 rounded-md mx-1 shadow-sm">系统监控</span>。
          </p>
        </div>
        
        <div class="mt-10 md:mt-0 flex-shrink-0 relative">
          <div class="absolute inset-0 bg-blue-500/20 blur-3xl rounded-full scale-150 animate-pulse"></div>
          <div class="w-48 h-48 md:w-64 md:h-64 relative z-10 flex items-center justify-center">
            <!-- 占位插图，使用大型图标并美化 -->
            <div class="w-full h-full bg-gradient-to-tr from-blue-100 to-indigo-50 dark:from-slate-700 dark:to-slate-800 rounded-[2rem] shadow-2xl rotate-3 hover:rotate-6 transition-transform duration-500 flex flex-col items-center justify-center border border-white dark:border-slate-600">
              <n-icon size="80" class="text-blue-500 dark:text-blue-400 drop-shadow-md mb-4"><PulseOutline /></n-icon>
              <div class="w-24 h-3 bg-blue-200 dark:bg-slate-600 rounded-full mb-2"></div>
              <div class="w-16 h-3 bg-indigo-200 dark:bg-slate-500 rounded-full"></div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
