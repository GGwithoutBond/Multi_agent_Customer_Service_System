<script setup lang="ts">
import { computed, ref, onMounted } from 'vue'
import { getMiddlewareStatus } from '@/api/admin'
import { NGrid, NGridItem, NDescriptions, NDescriptionsItem, NProgress } from 'naive-ui'
import UIState from '@/components/common/UIState.vue'
import type { UIStateType } from '@/types/ui-state'

interface MiddlewareStatus {
  redis: {
    status: 'healthy' | 'warning' | 'error'
    memoryUsed: string
    memoryPercentage: number
    connections: number
    uptime: string
  }
  postgres: {
    status: 'healthy' | 'warning' | 'error'
    activeConnections: number
    maxConnections: number
    databaseSize: string
    queriesPerSecond: number
  }
}

const status = ref<MiddlewareStatus>({
  redis: { status: 'healthy', memoryUsed: '0MB', memoryPercentage: 0, connections: 0, uptime: '0d' },
  postgres: { status: 'healthy', activeConnections: 0, maxConnections: 100, databaseSize: '0GB', queriesPerSecond: 0 },
})

const pageState = ref<UIStateType>('loading')
const descriptionLabelStyle = 'font-weight: 600; color: var(--ds-text-secondary);'

const postgresConnRate = computed(() => {
  if (!status.value.postgres.maxConnections) return 0
  return Math.round((status.value.postgres.activeConnections / status.value.postgres.maxConnections) * 100)
})

