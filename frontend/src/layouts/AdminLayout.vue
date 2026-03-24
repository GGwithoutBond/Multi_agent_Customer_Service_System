<script setup lang="ts">
import { computed, h, onMounted, onUnmounted, ref, watch } from 'vue'
import { RouterLink, useRouter, useRoute } from 'vue-router'
import {
  NBadge,
  NButton,
  NIcon,
  NLayout,
  NLayoutSider,
  NList,
  NListItem,
  NMenu,
  NPopover,
  useNotification,
} from 'naive-ui'
import {
  NotificationsOutline,
  HomeOutline,
  InformationCircleOutline,
  ListOutline,
  ServerOutline,
  LibraryOutline,
  LogOutOutline
} from '@vicons/ionicons5'
import { useUserStore } from '@/stores/user'

const router = useRouter()
const route = useRoute()
const userStore = useUserStore()
const notificationApi = useNotification()

const collapsed = ref(false)
const ws = ref<WebSocket | null>(null)
const reconnectTimer = ref<number | null>(null)
const reconnectAttempts = ref(0)

interface AdminRealtimeNotification {
  id: string
  type: 'human_transfer' | 'notification'
  conversationId?: string
  userId?: string
  userMessage?: string
  urgency?: string
  sentiment?: string
  priority?: number
  createdAt: string
  unread: boolean
}

const realtimeNotifications = ref<AdminRealtimeNotification[]>([])
const unreadCount = computed(() => realtimeNotifications.value.filter(item => item.unread).length)
const isSocketConnected = ref(false)

function renderIcon(icon: any) {
  return () => h(NIcon, null, { default: () => h(icon) })
}

const menuOptions = [
  {
    label: () => h(
      RouterLink,
      {
        to: {
          name: 'admin-dashboard'
        }
      },
      { default: () => '数据概览' }
    ),
    key: 'admin-dashboard',
    icon: renderIcon(HomeOutline)
  },
  {
    label: () => h(
      RouterLink,
      {
        to: {
          name: 'admin-models'
        }
      },
      { default: () => '模型监控' }
    ),
    key: 'admin-models',
    icon: renderIcon(ListOutline)
  },
  {
    label: () => h(RouterLink, { to: { name: 'admin-middleware' } }, { default: () => '中间件状态' }),
    key: 'admin-middleware',
    icon: renderIcon(ServerOutline)
  },
  {
    label: () => h(RouterLink, { to: { name: 'admin-rag' } }, { default: () => 'RAG 引擎监控' }),
    key: 'admin-rag',
    icon: renderIcon(LibraryOutline)
  }
]

const activeKey = ref<string>((route.name as string) || 'admin-dashboard')
watch(
  () => route.name,
  (name) => {
    if (typeof name === 'string') {
      activeKey.value = name
    }
  },
)

const handleMenuUpdate = (key: string) => {
  activeKey.value = key
  if (key === 'admin-dashboard') {
    router.push('/admin/dashboard')
  } else if (key === 'admin-models') {
    router.push('/admin/models')
  } else if (key === 'admin-middleware') {
    router.push('/admin/middleware')
  } else if (key === 'admin-rag') {
    router.push('/admin/rag')
  }
}

const handleLogout = () => {
  if (ws.value) {
    ws.value.close()
    ws.value = null
  }
  if (reconnectTimer.value) {
    clearTimeout(reconnectTimer.value)
    reconnectTimer.value = null
  }
  userStore.logout()
  router.push('/login')
}

const getAdminWsUrl = () => {
  const token = localStorage.getItem('token')
  if (!token) return null
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  return `${protocol}//${window.location.host}/api/v1/ws/admin/notifications?token=${encodeURIComponent(token)}`
}

