<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { getMiddlewareStatus } from '@/api/admin'
import { NGrid, NGridItem, NDescriptions, NDescriptionsItem, NProgress } from 'naive-ui'

interface MiddlewareStatus {
  redis: {
    status: 'healthy' | 'warning' | 'error';
    memoryUsed: string;
    memoryPercentage: number;
    connections: number;
    uptime: string;
  };
  postgres: {
    status: 'healthy' | 'warning' | 'error';
    activeConnections: number;
    maxConnections: number;
    databaseSize: string;
    queriesPerSecond: number;
  };
}

const status = ref<MiddlewareStatus>({
  redis: { status: 'healthy', memoryUsed: '0MB', memoryPercentage: 0, connections: 0, uptime: '0d' },
  postgres: { status: 'healthy', activeConnections: 0, maxConnections: 100, databaseSize: '0GB', queriesPerSecond: 0 }
})

const loading = ref(true)

const fetchStatus = async () => {
  loading.value = true
  try {
    const res: any = await getMiddlewareStatus()
    if (res.data) {
      status.value = res.data
    }
  } catch (err) {
    console.error('Failed to fetch middleware status:', err)
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  fetchStatus()
})
</script>

<template>
  <div class="space-y-8 pb-10">
    <div class="flex flex-col space-y-2 relative">
      <div class="absolute -top-10 -right-10 w-40 h-40 bg-pink-400/20 blur-3xl rounded-full pointer-events-none"></div>
      <h2 class="text-3xl font-extrabold tracking-tight text-slate-900 dark:text-white relative z-10">
        底层中间件状态
      </h2>
      <p class="text-slate-500 dark:text-slate-400 font-medium text-lg relative z-10">
        多维度监控核心依赖服务（数据库、缓存）的可用性及性能水位
      </p>
    </div>

    <n-grid cols="1 l:2" responsive="screen" :x-gap="24" :y-gap="24" class="relative z-10">
      <!-- PostgreSQL Card -->
      <n-grid-item>
        <div class="h-full rounded-2xl bg-white dark:bg-slate-800 border border-slate-200/60 dark:border-slate-700 shadow-[0_4px_20px_rgb(0,0,0,0.04)] hover:shadow-xl hover:-translate-y-1 transition-all duration-300 overflow-hidden flex flex-col relative group">
          <div class="absolute top-0 right-0 w-32 h-32 bg-sky-50 dark:bg-sky-900/20 rounded-full blur-3xl opacity-50 group-hover:scale-150 transition-transform duration-700 pointer-events-none"></div>
          
          <div class="p-6 border-b border-slate-100 dark:border-slate-700/50 flex justify-between items-center relative z-10">
             <div class="flex items-center space-x-3">
               <div class="w-10 h-10 rounded-xl bg-gradient-to-br from-sky-400 to-blue-500 flex items-center justify-center text-white shadow-lg shadow-sky-500/30">
                 <!-- 图标占位 -->
                 <svg class="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                   <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4m0 5c0 2.21-3.582 4-8 4s-8-1.79-8-4" />
                 </svg>
               </div>
               <h3 class="text-xl font-bold text-slate-800 dark:text-slate-100">PostgreSQL 数据库</h3>
             </div>
             <div class="flex items-center space-x-2 bg-slate-50 dark:bg-slate-900 px-3 py-1.5 rounded-full shadow-inner border border-slate-200/50 dark:border-slate-700/50">
               <span class="relative flex h-2.5 w-2.5">
                 <span v-if="!loading && status.postgres.status === 'healthy'" class="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                 <span class="relative inline-flex rounded-full h-2.5 w-2.5" :class="status.postgres.status === 'healthy' ? 'bg-emerald-500' : 'bg-rose-500'"></span>
               </span>
               <span class="text-sm font-semibold tracking-wide capitalize" :class="status.postgres.status === 'healthy' ? 'text-emerald-600' : 'text-rose-500'">{{ status.postgres.status }}</span>
             </div>
          </div>

          <div class="p-6 flex-1 bg-slate-50/30 dark:bg-slate-900/30">
            <div v-if="loading" class="animate-pulse space-y-5">
              <div class="h-4 bg-slate-200 dark:bg-slate-700 rounded w-full"></div>
              <div class="h-4 bg-slate-200 dark:bg-slate-700 rounded w-5/6"></div>
              <div class="h-4 bg-slate-200 dark:bg-slate-700 rounded w-4/6"></div>
            </div>
            
            <div v-else class="space-y-6">
              <n-descriptions :column="1" bordered size="large" class="!bg-transparent *:!bg-transparent">
                <n-descriptions-item label="当前连接数" label-style="font-weight: 600; color: #64748b;">
                  <span class="text-lg font-medium text-slate-800 dark:text-slate-200">{{ status.postgres.activeConnections }} / {{ status.postgres.maxConnections }}</span>
                </n-descriptions-item>
                <n-descriptions-item label="数据存储用量" label-style="font-weight: 600; color: #64748b;">
                  <span class="text-lg font-medium text-slate-800 dark:text-slate-200">{{ status.postgres.databaseSize }}</span>
                </n-descriptions-item>
                <n-descriptions-item label="QPS 状态" label-style="font-weight: 600; color: #64748b;">
                  <span class="text-lg font-medium text-slate-800 dark:text-slate-200">{{ status.postgres.queriesPerSecond }} /s</span>
                </n-descriptions-item>
              </n-descriptions>
              
              <div class="pt-2">
                <div class="flex justify-between text-sm mb-2 font-medium">
                  <span class="text-slate-500">连接池水位极值占比</span>
                  <span class="text-sky-600 dark:text-sky-400 font-bold">{{ Math.round((status.postgres.activeConnections / status.postgres.maxConnections) * 100) }}%</span>
                </div>
                <n-progress
                  type="line"
                  :percentage="Math.round((status.postgres.activeConnections / status.postgres.maxConnections) * 100)"
                  :show-indicator="false"
                  :color="'#0ea5e9'"
                  :rail-color="'#e0f2fe'"
                  :height="8"
                  class="[&_.n-progress-graph-line-fill]:rounded-full [&_.n-progress-graph-line-rail]:rounded-full"
                />
              </div>
            </div>
          </div>
        </div>
      </n-grid-item>

      <!-- Redis Card -->
      <n-grid-item>
        <div class="h-full rounded-2xl bg-white dark:bg-slate-800 border border-slate-200/60 dark:border-slate-700 shadow-[0_4px_20px_rgb(0,0,0,0.04)] hover:shadow-xl hover:-translate-y-1 transition-all duration-300 overflow-hidden flex flex-col relative group">
          <div class="absolute top-0 right-0 w-32 h-32 bg-rose-50 dark:bg-rose-900/20 rounded-full blur-3xl opacity-50 group-hover:scale-150 transition-transform duration-700 pointer-events-none"></div>
          
          <div class="p-6 border-b border-slate-100 dark:border-slate-700/50 flex justify-between items-center relative z-10">
             <div class="flex items-center space-x-3">
               <div class="w-10 h-10 rounded-xl bg-gradient-to-br from-rose-400 to-red-500 flex items-center justify-center text-white shadow-lg shadow-rose-500/30">
                 <!-- 图标占位 -->
                 <svg class="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                   <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z" />
                 </svg>
               </div>
               <h3 class="text-xl font-bold text-slate-800 dark:text-slate-100">Redis 缓存服务</h3>
             </div>
             <div class="flex items-center space-x-2 bg-slate-50 dark:bg-slate-900 px-3 py-1.5 rounded-full shadow-inner border border-slate-200/50 dark:border-slate-700/50">
               <span class="relative flex h-2.5 w-2.5">
                 <span v-if="!loading && status.redis.status === 'healthy'" class="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                 <span class="relative inline-flex rounded-full h-2.5 w-2.5" :class="status.redis.status === 'healthy' ? 'bg-emerald-500' : 'bg-rose-500'"></span>
               </span>
               <span class="text-sm font-semibold tracking-wide capitalize" :class="status.redis.status === 'healthy' ? 'text-emerald-600' : 'text-rose-500'">{{ status.redis.status }}</span>
             </div>
          </div>

          <div v-if="loading" class="animate-pulse space-y-4">
             <div class="h-4 bg-gray-200 rounded w-1/2"></div>
             <div class="h-4 bg-gray-200 rounded w-3/4"></div>
          </div>
          <div class="p-6 flex-1 bg-slate-50/30 dark:bg-slate-900/30">
            <div v-if="loading" class="animate-pulse space-y-5">
              <div class="h-4 bg-slate-200 dark:bg-slate-700 rounded w-full"></div>
              <div class="h-4 bg-slate-200 dark:bg-slate-700 rounded w-1/2"></div>
              <div class="h-4 bg-slate-200 dark:bg-slate-700 rounded w-5/6"></div>
            </div>
            
            <div v-else class="space-y-6">
              <n-descriptions :column="1" bordered size="large" class="!bg-transparent *:!bg-transparent">
                <n-descriptions-item label="活动连接" label-style="font-weight: 600; color: #64748b;">
                  <span class="text-lg font-medium text-slate-800 dark:text-slate-200">{{ status.redis.connections }}</span>
                </n-descriptions-item>
                <n-descriptions-item label="当前内存占用" label-style="font-weight: 600; color: #64748b;">
                  <span class="text-lg font-medium text-slate-800 dark:text-slate-200">{{ status.redis.memoryUsed }}</span>
                </n-descriptions-item>
                <n-descriptions-item label="连续运行天数" label-style="font-weight: 600; color: #64748b;">
                  <span class="text-lg font-medium text-slate-800 dark:text-slate-200">{{ status.redis.uptime }}</span>
                </n-descriptions-item>
              </n-descriptions>
              
              <div class="pt-2">
                <div class="flex justify-between text-sm mb-2 font-medium">
                  <span class="text-slate-500">机器内存占用率预估</span>
                  <span class="text-rose-500 dark:text-rose-400 font-bold">{{ status.redis.memoryPercentage }}%</span>
                </div>
                <n-progress
                  type="line"
                  :percentage="status.redis.memoryPercentage"
                  :show-indicator="false"
                  :color="'#f43f5e'"
                  :rail-color="'#ffe4e6'"
                  :height="8"
                  class="[&_.n-progress-graph-line-fill]:rounded-full [&_.n-progress-graph-line-rail]:rounded-full"
                />
              </div>
            </div>
          </div>
        </div>
      </n-grid-item>
    </n-grid>
  </div>
</template>