const fetchStatus = async () => {
  pageState.value = 'loading'
  try {
    const res: any = await getMiddlewareStatus()
    if (res?.data) {
      status.value = res.data
    }
    pageState.value = 'retry'
  } catch (err) {
    console.error('Failed to fetch middleware status:', err)
    pageState.value = 'error'
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
      <h2 class="text-3xl font-extrabold tracking-tight text-slate-900 relative z-10">中间件状态</h2>
      <p class="text-slate-500 font-medium text-lg relative z-10">监控数据库与缓存服务可用性，快速判断核心依赖健康度。</p>
    </div>

    <UIState
      v-if="pageState === 'loading'"
      type="loading"
      title="正在加载中间件状态"
      description="请稍候，我们正在同步最新健康检查结果。"
    />

    <UIState
      v-else-if="pageState === 'error'"
      type="error"
      title="中间件状态加载失败"
      description="无法获取 Redis / PostgreSQL 数据，请重试。"
      action-text="重试"
      @action="fetchStatus"
    />

    <n-grid v-else cols="1 l:2" responsive="screen" :x-gap="24" :y-gap="24" class="relative z-10">
      <n-grid-item>
        <div class="service-card group">
          <div class="service-glow bg-sky-50"></div>

          <div class="service-header">
            <div class="service-header-left">
              <div class="service-icon bg-gradient-to-br from-sky-400 to-blue-500 shadow-sky-500/30">
                <svg class="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4m0 5c0 2.21-3.582 4-8 4s-8-1.79-8-4" />
                </svg>
              </div>
              <h3 class="text-xl font-bold text-slate-800">PostgreSQL 数据库</h3>
            </div>
            <div class="status-pill">
              <span class="status-dot" :class="status.postgres.status === 'healthy' ? 'dot-ok' : 'dot-error'"></span>
              <span class="text-sm font-semibold tracking-wide capitalize" :class="status.postgres.status === 'healthy' ? 'text-emerald-600' : 'text-rose-500'">{{ status.postgres.status }}</span>
            </div>
          </div>

          <div class="service-body">
            <n-descriptions :column="1" bordered size="large" class="!bg-transparent *:!bg-transparent">
              <n-descriptions-item label="当前连接数" :label-style="descriptionLabelStyle">
                <span class="text-lg font-medium text-slate-800">{{ status.postgres.activeConnections }} / {{ status.postgres.maxConnections }}</span>
              </n-descriptions-item>
              <n-descriptions-item label="数据库大小" :label-style="descriptionLabelStyle">
                <span class="text-lg font-medium text-slate-800">{{ status.postgres.databaseSize }}</span>
              </n-descriptions-item>
              <n-descriptions-item label="QPS" :label-style="descriptionLabelStyle">
                <span class="text-lg font-medium text-slate-800">{{ status.postgres.queriesPerSecond }} /s</span>
              </n-descriptions-item>
            </n-descriptions>

            <div class="pt-2">
              <div class="flex justify-between text-sm mb-2 font-medium">
                <span class="text-slate-500">连接池占用率</span>
                <span class="text-sky-600 font-bold">{{ postgresConnRate }}%</span>
              </div>
              <n-progress
                type="line"
                :percentage="postgresConnRate"
                :show-indicator="false"
                :color="'#0ea5e9'"
                :rail-color="'#e0f2fe'"
                :height="8"
                class="[&_.n-progress-graph-line-fill]:rounded-full [&_.n-progress-graph-line-rail]:rounded-full"
              />
            </div>
          </div>
        </div>
      </n-grid-item>

      <n-grid-item>
        <div class="service-card group">
          <div class="service-glow bg-rose-50"></div>

          <div class="service-header">
            <div class="service-header-left">
              <div class="service-icon bg-gradient-to-br from-rose-400 to-red-500 shadow-rose-500/30">
                <svg class="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z" />
                </svg>
              </div>
              <h3 class="text-xl font-bold text-slate-800">Redis 缓存服务</h3>
            </div>
            <div class="status-pill">
              <span class="status-dot" :class="status.redis.status === 'healthy' ? 'dot-ok' : 'dot-error'"></span>
              <span class="text-sm font-semibold tracking-wide capitalize" :class="status.redis.status === 'healthy' ? 'text-emerald-600' : 'text-rose-500'">{{ status.redis.status }}</span>
            </div>
          </div>

          <div class="service-body">
            <n-descriptions :column="1" bordered size="large" class="!bg-transparent *:!bg-transparent">
              <n-descriptions-item label="活动连接" :label-style="descriptionLabelStyle">
                <span class="text-lg font-medium text-slate-800">{{ status.redis.connections }}</span>
              </n-descriptions-item>
              <n-descriptions-item label="内存占用" :label-style="descriptionLabelStyle">
                <span class="text-lg font-medium text-slate-800">{{ status.redis.memoryUsed }}</span>
              </n-descriptions-item>
              <n-descriptions-item label="连续运行时长" :label-style="descriptionLabelStyle">
                <span class="text-lg font-medium text-slate-800">{{ status.redis.uptime }}</span>
              </n-descriptions-item>
            </n-descriptions>

            <div class="pt-2">
              <div class="flex justify-between text-sm mb-2 font-medium">
                <span class="text-slate-500">内存占用率</span>
                <span class="text-rose-500 font-bold">{{ status.redis.memoryPercentage }}%</span>
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
      </n-grid-item>
    </n-grid>
  </div>
</template>

<style scoped>
.service-card {
  height: 100%;
  border-radius: 1rem;
  background: #fff;
  border: 1px solid rgba(226, 232, 240, 0.7);
  box-shadow: 0 4px 20px rgba(15, 23, 42, 0.04);
  overflow: hidden;
  display: flex;
  flex-direction: column;
  position: relative;
  transition: all var(--ds-duration-base) var(--ds-ease-standard);
}

.service-card:hover {
  box-shadow: 0 16px 30px rgba(15, 23, 42, 0.12);
  transform: translateY(-4px);
}

.service-glow {
  position: absolute;
  top: 0;
  right: 0;
  width: 8rem;
  height: 8rem;
  border-radius: 999px;
  filter: blur(30px);
  opacity: 0.5;
  transition: transform var(--ds-duration-slow) var(--ds-ease-standard);
  pointer-events: none;
}

.service-card:hover .service-glow {
  transform: scale(1.3);
}

.service-header {
  padding: 1.5rem;
  border-bottom: 1px solid rgba(226, 232, 240, 0.7);
  display: flex;
  justify-content: space-between;
  align-items: center;
  position: relative;
  z-index: 1;
}

.service-header-left {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.service-icon {
  width: 2.5rem;
  height: 2.5rem;
  border-radius: 0.75rem;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  box-shadow: 0 10px 20px;
}

.status-pill {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  background: #f8fafc;
  border-radius: 999px;
  border: 1px solid rgba(226, 232, 240, 0.8);
  padding: 0.4rem 0.75rem;
}

.status-dot {
  display: inline-block;
  width: 0.625rem;
  height: 0.625rem;
  border-radius: 50%;
}

.dot-ok {
  background: #10b981;
}

.dot-error {
  background: #f43f5e;
}

.service-body {
  padding: 1.5rem;
  flex: 1;
  background: linear-gradient(180deg, rgba(248, 250, 252, 0.35), rgba(241, 245, 249, 0.15));
}
</style>
