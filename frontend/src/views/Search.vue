<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useDialog, useMessage, NAvatar, NCheckbox, NDropdown, NIcon } from 'naive-ui'
import { CreateOutline, MenuOutline, SearchOutline, SettingsOutline, TrashOutline } from '@vicons/ionicons5'
import { deleteConversation, getConversations } from '@/api/conversation'
import { useUserStore } from '@/stores/user'

const router = useRouter()
const message = useMessage()
const dialog = useDialog()
const userStore = useUserStore()

const isSidebarOpen = ref(true)
const conversations = ref<any[]>([])
const searchQuery = ref('')
const selectedIds = ref<string[]>([])
const isDeleting = ref(false)

const userName = computed(() => userStore.user?.name || '用户')

const settingsOptions = [{ label: '退出登录', key: 'logout' }]

const handleSettingsSelect = (key: string) => {
  if (key !== 'logout') return
  userStore.logout()
  router.push('/login')
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
    conversations.value = Array.isArray(res) ? res : res.data || []
  } catch (error) {
    console.error('获取历史会话失败', error)
  }
}

const filteredConversations = computed(() => {
  if (!searchQuery.value) return conversations.value
  const q = searchQuery.value.toLowerCase()
  return conversations.value.filter((c) => (c.title || '').toLowerCase().includes(q))
})

const formatDate = (dateString?: string) => {
  if (!dateString) return ''
  const date = new Date(dateString)
  return date.toLocaleDateString('zh-CN', {
    month: 'short',
    day: 'numeric',
    year: date.getFullYear() !== new Date().getFullYear() ? 'numeric' : undefined,
  })
}

const toggleSelectAll = (checked: boolean) => {
  selectedIds.value = checked ? filteredConversations.value.map((c) => c.id) : []
}

const toggleSelection = (id: string, checked: boolean) => {
  if (checked) {
    if (!selectedIds.value.includes(id)) selectedIds.value.push(id)
    return
  }
  selectedIds.value = selectedIds.value.filter((value) => value !== id)
}

const isAllSelected = computed(
  () => filteredConversations.value.length > 0 && selectedIds.value.length === filteredConversations.value.length,
)

const isIndeterminate = computed(
  () =>
    selectedIds.value.length > 0 &&
    selectedIds.value.length < filteredConversations.value.length,
)

const handleBatchDelete = () => {
  if (selectedIds.value.length === 0) return
  dialog.warning({
    title: '批量删除会话',
    content: `确定删除已选中的 ${selectedIds.value.length} 条会话吗？此操作不可恢复。`,
    positiveText: '确认删除',
    negativeText: '取消',
    async onPositiveClick() {
      isDeleting.value = true
      try {
        for (const id of selectedIds.value) {
          await deleteConversation(id)
        }
        message.success('批量删除成功')
        selectedIds.value = []
        await fetchConversationList()
      } catch (err) {
        console.error(err)
        message.error('删除过程中发生错误，请稍后重试')
      } finally {
        isDeleting.value = false
      }
    },
  })
}

onMounted(() => {
  fetchConversationList()
})
</script>

<template>
  <div class="app-layout ds-page-shell">
    <div class="sidebar-wrapper" :class="{ 'is-collapsed': !isSidebarOpen }">
      <div class="sidebar-header">
        <div class="menu-btn ds-icon-btn" @click="toggleSidebar">
          <n-icon :size="20"><MenuOutline /></n-icon>
        </div>
        <div class="menu-btn ds-icon-btn">
          <n-icon :size="18"><SearchOutline /></n-icon>
        </div>
      </div>

      <div class="sidebar-content ds-scrollbar" v-show="isSidebarOpen">
        <div class="new-chat-btn new-chat-btn-shift" @click="handleNewChat">
          <n-icon :size="18"><CreateOutline /></n-icon>
          <span>新建会话</span>
        </div>

        <div class="sidebar-menu-header">
          <span>最近会话</span>
        </div>
        <div class="chat-history-list">
          <div
            v-for="convo in conversations.slice(0, 15)"
            :key="convo.id"
            class="history-item"
            @click="handleSelectChat(convo.id)"
          >
            <span class="history-title">{{ convo.title || '新会话' }}</span>
          </div>
        </div>

        <div class="sidebar-bottom">
          <div class="sidebar-menu-item sidebar-profile-item">
            <n-avatar round :size="24" class="user-avatar-pill">{{ userName.slice(0, 1) }}</n-avatar>
            <span class="sidebar-user-name">{{ userName }}</span>
          </div>

          <n-dropdown :options="settingsOptions" placement="top-start" @select="handleSettingsSelect">
            <div class="sidebar-menu-item">
              <n-icon :size="18"><SettingsOutline /></n-icon>
              <span>设置与帮助</span>
            </div>
          </n-dropdown>
        </div>
      </div>
    </div>

    <div class="search-container ds-card">
      <div class="top-nav">
        <div class="nav-left">
          <div class="menu-btn ds-icon-btn" @click="toggleSidebar" v-if="!isSidebarOpen">
            <n-icon :size="20"><MenuOutline /></n-icon>
          </div>
          <span class="page-title">会话检索中心</span>
        </div>
      </div>

      <div class="search-content ds-scrollbar">
        <h1 class="search-title">搜索会话</h1>

        <div class="search-input-wrapper ds-card ds-card-elevated">
          <n-icon :size="20" class="search-icon"><SearchOutline /></n-icon>
          <input
            v-model="searchQuery"
            type="text"
            class="search-input"
            placeholder="输入关键词搜索会话标题"
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
              <span>最近会话</span>
            </div>
            <button
              type="button"
              class="delete-btn"
              :class="{ disabled: selectedIds.length === 0 || isDeleting }"
              @click="handleBatchDelete"
            >
              <n-icon :size="16"><TrashOutline /></n-icon>
              <span>{{ isDeleting ? '删除中...' : '批量删除' }}</span>
            </button>
          </div>

          <div class="list-container">
            <div v-for="convo in filteredConversations" :key="convo.id" class="list-item">
              <div class="item-left">
                <n-checkbox
                  :checked="selectedIds.includes(convo.id)"
                  @update:checked="(checked) => toggleSelection(convo.id, checked)"
                />
                <span class="item-title" @click="handleSelectChat(convo.id)">
                  {{ convo.title || '新会话' }}
                </span>
              </div>
              <div class="item-right">
                <span class="item-date">{{ formatDate(convo.updated_at || convo.created_at) }}</span>
              </div>
            </div>
          </div>
        </div>

        <div v-else class="empty-state">
          没有找到匹配的会话，请尝试更换关键词。
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.app-layout {
  display: flex;
  height: 100vh;
  width: 100vw;
  overflow: hidden;
  background: var(--ds-bg-page);
}

