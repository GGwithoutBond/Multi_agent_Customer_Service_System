<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useMessage, NIcon, NAvatar, NDropdown, NCheckbox } from 'naive-ui'
import {
  MenuOutline,
  SearchOutline,
  CreateOutline,
  SettingsOutline,
  TrashOutline
} from '@vicons/ionicons5'
import { getConversations, deleteConversation } from '@/api/conversation'
import { useUserStore } from '@/stores/user'

const router = useRouter()
const message = useMessage()
const userStore = useUserStore()

const isSidebarOpen = ref(true)
const conversations = ref<any[]>([])
const searchQuery = ref('')
const selectedIds = ref<string[]>([])
const isDeleting = ref(false)

const userName = computed(() => userStore.user?.name || 'User')

// 侧边栏底部设置
const settingsOptions = [
  { label: '退出登录 (Logout)', key: 'logout' }
]

const handleSettingsSelect = (key: string) => {
  if (key === 'logout') {
    userStore.logout()
    router.push('/login')
  }
}

const toggleSidebar = () => {
  isSidebarOpen.value = !isSidebarOpen.value
}

const handleNewChat = () => {
  router.push('/')
}

const handleSelectChat = (id: string) => {
  router.push(`/chat/${id}`)
}

const fetchConversationList = async () => {
  try {
    const res: any = await getConversations()
    conversations.value = Array.isArray(res) ? res : (res.data || [])
  } catch (error) {
    console.error('获取历史会话失败', error)
  }
}

const filteredConversations = computed(() => {
  if (!searchQuery.value) return conversations.value
  const q = searchQuery.value.toLowerCase()
  return conversations.value.filter(c => (c.title || '').toLowerCase().includes(q))
})

const formatDate = (dateString?: string) => {
  if (!dateString) return ''
  const date = new Date(dateString)
  return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: date.getFullYear() !== new Date().getFullYear() ? 'numeric' : undefined })
}

const toggleSelectAll = (checked: boolean) => {
  if (checked) {
    selectedIds.value = filteredConversations.value.map(c => c.id)
  } else {
    selectedIds.value = []
  }
}

const toggleSelection = (id: string, checked: boolean) => {
  if (checked) {
    if (!selectedIds.value.includes(id)) {
      selectedIds.value.push(id)
    }
  } else {
    selectedIds.value = selectedIds.value.filter(v => v !== id)
  }
}

const isAllSelected = computed(() => {
  return filteredConversations.value.length > 0 && selectedIds.value.length === filteredConversations.value.length
})

const isIndeterminate = computed(() => {
  return selectedIds.value.length > 0 && selectedIds.value.length < filteredConversations.value.length
})

const handleBatchDelete = async () => {
  if (selectedIds.value.length === 0) return
  if (!window.confirm(`确定要删除选中的 ${selectedIds.value.length} 个对话吗？此操作不可恢复。`)) return

  isDeleting.value = true
  try {
    for (const id of selectedIds.value) {
      await deleteConversation(id)
    }
    message.success('批量删除成功')
    selectedIds.value = []
    await fetchConversationList()
  } catch (err: any) {
    console.error(err)
    message.error('删除过程中出现错误')
  } finally {
    isDeleting.value = false
  }
}

onMounted(() => {
  fetchConversationList()
})
</script>

