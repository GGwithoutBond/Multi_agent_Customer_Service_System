<script setup lang="ts">
import { h, ref } from 'vue'
import { RouterLink, useRouter, useRoute } from 'vue-router'
import {
  NLayout,
  NLayoutSider,
  NMenu,
  NIcon,
  NButton
} from 'naive-ui'
import {
  HomeOutline,
  ListOutline,
  ServerOutline,
  LibraryOutline,
  LogOutOutline
} from '@vicons/ionicons5'

const router = useRouter()
const route = useRoute()

const collapsed = ref(false)

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

const handleMenuUpdate = (key: string) => {
  activeKey.value = key
  if (key === 'admin-dashboard') {
    router.push('/admin/dashboard')
  } else if (key === 'admin-models') {
    router.push('/admin/models')
  } else if (key === 'admin-middleware') {
    router.push('/admin/middleware')
  }
}

const handleLogout = () => {
  router.push('/')
}
</script>

<template>
  <div class="h-screen w-full bg-[#f8fafc] dark:bg-[#0f172a] text-slate-800 dark:text-slate-100 flex overflow-hidden selection:bg-blue-500/30">
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
      class="h-full bg-white/60 dark:bg-slate-900/60 backdrop-blur-xl border-r border-slate-200/60 dark:border-slate-800/60 shadow-[4px_0_24px_rgba(0,0,0,0.02)] z-20"
    >
      <div class="flex items-center justify-center py-8 border-b border-transparent">
        <div class="flex items-center space-x-3 transition-all duration-300">
          <div class="w-10 h-10 rounded-xl bg-gradient-to-br from-blue-500 hover:from-blue-600 to-indigo-600 shadow-lg shadow-blue-500/30 flex items-center justify-center text-white font-bold text-xl cursor-pointer hover:rotate-6 transition-transform">
            <span class="drop-shadow-sm">A</span>
          </div>
          <h1 v-if="!collapsed" class="text-xl font-extrabold tracking-tight bg-clip-text text-transparent bg-gradient-to-r from-slate-800 to-slate-500 dark:from-white dark:to-slate-400">
            Agent Admin
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
      <header class="sticky top-0 z-50 h-20 shrink-0 flex items-center justify-between px-8 bg-white/85 dark:bg-slate-900/85 backdrop-blur-xl border-b border-slate-200/60 dark:border-slate-800/60 shadow-sm">
        <div class="flex items-center space-x-4">
          <span class="text-slate-800 dark:text-slate-200 font-semibold tracking-wide text-lg drop-shadow-sm">智能体客服看板</span>
        </div>
        <div class="flex items-center space-x-4">
          <div class="w-8 h-8 rounded-full bg-slate-100 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 flex items-center justify-center text-slate-500 cursor-pointer hover:bg-slate-200 transition-colors">
            <!-- 占位符，例如日间/夜间模式切换 -->
          </div>
          <n-button quaternary circle @click="handleLogout" class="hover:bg-red-50 hover:text-red-500 transition-all">
            <template #icon>
              <n-icon size="20"><LogOutOutline /></n-icon>
            </template>
          </n-button>
        </div>
      </header>

      <!-- 主要内容区域 -->
      <main class="relative z-0 flex-1 min-h-0 p-8 overflow-y-auto w-full max-w-[1600px] mx-auto nice-scrollbar">
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