const pushRealtimeNotification = (payload: any) => {
  const item: AdminRealtimeNotification = {
    id: `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
    type: payload.type === 'human_transfer' ? 'human_transfer' : 'notification',
    conversationId: payload.conversation_id,
    userId: payload.user_id,
    userMessage: payload.user_message,
    urgency: payload.urgency,
    sentiment: payload.sentiment,
    priority: payload.priority,
    createdAt: new Date().toISOString(),
    unread: true,
  }
  realtimeNotifications.value.unshift(item)
  realtimeNotifications.value = realtimeNotifications.value.slice(0, 100)

  if (item.type === 'human_transfer') {
    notificationApi.warning({
      title: '转人工通知',
      content: `会话 ${item.conversationId || '-'}，优先级 ${item.priority ?? '-'}`,
      duration: 5000,
    })
  }
}

const scheduleReconnect = () => {
  if (reconnectTimer.value) return
  const wait = Math.min(10000, 1000 * (reconnectAttempts.value + 1))
  reconnectTimer.value = window.setTimeout(() => {
    reconnectTimer.value = null
    reconnectAttempts.value += 1
    connectAdminNotifications()
  }, wait)
}

const connectAdminNotifications = () => {
  const wsUrl = getAdminWsUrl()
  if (!wsUrl) return

  try {
    ws.value = new WebSocket(wsUrl)
  } catch (_err) {
    scheduleReconnect()
    return
  }

  ws.value.onopen = () => {
    reconnectAttempts.value = 0
    isSocketConnected.value = true
  }

  ws.value.onmessage = (event) => {
    try {
      const payload = JSON.parse(event.data)
      if (payload.type === 'connected' || payload.type === 'pong') return
      pushRealtimeNotification(payload)
    } catch (_err) {
      // ignore malformed payload
    }
  }

  ws.value.onclose = () => {
    isSocketConnected.value = false
    ws.value = null
    scheduleReconnect()
  }

  ws.value.onerror = () => {
    isSocketConnected.value = false
  }
}

const markAllRead = () => {
  realtimeNotifications.value = realtimeNotifications.value.map(item => ({ ...item, unread: false }))
}

onMounted(() => {
  connectAdminNotifications()
})

onUnmounted(() => {
  if (reconnectTimer.value) {
    clearTimeout(reconnectTimer.value)
  }
  if (ws.value) {
    ws.value.close()
    ws.value = null
  }
})
</script>

<template>
  <div class="admin-shell h-screen w-full flex overflow-hidden">
    <!-- 侧边栏 -->
    <n-layout-sider
      bordered
      collapse-mode="width"
      :collapsed-width="72"
      :width="260"
      :collapsed="collapsed"
      show-trigger="bar"
      @collapse="collapsed = true"
      @expand="collapsed = false"
      class="h-full admin-sider z-20"
    >
      <div class="flex items-center justify-center py-8 border-b border-transparent">
        <div class="flex items-center space-x-3 transition-all duration-300">
          <div class="admin-logo-badge">
            <span class="drop-shadow-sm">A</span>
          </div>
          <h1 v-if="!collapsed" class="admin-logo-text">
            客服控制台
          </h1>
        </div>
      </div>
      
      <n-menu
        :collapsed="collapsed"
        :collapsed-width="64"
        :collapsed-icon-size="22"
        :options="menuOptions"
        :value="activeKey"
        @update:value="handleMenuUpdate"
        class="mt-4"
      />
    </n-layout-sider>

    <n-layout class="bg-transparent flex-1 h-full flex flex-col relative isolate">
      <!-- 顶部通知/导航栏 -->
      <header class="admin-header sticky top-0 z-50 h-20 shrink-0 flex items-center justify-between px-8 shadow-sm">
        <div class="flex items-center space-x-4">
          <span class="admin-title font-semibold tracking-wide text-lg drop-shadow-sm">智能体客服看板</span>
        </div>
        <div class="flex items-center space-x-4">
          <n-popover trigger="click" placement="bottom-end" @update:show="(show) => { if (show) markAllRead() }">
            <template #trigger>
              <n-button quaternary circle :title="isSocketConnected ? '实时通知已连接' : '实时通知重连中'">
                <template #icon>
                  <n-badge :value="unreadCount" :max="99" :show="unreadCount > 0">
                    <n-icon size="20"><NotificationsOutline /></n-icon>
                  </n-badge>
                </template>
              </n-button>
            </template>
            <div class="notify-panel">
              <div class="notify-header">
                <span>实时通知</span>
                <span :class="isSocketConnected ? 'notify-status-online' : 'notify-status-offline'">
                  {{ isSocketConnected ? '已连接' : '重连中' }}
                </span>
              </div>
              <n-list v-if="realtimeNotifications.length > 0" hoverable clickable>
                <n-list-item v-for="item in realtimeNotifications.slice(0, 20)" :key="item.id">
                  <div class="notify-item">
                    <div class="notify-item-title">
                      <n-icon :size="16"><InformationCircleOutline /></n-icon>
                      <span>{{ item.type === 'human_transfer' ? '转人工通知' : '系统通知' }}</span>
                    </div>
                    <div class="notify-item-desc">
                      会话: {{ item.conversationId || '-' }} | 优先级: {{ item.priority ?? '-' }}
                    </div>
                    <div class="notify-item-time">{{ new Date(item.createdAt).toLocaleString() }}</div>
                  </div>
                </n-list-item>
              </n-list>
              <div v-else class="notify-empty">暂无实时通知</div>
            </div>
          </n-popover>

          <n-button quaternary circle @click="handleLogout" class="hover:bg-red-50 hover:text-red-500 transition-all" title="退出登录">
            <template #icon>
              <n-icon size="20"><LogOutOutline /></n-icon>
            </template>
          </n-button>
        </div>
      </header>

      <!-- 主要内容区域 -->
      <main class="relative z-0 flex-1 min-h-0 p-8 overflow-y-auto w-full max-w-[1600px] mx-auto nice-scrollbar ds-scrollbar">
        <router-view v-slot="{ Component }">
          <transition name="fade" mode="out-in">
            <component :is="Component" />
          </transition>
        </router-view>
      </main>
    </n-layout>
  </div>
</template>

<style>
.admin-shell {
  background: radial-gradient(circle at top left, #e9efff 0%, var(--ds-bg-page) 45%);
  color: var(--ds-text-primary);
}

.admin-sider {
  background: rgba(255, 255, 255, 0.82) !important;
  backdrop-filter: blur(14px);
  border-right: 1px solid var(--ds-border);
  box-shadow: 4px 0 24px rgba(0, 0, 0, 0.03);
}

.admin-logo-badge {
  width: 40px;
  height: 40px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  font-size: 20px;
  color: #fff;
  cursor: pointer;
  background: linear-gradient(135deg, var(--ds-brand), #7b4fff);
  box-shadow: 0 10px 18px rgba(44, 107, 255, 0.28);
  transition: transform var(--ds-duration-fast) ease;
}

.admin-logo-badge:hover {
  transform: rotate(6deg);
}

.admin-logo-text {
  font-size: 20px;
  font-weight: 800;
  letter-spacing: -0.02em;
  color: var(--ds-text-primary);
}

.admin-header {
  background: rgba(255, 255, 255, 0.84);
  backdrop-filter: blur(12px);
  border-bottom: 1px solid var(--ds-border);
}

.admin-title {
  color: var(--ds-text-primary);
}

.notify-panel {
  width: 360px;
  max-height: 420px;
  overflow: auto;
}

.notify-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 13px;
  font-weight: 600;
  margin-bottom: 10px;
}

.notify-status-online {
  color: #16a34a;
}

.notify-status-offline {
  color: #ef4444;
}

.notify-item-title {
  display: flex;
  align-items: center;
  gap: 6px;
  font-weight: 600;
  color: var(--ds-text-primary);
}

.notify-item-desc {
  margin-top: 4px;
  font-size: 12px;
  color: var(--ds-text-secondary);
}

.notify-item-time {
  margin-top: 4px;
  font-size: 11px;
  color: var(--ds-text-tertiary);
}

.notify-empty {
  padding: 18px 8px;
  text-align: center;
  color: var(--ds-text-tertiary);
  font-size: 12px;
}

/* 覆盖 NaiveUI 的背景 */
.n-layout-sider, .n-layout, .n-menu {
  background-color: transparent !important;
}

/* 优雅滚动条 */
.nice-scrollbar::-webkit-scrollbar {
  width: 6px;
  height: 6px;
}
.nice-scrollbar::-webkit-scrollbar-track {
  background: transparent;
}
.nice-scrollbar::-webkit-scrollbar-thumb {
  background: #cbd5e1;
  border-radius: 4px;
}
.nice-scrollbar::-webkit-scrollbar-thumb:hover {
  background: #94a3b8;
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.3s ease, transform 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}
.fade-enter-from {
  opacity: 0;
  transform: translateY(10px) scale(0.99);
}
.fade-leave-to {
  opacity: 0;
  transform: translateY(-10px) scale(0.99);
}
</style>