<template>
  <div class="app-layout">
    <!-- 侧边栏 (Gemini Layout) -->
    <div class="sidebar-wrapper" :class="{ 'is-collapsed': !isSidebarOpen }">
      <div class="sidebar-header">
        <div class="menu-btn" @click="toggleSidebar">
          <n-icon :size="20"><MenuOutline /></n-icon>
        </div>
        <div class="menu-btn" style="margin-left:4px;" title="搜索" @click="router.push('/search')">
          <n-icon :size="18"><SearchOutline /></n-icon>
        </div>
      </div>
      
      <div class="sidebar-content" v-show="isSidebarOpen">
        <!-- 第一个大按钮 -->
        <div class="new-chat-btn" @click="handleNewChat" style="margin-left: -4px;">
          <n-icon :size="18"><CreateOutline /></n-icon>
          <span>New chat</span>
        </div>
        
        <!-- Chats List -->
        <div class="sidebar-menu-header">
          <span>Chats</span>
        </div>
        <div class="chat-history-list">
          <div
            v-for="convo in conversations.slice(0, 15)"
            :key="convo.id"
            class="history-item"
            @click="handleSelectChat(convo.id)"
          >
            <span class="history-title">{{ convo.title || '新对话' }}</span>
          </div>
        </div>
        
        <!-- Bottom Settings & Avatar -->
        <div class="sidebar-bottom">
          <div class="sidebar-menu-item" style="padding-left: 8px;">
            <n-avatar round :size="24" class="user-avatar" style="background-color: #9b72cb;">{{ userName.slice(0, 1) }}</n-avatar>
            <span style="font-weight: 500; color: #1f1f1f;">{{ userName }}</span>
          </div>

          <n-dropdown :options="settingsOptions" placement="top-start" @select="handleSettingsSelect">
            <div class="sidebar-menu-item">
              <n-icon :size="18" class="icon"><SettingsOutline /></n-icon>
              <span>Settings & help</span>
            </div>
          </n-dropdown>
        </div>
      </div>
    </div>

    <!-- 主搜索区 -->
    <div class="search-container">
      <!-- 顶部 Header -->
      <div class="top-nav">
        <div class="nav-left">
          <div class="menu-btn" @click="toggleSidebar" v-if="!isSidebarOpen">
            <n-icon :size="20"><MenuOutline /></n-icon>
          </div>
          <span class="gemini-logo">AI 客服助手</span>
        </div>
      </div>

      <!-- 搜索核心区域 -->
      <div class="search-content">
        <h1 class="search-title">Search</h1>
        
        <div class="search-input-wrapper">
          <n-icon :size="20" class="search-icon"><SearchOutline /></n-icon>
          <input 
            type="text" 
            class="search-input" 
            placeholder="Search for chats" 
            v-model="searchQuery"
          />
        </div>

        <div class="recent-section" v-if="filteredConversations.length > 0">
          <div class="section-header">
            <div class="header-left">
              <n-checkbox 
                :checked="isAllSelected" 
                :indeterminate="isIndeterminate" 
                @update:checked="toggleSelectAll"
              />
              <span>Recent</span>
            </div>
            <div class="header-right">
              <div class="delete-btn" :class="{ disabled: selectedIds.length === 0, loading: isDeleting }" @click="handleBatchDelete">
                <n-icon :size="16"><TrashOutline /></n-icon>
                <span>批量删除</span>
              </div>
            </div>
          </div>

          <div class="list-container">
            <div v-for="convo in filteredConversations" :key="convo.id" class="list-item">
              <div class="item-left">
                <n-checkbox 
                  :checked="selectedIds.includes(convo.id)" 
                  @update:checked="(checked) => toggleSelection(convo.id, checked)"
                />
                <span class="item-title" @click="handleSelectChat(convo.id)">{{ convo.title || '新对话' }}</span>
              </div>
              <div class="item-right">
                <span class="item-date">{{ formatDate(convo.updated_at || convo.created_at) }}</span>
              </div>
            </div>
          </div>
        </div>
        <div v-else class="empty-state">
           No matching chats found.
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
/* App Layout Container - from Chat.vue */
.app-layout {
  display: flex;
  height: 100vh;
  width: 100vw;
  overflow: hidden;
  background-color: #f0f4f9;
}

/* ===== 侧边栏 Sidebar ===== */
.sidebar-wrapper {
  width: 280px;
  background-color: #f0f4f9;
  display: flex;
  flex-direction: column;
  transition: width 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  overflow: hidden;
  flex-shrink: 0;
}

.sidebar-wrapper.is-collapsed {
  width: 0;
}

.sidebar-header {
  padding: 16px;
  display: flex;
  align-items: center;
}

.menu-btn {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  color: #444746;
  transition: background-color 0.2s;
}

.menu-btn:hover {
  background-color: #dfe4ea;
}

.sidebar-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  padding: 0 16px 16px 16px;
  overflow-y: auto;
}