.sidebar-wrapper {
  width: 280px;
  background: transparent;
  display: flex;
  flex-direction: column;
  transition: width 0.28s ease;
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
  gap: 6px;
}

.sidebar-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  padding: 0 16px 16px;
  overflow-y: auto;
}

.new-chat-btn {
  background: linear-gradient(135deg, var(--ds-brand-soft), #edf2ff);
  border-radius: 16px;
  display: inline-flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  margin-bottom: 24px;
  width: max-content;
  color: var(--ds-text-primary);
  font-weight: 600;
  font-size: 14px;
  cursor: pointer;
}

.new-chat-btn-shift {
  margin-left: -4px;
}

.sidebar-menu-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 12px;
  border-radius: 12px;
  color: var(--ds-text-secondary);
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  margin-bottom: 8px;
}

.sidebar-menu-item:hover {
  background: var(--ds-bg-elevated);
}

.sidebar-menu-header {
  padding: 12px;
  color: var(--ds-text-secondary);
  font-size: 13px;
  font-weight: 700;
}

.chat-history-list {
  display: flex;
  flex-direction: column;
}

.history-item {
  padding: 10px 12px;
  border-radius: 12px;
  color: var(--ds-text-secondary);
  font-size: 14px;
  cursor: pointer;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  margin-bottom: 2px;
}

.history-item:hover {
  background: var(--ds-bg-elevated);
}

.sidebar-bottom {
  margin-top: auto;
  padding-top: 16px;
}

.sidebar-profile-item {
  padding-left: 8px;
}

.sidebar-user-name {
  font-weight: 500;
  color: var(--ds-text-primary);
}

.user-avatar-pill {
  background: linear-gradient(135deg, #4e75ff, #7b4fff);
  color: #fff;
}

.search-container {
  flex: 1;
  margin: 10px 10px 10px 0;
  border-radius: 20px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.top-nav {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 24px;
}

.nav-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.page-title {
  font-size: 18px;
  font-weight: 600;
  color: var(--ds-text-secondary);
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
  font-size: 30px;
  font-weight: 700;
  color: var(--ds-text-primary);
  margin-bottom: 20px;
}

.search-input-wrapper {
  width: 90%;
  max-width: 780px;
  display: flex;
  align-items: center;
  border-radius: 24px;
  padding: 12px 20px;
  margin-bottom: 32px;
}

.search-input-wrapper:focus-within {
  box-shadow: var(--ds-shadow-md);
  border-color: #bfd0f4;
}

.search-icon {
  color: var(--ds-text-tertiary);
  margin-right: 12px;
}

.search-input {
  flex: 1;
  border: none;
  outline: none;
  font-size: 15px;
  color: var(--ds-text-primary);
  background: transparent;
}

.search-input::placeholder {
  color: var(--ds-text-tertiary);
}

.recent-section {
  width: 90%;
  max-width: 780px;
  display: flex;
  flex-direction: column;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
  padding: 0 8px;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 14px;
  font-weight: 600;
  color: var(--ds-text-secondary);
}

.delete-btn {
  border: none;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: var(--ds-error);
  background: rgba(229, 57, 53, 0.08);
  cursor: pointer;
  padding: 8px 12px;
  border-radius: 999px;
}

.delete-btn:hover {
  background: rgba(229, 57, 53, 0.16);
}

.delete-btn.disabled {
  opacity: 0.55;
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
  padding: 14px 12px;
  border-radius: 10px;
}

.list-item:hover {
  background: var(--ds-bg-elevated);
}

.item-left {
  display: flex;
  align-items: center;
  gap: 14px;
  flex: 1;
  min-width: 0;
}

.item-title {
  font-size: 14px;
  color: var(--ds-text-primary);
  cursor: pointer;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.item-title:hover {
  color: var(--ds-brand);
}

.item-right {
  font-size: 13px;
  color: var(--ds-text-tertiary);
  white-space: nowrap;
  margin-left: 20px;
}

.empty-state {
  margin-top: 44px;
  font-size: 14px;
  color: var(--ds-text-tertiary);
}
</style>