.sidebar-content::-webkit-scrollbar {
  width: 6px;
}
.sidebar-content::-webkit-scrollbar-thumb {
  background: #c7c7c7;
  border-radius: 3px;
}

/* Sidebar Buttons */
.new-chat-btn {
  background-color: #e3e8ee;
  border-radius: 16px;
  display: inline-flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  margin-bottom: 24px;
  width: max-content;
  color: #1f1f1f;
  font-weight: 500;
  font-size: 14px;
  cursor: pointer;
  transition: background-color 0.2s;
}

.new-chat-btn:hover {
  background-color: #d3d9e0;
}

.sidebar-menu-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 12px;
  border-radius: 12px;
  color: #444746;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  margin-bottom: 8px;
  transition: background-color 0.2s;
}

.sidebar-menu-item:hover {
  background-color: #e3e8ee;
}

.sidebar-menu-header {
  padding: 12px;
  color: #444746;
  font-size: 13px;
  font-weight: 600;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.chat-history-list {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.history-item {
  padding: 10px 12px;
  border-radius: 12px;
  color: #444746;
  font-size: 14px;
  cursor: pointer;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  margin-bottom: 2px;
  transition: background-color 0.2s;
}

.history-item:hover {
  background-color: #e3e8ee;
}

.sidebar-bottom {
  margin-top: auto;
  padding-top: 16px;
}

/* ===== Search 主区 ===== */
.search-container {
  flex: 1;
  display: flex;
  flex-direction: column;
  background-color: #ffffff;
  position: relative;
  overflow: hidden;
  border-radius: 16px 0 0 16px;
}

.top-nav {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 24px;
}

.nav-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.gemini-logo {
  font-size: 20px;
  font-weight: 400;
  color: #5f6368;
}

.search-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  padding-top: 4vh;
  overflow-y: auto;
}

.search-title {
  font-size: 28px;
  font-weight: 400;
  color: #1f1f1f;
  margin-bottom: 24px;
}

.search-input-wrapper {
  width: 90%;
  max-width: 720px;
  display: flex;
  align-items: center;
  background-color: #ffffff;
  border: 1px solid #dadce0;
  border-radius: 24px;
  padding: 12px 20px;
  transition: box-shadow 0.2s;
  margin-bottom: 40px;
}

.search-input-wrapper:focus-within {
  box-shadow: 0 1px 6px rgba(32, 33, 36, 0.28);
  border-color: transparent;
}

.search-icon {
  color: #5f6368;
  margin-right: 12px;
}

.search-input {
  flex: 1;
  border: none;
  outline: none;
  font-size: 16px;
  color: #1f1f1f;
  background: transparent;
}

.search-input::placeholder {
  color: #5f6368;
}

.recent-section {
  width: 90%;
  max-width: 720px;
  display: flex;
  flex-direction: column;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
  padding: 0 12px;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 16px;
  font-size: 14px;
  font-weight: 500;
  color: #444746;
}

.header-right {
  display: flex;
}

.delete-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: #e53935;
  cursor: pointer;
  padding: 6px 12px;
  border-radius: 16px;
  transition: background-color 0.2s;
}

.delete-btn:hover {
  background-color: #fde8e8;
}

.delete-btn.disabled {
  color: #9aa0a6;
  pointer-events: none;
}

.delete-btn.loading {
  opacity: 0.7;
  pointer-events: none;
}

.list-container {
  display: flex;
  flex-direction: column;
}

.list-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 12px;
  border-radius: 8px;
  transition: background-color 0.2s;
}

.list-item:hover {
  background-color: #f0f4f9;
}

.item-left {
  display: flex;
  align-items: center;
  gap: 16px;
  flex: 1;
  min-width: 0;
}

.item-title {
  font-size: 14px;
  color: #1f1f1f;
  cursor: pointer;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.item-title:hover {
  text-decoration: underline;
}

.item-right {
  font-size: 13px;
  color: #444746;
  white-space: nowrap;
  margin-left: 24px;
}

.empty-state {
  margin-top: 40px;
  font-size: 14px;
  color: #5f6368;
}
</style>
