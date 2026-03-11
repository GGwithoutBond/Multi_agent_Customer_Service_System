<script setup lang="ts">
import { ref, onMounted, onUnmounted, nextTick, watch, computed, h } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useMessage, NIcon, NAvatar, NInput, NTag, NDropdown, NDrawer, NDrawerContent, NModal } from 'naive-ui'
import {
  SendOutline,
  ImageOutline,
  MicOutline,
  AddOutline,
  DocumentTextOutline,
  CartOutline,
  ListOutline,
  CloseOutline,
  DownloadOutline,
  SearchOutline,
  SettingsOutline,
  TimeOutline,
  PersonOutline,
  AppsOutline,
  LinkOutline,
  SunnyOutline,
  CardOutline,
  BookOutline,
  ChatboxEllipsesOutline,
  HelpCircleOutline,
  LocationOutline,
  LogOutOutline,
  ShareOutline,
  PinOutline,
  PencilOutline,
  TrashOutline,
  CopyOutline,
  RefreshOutline,
  ArrowDownOutline
} from '@vicons/ionicons5'
import hljs from 'highlight.js'
import 'highlight.js/styles/github-dark.css'
import MarkdownIt from 'markdown-it'
import { getMessages, uploadFile } from '@/api/chat'
import { createConversation, updateConversation, getConversations, deleteConversation } from '@/api/conversation'
import { useUserStore } from '@/stores/user'

const emit = defineEmits<{
  refresh: []
}>()

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()
const message = useMessage()

function renderIcon(icon: any) {
  return () => h(NIcon, null, { default: () => h(icon) })
}

// Markdown 渲染
const md = new MarkdownIt({
  html: false,
  breaks: true,
  linkify: true,
  highlight: function (str: string, lang: string) {
    const langstr = lang ? `<span class="code-lang">${lang}</span>` : '';
    let codeStr = '';
    if (lang && hljs.getLanguage(lang)) {
      try {
        codeStr = hljs.highlight(str, { language: lang, ignoreIllegals: true }).value;
      } catch (__) {
        codeStr = md.utils.escapeHtml(str);
      }
    } else {
      codeStr = md.utils.escapeHtml(str);
    }
    
    const encodedStr = encodeURIComponent(str);
    
    return `<div class="code-block-wrapper">
      <div class="code-block-header">
        ${langstr}
        <button class="copy-code-btn" onclick="navigator.clipboard.writeText(decodeURIComponent('${encodedStr}')); this.innerText='Copied!'; setTimeout(() => this.innerText='Copy', 2000)">Copy</button>
      </div>
      <pre class="hljs"><code>${codeStr}</code></pre>
    </div>`;
  }
})

const renderMarkdown = (content: string) => {
  return md.render(content || '')
}

const conversationId = ref<string>('')
const messages = ref<any[]>([])
const inputValue = ref('')
const isLoading = ref(false)
const scrollContainerRef = ref<HTMLElement>()
const innerRef = ref()
const sending = ref(false)
const webSearchEnabled = ref(false)
const showScrollToBottom = ref(false)
const isDraggingFile = ref(false)

const isSidebarOpen = ref(window.innerWidth > 768)
const conversations = ref<any[]>([])

const fetchConversationList = async () => {
  try {
    const res: any = await getConversations()
    conversations.value = Array.isArray(res) ? res : (res.data || [])
  } catch (error) {
    console.error('获取历史会话失败', error)
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

// ===== 历史会话操作 (More Options) =====
const showRenameModal = ref(false)
const renameId = ref('')
const renameTitle = ref('')

const chatOptions = [
  { label: 'Share conversation', key: 'share', icon: renderIcon(ShareOutline) },
  { label: 'Pin', key: 'pin', icon: renderIcon(PinOutline) },
  { label: 'Rename', key: 'rename', icon: renderIcon(PencilOutline) },
  { label: 'Delete', key: 'delete', icon: renderIcon(TrashOutline) }
]

const handleChatOption = async (key: string, id: string) => {
  if (key === 'share' || key === 'pin') {
    // No-op for now
    message.info(`功能开发中: ${key}`)
  } else if (key === 'rename') {
    const chat = conversations.value.find(c => c.id === id)
    if (chat) {
      renameId.value = id
      renameTitle.value = chat.title || ''
      showRenameModal.value = true
    }
  } else if (key === 'delete') {
    if (confirm('确定要删除此段对话吗？此操作不可恢复。')) {
      try {
        await deleteConversation(id)
        if (conversationId.value === id) {
          router.push('/')
        } else {
          fetchConversationList()
        }
        message.success('已删除对话')
      } catch (err) {
        message.error('删除失败')
      }
    }
  }
}

const submitRename = async () => {
  if (!renameTitle.value.trim() || !renameId.value) return
  try {
    await updateConversation(renameId.value, { title: renameTitle.value.trim() })
    showRenameModal.value = false
    message.success('重命名成功')
    fetchConversationList()
  } catch (err) {
    message.error('重命名失败')
  }
}

// 客服风格设置
const personaOptions = [
  { label: '专业型 (Professional)', key: 'professional' },
  { label: '亲切型 (Friendly)', key: 'friendly' },
  { label: '技术型 (Technical)', key: 'technical' }
]
const selectedPersona = ref('friendly')

// ===== 附件相关状态 =====
interface AttachmentItem {
  type: 'image' | 'file' | 'order' | 'product'
  url?: string
  name?: string
  size?: number
  order_id?: string
  status?: string
  product_id?: string
  price?: number
  image?: string
}

const pendingAttachments = ref<AttachmentItem[]>([])
const imageInputRef = ref<HTMLInputElement>()
const fileInputRef = ref<HTMLInputElement>()
const uploading = ref(false)
const showOrderDrawer = ref(false)
const showProductDrawer = ref(false)

// 模拟订单数据
const mockOrders = ref([
  { order_id: 'ORD-2024001', name: 'iPhone 16 Pro', status: '已发货', price: 8999, date: '2024-12-01' },
  { order_id: 'ORD-2024002', name: 'AirPods Pro 2', status: '已签收', price: 1899, date: '2024-11-28' },
  { order_id: 'ORD-2024003', name: 'MacBook Air M3', status: '处理中', price: 9499, date: '2024-12-05' },
  { order_id: 'ORD-2024004', name: 'iPad Pro 13"', status: '待付款', price: 10999, date: '2024-12-08' },
])

// 模拟商品数据
const mockProducts = ref([
  { product_id: 'P001', name: 'MacBook Pro 14"', price: 12999, image: '', category: '电脑' },
  { product_id: 'P002', name: 'iPhone 16 Pro Max', price: 9999, image: '', category: '手机' },
  { product_id: 'P003', name: 'Apple Watch Ultra 2', price: 5999, image: '', category: '手表' },
  { product_id: 'P004', name: 'Vision Pro', price: 29999, image: '', category: 'AR设备' },
  { product_id: 'P005', name: 'AirPods Max', price: 4399, image: '', category: '耳机' },
])

// Plus 按钮下拉菜单选项
const plusOptions = [
  {
    label: '上传文件',
    key: 'file',
    icon: () => h(NIcon, null, { default: () => h(DocumentTextOutline) })
  },
  {
    label: '选择订单',
    key: 'order',
    icon: () => h(NIcon, null, { default: () => h(ListOutline) })
  },
  {
    label: '选择商品',
    key: 'product',
    icon: () => h(NIcon, null, { default: () => h(CartOutline) })
  }
]

// ===== 侧边栏底部设置 =====
const settingsOptions = [
  { label: 'Activity', key: 'activity', icon: renderIcon(TimeOutline) },
  { label: 'Instructions for Gemini', key: 'instructions', icon: renderIcon(PersonOutline) },
  { label: 'Connected Apps', key: 'apps', icon: renderIcon(AppsOutline) },
  { type: 'divider', key: 'd1' },
  { label: 'Your public links', key: 'links', icon: renderIcon(LinkOutline) },
  { type: 'divider', key: 'd2' },
  { label: 'Theme', key: 'theme', icon: renderIcon(SunnyOutline) },
  { type: 'divider', key: 'd3' },
  { label: 'View subscriptions', key: 'subscriptions', icon: renderIcon(CardOutline) },
  { type: 'divider', key: 'd4' },
  { label: 'NotebookLM', key: 'notebook', icon: renderIcon(BookOutline) },
  { type: 'divider', key: 'd5' },
  { label: 'Send feedback', key: 'feedback', icon: renderIcon(ChatboxEllipsesOutline) },
  { type: 'divider', key: 'd6' },
  { label: 'Help', key: 'help', icon: renderIcon(HelpCircleOutline) },
  { type: 'divider', key: 'd7' },
  { label: 'Tokyo, Japan', key: 'location', icon: renderIcon(LocationOutline) },
  { type: 'divider', key: 'd8' },
  { label: '退出登录 (Logout)', key: 'logout', icon: renderIcon(LogOutOutline) }
]

const handleSettingsSelect = (key: string) => {
  if (key === 'logout') {
    userStore.logout()
    router.push('/login')
  }
}

// ===== 文件上传处理 =====
const handleImageSelect = () => {
  imageInputRef.value?.click()
}

const handleFileSelect = () => {
  fileInputRef.value?.click()
}

const onImageChange = async (e: Event) => {
  const target = e.target as HTMLInputElement
  const files = target.files
  if (!files?.length) return

  for (const file of Array.from(files)) {
    if (!file.type.startsWith('image/')) {
      message.warning(`${file.name} 不是图片文件`)
      continue
    }
    await doUpload(file)
  }
  target.value = ''
}

const onFileChange = async (e: Event) => {
  const target = e.target as HTMLInputElement
  const files = target.files
  if (!files?.length) return

  for (const file of Array.from(files)) {
    await doUpload(file)
  }
  target.value = ''
}

const doUpload = async (file: File) => {
  uploading.value = true
  try {
    const res: any = await uploadFile(file)
    const data = res.data || res
    pendingAttachments.value.push({
      type: data.type === 'image' ? 'image' : 'file',
      url: data.url,
      name: data.name || file.name,
      size: data.size || file.size,
    })
    message.success(`${file.name} 上传成功`)
  } catch (err) {
    console.error(err)
    message.error(`${file.name} 上传失败`)
  } finally {
    uploading.value = false
  }
}

// 移除待发送附件
const removeAttachment = (index: number) => {
  pendingAttachments.value.splice(index, 1)
}

// ===== 订单选择 =====
const selectOrder = (order: any) => {
  if (pendingAttachments.value.some(a => a.type === 'order' && a.order_id === order.order_id)) {
    message.info('该订单已添加')
    return
  }
  pendingAttachments.value.push({
    type: 'order',
    order_id: order.order_id,
    name: order.name,
    status: order.status,
    price: order.price,
  })
  showOrderDrawer.value = false
  message.success('已选择订单')
}

// ===== 消息快捷操作 =====
const copyMessage = (content: string) => {
  navigator.clipboard.writeText(content)
  message.success('内容已复制')
}

const regenerateMessage = (index: number) => {
  if (sending.value || index <= 0) return
  let userMsgIndex = index - 1
  while (userMsgIndex >= 0 && messages.value[userMsgIndex].role !== 'user') {
    userMsgIndex--
  }
  if (userMsgIndex < 0) return
  
  const userMsg = messages.value[userMsgIndex]
  inputValue.value = userMsg.content === '[附件]' ? '' : userMsg.content
  if (userMsg.attachments && userMsg.attachments.length > 0) {
    pendingAttachments.value = [...userMsg.attachments]
  }
  messages.value.splice(userMsgIndex)
  handleSend()
}

const editMessage = (index: number) => {
  if (sending.value) return
  const msg = messages.value[index]
  inputValue.value = msg.content === '[附件]' ? '' : msg.content
  if (msg.attachments && msg.attachments.length > 0) {
    pendingAttachments.value = [...msg.attachments]
  }
  messages.value.splice(index)
}

const deleteMessage = (index: number) => {
  if (confirm('确认删除这条消息吗？')) {
    messages.value.splice(index, 1)
  }
}

// ===== 拖拽上传 =====
let dragCounter = 0
const onDragOver = (e: DragEvent) => {
  e.preventDefault()
}
const onDragEnter = (e: DragEvent) => {
  e.preventDefault()
  dragCounter++
  isDraggingFile.value = true
}
const onDragLeave = (e: DragEvent) => {
  e.preventDefault()
  dragCounter--
  if (dragCounter === 0) {
    isDraggingFile.value = false
  }
}
const onDrop = async (e: DragEvent) => {
  e.preventDefault()
  dragCounter = 0
  isDraggingFile.value = false
  const files = e.dataTransfer?.files
  if (!files || files.length === 0) return

  for (const file of Array.from(files)) {
    await doUpload(file)
  }
}

// ===== 商品选择 =====
const selectProduct = (product: any) => {
  if (pendingAttachments.value.some(a => a.type === 'product' && a.product_id === product.product_id)) {
    message.info('该商品已添加')
    return
  }
  pendingAttachments.value.push({
    type: 'product',
    product_id: product.product_id,
    name: product.name,
    price: product.price,
    image: product.image,
  })
  showProductDrawer.value = false
  message.success('已选择商品')
}

// 格式化文件大小
const formatSize = (bytes?: number) => {
  if (!bytes) return ''
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1048576) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / 1048576).toFixed(1) + ' MB'
}

// 获取订单状态类型
const getStatusType = (status: string): "default" | "success" | "warning" | "error" | "info" => {
  const map: Record<string, "default" | "success" | "warning" | "error" | "info"> = {
    '已签收': 'success',
    '已发货': 'info',
    '处理中': 'warning',
    '待付款': 'error',
  }
  return map[status] || 'default'
}

// 滚动到底部
const scrollToBottom = () => {
  nextTick(() => {
    if (scrollContainerRef.value) {
      scrollContainerRef.value.scrollTop = scrollContainerRef.value.scrollHeight
    }
  })
}

const handleScroll = (e: Event) => {
  const target = e.target as HTMLElement
  const isNearBottom = target.scrollHeight - target.scrollTop - target.clientHeight < 100
  showScrollToBottom.value = !isNearBottom
}

// 获取消息列表
const fetchMessages = async () => {
  if (!conversationId.value) return
  isLoading.value = true
  try {
    const res: any = await getMessages(conversationId.value)
    messages.value = Array.isArray(res) ? res : (res.data || [])
    // 解析 attachments
    messages.value.forEach((msg: any) => {
      if (msg.metadata_ && msg.metadata_.attachments) {
        msg.attachments = msg.metadata_.attachments
      }
    })
    scrollToBottom()
  } catch (error) {
    console.error(error)
  } finally {
    isLoading.value = false
  }
}

// 监听路由变化
watch(() => route.params.id, async (newId) => {
  if (newId && typeof newId === 'string') {
    if (newId === conversationId.value && messages.value.length > 0) return
    conversationId.value = newId
    await fetchMessages()
  } else {
    // 仅在非发送状态时才清空（避免新对话发送中被清空）
    if (!sending.value) {
      messages.value = []
      conversationId.value = ''
    }
  }
  // 任何路由改变都刷新一下列表
  fetchConversationList()
})

// 发送消息
const handleSend = async () => {
  const content = inputValue.value.trim()
  if (!content && pendingAttachments.value.length === 0) return

  // 检查登录状态
  if (!userStore.token) {
    message.warning('请先登录后再发送消息')
    router.push('/login')
    return
  }

  // 标记是否是新创建的会话（需要在流式结束后导航）
  let isNewConversation = false

  // 如果没有 conversationId，先创建会话
  if (!conversationId.value) {
    try {
      isLoading.value = true
      const titleText = content || pendingAttachments.value[0]?.name || '新对话'
      const res: any = await createConversation({ title: titleText.slice(0, 30) })
      conversationId.value = res.id || res.data?.id
      if (!conversationId.value) {
        throw new Error('创建会话失败')
      }
      isNewConversation = true
      emit('refresh')
    } catch (error) {
      console.error(error)
      message.error('创建会话失败，请刷新页面重试')
      isLoading.value = false
      return
    }
  }

  if (sending.value) return

  // 收集附件
  const attachments = pendingAttachments.value.length > 0
    ? [...pendingAttachments.value]
    : undefined

  // 添加用户消息（包含附件）
  messages.value.push({
    role: 'user',
    content: content || (attachments ? '[附件]' : ''),
    attachments: attachments,
    created_at: new Date().toISOString()
  })

  inputValue.value = ''
  pendingAttachments.value = []
  scrollToBottom()
  sending.value = true

  // 创建 AI 回复占位（包含打字动画 + 思考过程状态）
  const aiMessage = {
    role: 'assistant',
    content: '',
    loading: true,
    thinkingSteps: [] as { step: string; content?: string }[],
    thinkingDone: false,
    actionButtons: [] as { type: string; label: string; action: string; style?: string; order_id?: string; product?: string; status?: string; amount?: string; disabled?: boolean }[],
    created_at: new Date().toISOString()
  }
  messages.value.push(aiMessage)
  const aiMessageIndex = messages.value.length - 1

  try {
    const body: any = {
      message: content || '[用户发送了附件]',
      conversation_id: conversationId.value,
      web_search: webSearchEnabled.value,
      persona_style: selectedPersona.value,
    }
    if (attachments) {
      body.attachments = attachments
    }

    const response = await fetch(`/api/v1/chat/stream`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${userStore.token}`
      },
      body: JSON.stringify(body)
    })

    if (!response.ok) {
      throw new Error(`请求失败: ${response.status}`)
    }

    if (!response.body) throw new Error('响应体为空')

    const reader = response.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      buffer = lines.pop() || ''

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const dataStr = line.slice(6).trim()
          if (dataStr === '[DONE]') continue

          try {
            const data = JSON.parse(dataStr)
            if (data.type === 'thinking' || data.type === 'tool_call') {
              messages.value[aiMessageIndex].thinkingSteps.push({
                step: data.step || (data.type === 'thinking' ? '思考中...' : '调用工具...'),
                content: data.content || '',
              })
              scrollToBottom()
            } else if (data.type === 'chunk' && data.content) {
              if (!messages.value[aiMessageIndex].thinkingDone) {
                messages.value[aiMessageIndex].thinkingDone = true
              }
              messages.value[aiMessageIndex].content += data.content
              scrollToBottom()
            } else if (data.type === 'action_buttons' && data.actions) {
              // 交互式按钮（退货订单选择、确认/取消等）
              const actions = data.actions.map((a: any) => ({ ...a, disabled: false }))
              messages.value[aiMessageIndex].actionButtons.push(...actions)
              scrollToBottom()
            } else if (data.type === 'error') {
              messages.value[aiMessageIndex].content = `错误: ${data.error || '未知错误'}`
            }
          } catch {
            // Ignore unparseable SSE data
          }
        }
      }
    }

  } catch (error: any) {
    console.error(error)
    message.error(error.message || '发送消息失败')
    messages.value[aiMessageIndex].content = '抱歉，消息发送失败，请稍后重试。'
  } finally {
    messages.value[aiMessageIndex].loading = false
    sending.value = false
    scrollToBottom()

    // 流式结束后，如果是新会话，更新 URL
    if (isNewConversation && conversationId.value) {
      router.replace(`/chat/${conversationId.value}`)
    }

    // 发送成功后更新对话标题（第一条消息）
    if (messages.value.length === 2 && conversationId.value) {
      const firstMessage = messages.value[0].content
      const title = firstMessage.slice(0, 30) + (firstMessage.length > 30 ? '...' : '')
      try {
        await updateConversation(conversationId.value, { title })
        emit('refresh')
      } catch (e) {
        console.error('更新标题失败', e)
      }
    }
  }
}

const userName = computed(() => userStore.user?.name || 'User')

// 处理交互按钮点击（退货订单选择、确认/取消）
const handleActionClick = (action: any, msgIndex: number) => {
  if (action.disabled || sending.value) return
  // 禁用同组所有按钮
  const msg = messages.value[msgIndex]
  if (msg?.actionButtons) {
    msg.actionButtons.forEach((a: any) => a.disabled = true)
  }
  // 自动发送对应的文本消息
  inputValue.value = action.action
  nextTick(() => handleSend())
}

// Plus 按钮的弹出菜单
const handlePlusCommand = (key: string) => {
  if (key === 'file') handleFileSelect()
  else if (key === 'order') showOrderDrawer.value = true
  else if (key === 'product') showProductDrawer.value = true
}

const openImagePreview = (url: string) => {
  window.open(url, '_blank')
}

let resizeObserver: ResizeObserver | null = null

onMounted(() => {
  fetchConversationList()
  if (route.params.id && typeof route.params.id === 'string') {
    conversationId.value = route.params.id
    fetchMessages()
  }

  if (innerRef.value && scrollContainerRef.value) {
    resizeObserver = new ResizeObserver(() => {
      if (sending.value && scrollContainerRef.value) {
        scrollContainerRef.value.scrollTop = scrollContainerRef.value.scrollHeight
      }
    })
    resizeObserver.observe(innerRef.value)
  }
})

onUnmounted(() => {
  if (resizeObserver) resizeObserver.disconnect()
})
</script>

<template>
  <div class="app-layout" @dragover="onDragOver" @dragenter="onDragEnter" @dragleave="onDragLeave" @drop="onDrop">
    <!-- Mobile Sidebar Overlay -->
    <div class="mobile-sidebar-overlay" :class="{ 'is-open': isSidebarOpen }" @click="isSidebarOpen = false"></div>
    <!-- Drag Overlay -->
    <div v-if="isDraggingFile" class="drag-overlay">
      <div class="drag-overlay-content">
        <n-icon :size="48"><DocumentTextOutline /></n-icon>
        <span>释放文件以上传</span>
      </div>
    </div>
    <!-- 侧边栏 (Gemini Layout) -->
    <div class="sidebar-wrapper" :class="{ 'is-collapsed': !isSidebarOpen }">
      <div class="sidebar-header" :style="isSidebarOpen ? '' : 'flex-direction: column; gap: 12px; align-items: center; padding: 16px 0;'">
        <div class="menu-btn" @click="toggleSidebar" :style="isSidebarOpen ? '' : 'margin: 0;'">
          <n-icon :size="20"><MenuOutline /></n-icon>
        </div>
        <div class="menu-btn" title="搜索" @click="router.push('/search')" :style="isSidebarOpen ? 'margin-left:4px;' : 'margin: 0;'">
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
            v-for="convo in conversations"
            :key="convo.id"
            class="history-item"
            :class="{ active: convo.id === conversationId }"
            @click="handleSelectChat(convo.id)"
          >
            <span class="history-title">{{ convo.title || '新对话' }}</span>
            <n-dropdown 
              :options="chatOptions" 
              placement="bottom-end"
              trigger="click"
              @select="(key: string) => handleChatOption(key, convo.id)"
            >
              <div class="history-more-btn" @click.stop>
                <n-icon :size="16"><EllipsisVertical /></n-icon>
              </div>
            </n-dropdown>
          </div>
        </div>
        
        <!-- Bottom Settings & Avatar -->
        <div class="sidebar-bottom">
          <div class="sidebar-menu-item" style="padding-left: 8px;">
            <n-avatar round :size="24" class="user-avatar" style="background-color: #9b72cb;">{{ userName.slice(0, 1) }}</n-avatar>
            <span style="font-weight: 500; color: var(--text-primary);">{{ userName }}</span>
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

    <!-- 主聊天区 -->
    <div class="chat-container">
      <!-- 顶部 Header: Hamburger toggle when sidebar is closed, Gemini logo -->
      <div class="top-nav">
        <div class="nav-left">
          <div class="menu-btn" @click="toggleSidebar" v-if="!isSidebarOpen">
            <n-icon :size="20"><MenuOutline /></n-icon>
          </div>
          <span class="gemini-logo">AI 客服助手</span>
        </div>
      </div>

      <!-- Hidden file inputs -->
      <input ref="imageInputRef" type="file" accept="image/*" multiple style="display:none" @change="onImageChange" />
      <input ref="fileInputRef" type="file" accept=".pdf,.doc,.docx,.xls,.xlsx,.txt,.csv" multiple style="display:none" @change="onFileChange" />

    <!-- 消息列表区域 -->
    <div ref="scrollContainerRef" class="chat-area" @scroll="handleScroll">
      <div ref="innerRef" class="messages-wrapper">
        <!-- 消息列表 -->
        <template v-if="messages.length > 0">
          <div v-for="(msg, index) in messages" :key="index" class="message-row" :class="msg.role">
            <!-- Avatar for AI -->
            <div class="message-avatar" v-if="msg.role === 'assistant'">
              <n-avatar :size="30" round class="ai-avatar">
                <n-icon><SendOutline /></n-icon>
              </n-avatar>
            </div>

            <div class="message-content-wrapper" :style="msg.role === 'user' ? 'display: flex; flex-direction: column; align-items: flex-end;' : ''">
              <div class="message-heading" v-if="msg.role === 'assistant'">
                <span class="sender-name">客服小鹏</span>
              </div>
              <div class="message-bubble">
                <!-- 附件渲染 -->
                <div v-if="msg.attachments && msg.attachments.length > 0" class="msg-attachments">
                  <template v-for="(att, ai) in msg.attachments" :key="ai">
                    <!-- 图片附件 -->
                    <div v-if="att.type === 'image'" class="att-image">
                      <img :src="att.url" :alt="att.name" @click="openImagePreview(att.url)" />
                    </div>
                    <!-- 文件附件 -->
                    <div v-else-if="att.type === 'file'" class="att-file">
                      <n-icon class="att-file-icon" :size="28"><DocumentTextOutline /></n-icon>
                      <div class="att-file-info">
                        <span class="att-file-name">{{ att.name }}</span>
                        <span class="att-file-size">{{ formatSize(att.size) }}</span>
                      </div>
                      <a :href="att.url" target="_blank" class="att-download">
                        <n-icon :size="20"><DownloadOutline /></n-icon>
                      </a>
                    </div>
                    <!-- 订单卡片 -->
                    <div v-else-if="att.type === 'order'" class="att-order">
                      <div class="att-card-header">
                        <n-icon><ListOutline /></n-icon>
                        <span>订单</span>
                        <n-tag :type="getStatusType(att.status)" size="small" round>{{ att.status }}</n-tag>
                      </div>
                      <div class="att-card-body">
                        <span class="att-card-title">{{ att.name }}</span>
                        <span class="att-card-id">{{ att.order_id }}</span>
                      </div>
                      <div class="att-card-price" v-if="att.price">¥{{ att.price }}</div>
                    </div>
                    <!-- 商品卡片 -->
                    <div v-else-if="att.type === 'product'" class="att-product">
                      <div class="att-card-header">
                        <n-icon><CartOutline /></n-icon>
                        <span>商品</span>
                      </div>
                      <div class="att-card-body">
                        <span class="att-card-title">{{ att.name }}</span>
                        <span class="att-card-id">{{ att.product_id }}</span>
                      </div>
                      <div class="att-card-price" v-if="att.price">¥{{ att.price }}</div>
                    </div>
                  </template>
                </div>
                <!-- 思考过程（可折叠） -->
                <div v-if="msg.thinkingSteps && msg.thinkingSteps.length > 0" class="thinking-section" :class="{ collapsed: msg.thinkingDone }">
                  <details :open="!msg.thinkingDone">
                    <summary class="thinking-summary">
                      <span class="thinking-label">{{ msg.thinkingDone ? '✅ 已完成分析' : '⏳ 正在分析...' }}</span>
                    </summary>
                    <div class="thinking-steps">
                      <div v-for="(ts, si) in msg.thinkingSteps" :key="si" class="thinking-step">
                        <span class="step-icon">{{ [...ts.step][0] }}</span>
                        <div class="step-info">
                          <span class="step-label">{{ [...ts.step].slice(1).join('').trim() }}</span>
                          <span v-if="ts.content" class="step-content">{{ ts.content.slice(0, 100) }}{{ ts.content.length > 100 ? '...' : '' }}</span>
                        </div>
                      </div>
                    </div>
                  </details>
                </div>
                <!-- 打字动画 -->
                <div v-if="msg.role === 'assistant' && msg.loading && !msg.content && (!msg.thinkingSteps || msg.thinkingSteps.length === 0)" class="typing-indicator">
                  <span></span><span></span><span></span>
                </div>
                <!-- 消息内容 -->
                <div v-if="msg.content" class="message-content" v-html="renderMarkdown(msg.content)"></div>
                <!-- 交互按钮区域（退货订单选择 / 确认取消） -->
                <div v-if="msg.actionButtons && msg.actionButtons.length > 0" class="action-buttons-area">
                  <template v-for="(btn, bi) in msg.actionButtons" :key="bi">
                    <!-- 订单选择卡片 -->
                    <div v-if="btn.type === 'order_card'" class="action-order-card" :class="{ disabled: btn.disabled }" @click="handleActionClick(btn, index)">
                      <div class="action-order-info">
                        <span class="action-order-product">{{ btn.product }}</span>
                        <span class="action-order-id">{{ btn.order_id }}</span>
                      </div>
                      <div class="action-order-meta">
                        <n-tag :type="getStatusType(btn.status || '')" size="small" round>{{ btn.status }}</n-tag>
                        <span class="action-order-amount">{{ btn.amount }}</span>
                      </div>
                      <div class="action-order-btn-label">{{ btn.disabled ? '✔ 已选择' : '点击选择退货' }}</div>
                    </div>
                    <!-- 确认 / 取消按钮 -->
                    <button v-else class="action-btn" :class="[btn.style || 'default', { disabled: btn.disabled }]" :disabled="btn.disabled" @click="handleActionClick(btn, index)">
                      {{ btn.label }}
                    </button>
                  </template>
                </div>
                <!-- AI 消息快捷操作 -->
                <div class="message-actions ai-actions" v-if="!msg.loading">
                  <div class="msg-action-btn" title="复制" @click="copyMessage(msg.content)">
                    <n-icon><CopyOutline /></n-icon>
                  </div>
                  <div class="msg-action-btn" title="重新生成" @click="regenerateMessage(index)">
                    <n-icon><RefreshOutline /></n-icon>
                  </div>
                  <div class="msg-action-btn" title="删除" @click="deleteMessage(index)">
                    <n-icon><TrashOutline /></n-icon>
                  </div>
                </div>
              </div>
            </div>

            <!-- Avatar for User -->
            <div class="message-avatar" v-if="msg.role === 'user'">
              <n-avatar :size="30" round class="user-avatar" style="background-color: #9b72cb; color: white;">{{ userName.slice(0, 1) }}</n-avatar>
            </div>

            <!-- User 消息快捷操作（hover 显示于左侧） -->
            <div class="message-actions user-actions" v-if="msg.role === 'user'">
              <div class="msg-action-btn" title="编辑重新发送" @click="editMessage(index)">
                <n-icon><PencilOutline /></n-icon>
              </div>
              <div class="msg-action-btn" title="删除" @click="deleteMessage(index)">
                <n-icon><TrashOutline /></n-icon>
              </div>
            </div>
          </div>
        </template>
      </div>
      
      <!-- Scroll to bottom button -->
      <Transition name="fade">
        <div v-if="showScrollToBottom" class="scroll-bottom-btn" @click="scrollToBottom">
          <n-icon :size="20"><ArrowDownOutline /></n-icon>
        </div>
      </Transition>
    </div>

    <!-- 输入区域 -->
    <div class="input-area" :class="{ 'is-new-chat': messages.length === 0 && !isLoading }">
      <!-- 欢迎/空状态 -->
      <Transition name="fade-up">
        <div v-if="messages.length === 0 && !isLoading" class="greeting-container">
          <div class="greeting-hi"><span class="gradient-star">✨</span> Hi {{ userName }}</div>
          <div class="greeting-sub">有什么我可以帮助你的吗</div>
        </div>
      </Transition>

      <!-- 待发送附件预览 -->
      <Transition name="slide-up">
        <div v-if="pendingAttachments.length > 0" class="pending-attachments">
          <TransitionGroup name="att-item">
            <div v-for="(att, idx) in pendingAttachments" :key="idx" class="pending-item">
              <!-- 图片预览 -->
              <template v-if="att.type === 'image'">
                <img :src="att.url" class="pending-thumb" />
                <span class="pending-name">{{ att.name }}</span>
              </template>
              <!-- 文件 -->
              <template v-else-if="att.type === 'file'">
                <n-icon class="pending-file-icon" :size="22"><DocumentTextOutline /></n-icon>
                <span class="pending-name">{{ att.name }}</span>
                <span class="pending-size">{{ formatSize(att.size) }}</span>
              </template>
              <!-- 订单 -->
              <template v-else-if="att.type === 'order'">
                <n-icon class="pending-file-icon" :size="22"><ListOutline /></n-icon>
                <span class="pending-name">订单: {{ att.name }}</span>
              </template>
              <!-- 商品 -->
              <template v-else-if="att.type === 'product'">
                <n-icon class="pending-file-icon" :size="22"><CartOutline /></n-icon>
                <span class="pending-name">商品: {{ att.name }}</span>
              </template>
              <div class="pending-remove" @click="removeAttachment(idx)">
                <n-icon :size="14"><CloseOutline /></n-icon>
              </div>
            </div>
          </TransitionGroup>
        </div>
      </Transition>

      <div class="input-container">
        <div class="input-tools">
          <!-- Plus 按钮：下拉菜单 -->
          <n-dropdown :options="plusOptions" trigger="click" @select="handlePlusCommand">
            <div class="tool-btn" :class="{ loading: uploading }">
              <n-icon :size="20"><AddOutline /></n-icon>
            </div>
          </n-dropdown>
          <!-- 图片按钮 -->
          <div class="tool-btn" @click="handleImageSelect">
            <n-icon :size="20"><ImageOutline /></n-icon>
          </div>
        </div>
        
        <n-input
          v-model:value="inputValue"
          type="textarea"
          :autosize="{ minRows: 1, maxRows: 6 }"
          placeholder="Ask a question here"
          :bordered="false"
          class="chat-input"
          @keydown.enter.exact.prevent="handleSend"
        />
        
        <div class="input-actions">
          <div class="tool-btn" v-if="!inputValue && pendingAttachments.length === 0">
            <n-icon :size="20"><MicOutline /></n-icon>
          </div>
          <Transition name="scale">
            <div
              v-if="inputValue || pendingAttachments.length > 0"
              class="send-btn"
              :class="{ sending: sending }"
              @click="handleSend"
            >
              <n-icon :size="18" v-if="!sending"><SendOutline /></n-icon>
              <div v-else class="send-spinner"></div>
            </div>
          </Transition>
        </div>
      </div>
      <!-- Options Toggles -->
      <div class="input-extras">
        <!-- Web Search Toggle -->
        <div
          class="web-search-toggle"
          :class="{ active: webSearchEnabled }"
          @click="webSearchEnabled = !webSearchEnabled"
        >
          <n-icon :size="16"><SearchOutline /></n-icon>
          <span>{{ webSearchEnabled ? '联网搜索 · 已开启' : '联网搜索' }}</span>
        </div>
        
        <!-- Persona Selector -->
        <n-dropdown :options="personaOptions" @select="(key) => selectedPersona = key">
          <div class="persona-toggle">
            <span class="persona-icon">🎭</span>
            <span>风格: {{ personaOptions.find(o => o.key === selectedPersona)?.label.split(' ')[0] || '默认' }}</span>
          </div>
        </n-dropdown>
      </div>
      
      <Transition name="fade-up">
        <div class="suggestion-pills" v-if="messages.length === 0 && !isLoading">
          <div class="pill" @click="inputValue = '查询最近订单的物流状态'" style="animation-delay: 0.1s">
            <span>📦</span> 查询订单
          </div>
          <div class="pill" @click="inputValue = '有什么热销商品推荐吗'" style="animation-delay: 0.15s">
            <span>🛍️</span> 推荐商品
          </div>
          <div class="pill" @click="inputValue = '我想对刚才的服务做出评价'" style="animation-delay: 0.2s">
            <span>⭐</span> 服务评价
          </div>
          <div class="pill" @click="inputValue = '帮我转接人工客服'" style="animation-delay: 0.25s">
            <span>🙋</span> 人工客服
          </div>
        </div>
      </Transition>
      <div class="disclaimer">客服小鹏可能会产生不准确的信息，请核实重要内容。</div>
    </div>

    <!-- 订单选择 Drawer -->
    <n-drawer v-model:show="showOrderDrawer" :width="400" placement="right">
      <n-drawer-content title="选择订单">
        <div class="drawer-list">
          <div v-for="order in mockOrders" :key="order.order_id" class="drawer-item" @click="selectOrder(order)">
            <div class="drawer-item-top">
              <span class="drawer-item-name">{{ order.name }}</span>
              <n-tag :type="getStatusType(order.status)" size="small" round>{{ order.status }}</n-tag>
            </div>
            <div class="drawer-item-bottom">
              <span class="drawer-item-id">{{ order.order_id }}</span>
              <span class="drawer-item-price">¥{{ order.price }}</span>
            </div>
            <span class="drawer-item-date">{{ order.date }}</span>
          </div>
        </div>
      </n-drawer-content>
    </n-drawer>

    <!-- 商品选择 Drawer -->
    <n-drawer v-model:show="showProductDrawer" :width="400" placement="right">
      <n-drawer-content title="选择商品">
        <div class="drawer-list">
          <div v-for="product in mockProducts" :key="product.product_id" class="drawer-item" @click="selectProduct(product)">
            <div class="drawer-item-top">
              <span class="drawer-item-name">{{ product.name }}</span>
              <n-tag size="small" type="info" round>{{ product.category }}</n-tag>
            </div>
            <div class="drawer-item-bottom">
              <span class="drawer-item-id">{{ product.product_id }}</span>
              <span class="drawer-item-price">¥{{ product.price }}</span>
            </div>
          </div>
        </div>
      </n-drawer-content>
    </n-drawer>

    <!-- 重命名 Modal -->
    <n-modal v-model:show="showRenameModal" preset="dialog" title="Rename chat">
      <div style="margin-top: 16px;">
        <n-input v-model:value="renameTitle" placeholder="Enter new chat title" @keydown.enter="submitRename" />
      </div>
      <template #action>
        <div style="display: flex; gap: 12px;">
          <button class="pill" @click="showRenameModal = false">Cancel</button>
          <button class="pill" style="background:#0b57d0; color:white;" @click="submitRename">Save</button>
        </div>
      </template>
    </n-modal>
  </div>
  </div>
</template>

<style scoped>
/* App Layout Container */


.app-layout {
  --bg-color: #f0f4f9;
  --surface-color: #ffffff;
  --text-primary: #1f1f1f;
  --text-secondary: #444746;
  --text-tertiary: #5f6368;
  --surface-hover: #e3e8ee;
  --active-bg: #d3e3fd;
  --active-text: #041e49;
  --hover-dark: #dfe4ea;
  --primary-color: #1a73e8;

  --bg-color: var(--bg-color);
  --surface-color: var(--surface-color);
  --text-primary: var(--text-primary);
  --text-secondary: var(--text-secondary);
  --text-tertiary: var(--text-tertiary);
  --surface-hover: var(--surface-hover);
  --active-bg: var(--active-bg);
  --active-text: var(--active-text);
  --hover-dark: var(--hover-dark);
  --primary-color: #1a73e8;

  display: flex;
  height: 100vh;
  width: 100vw;
  overflow: hidden;
  background-color: var(--bg-color); /* The super subtle light grey background */
}

/* Apps and sidebar mini-state */
.sidebar-wrapper {
  width: 280px;
  background-color: var(--bg-color);
  display: flex;
  flex-direction: column;
  transition: width 0.3s cubic-bezier(0.4, 0, 0.2, 1), transform 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  overflow: hidden;
  flex-shrink: 0;
}

.sidebar-wrapper.is-collapsed {
  width: 68px; /* Instead of completely disappearing, it goes skinny */
}

/* Mobile Sidebar Styles */
.mobile-sidebar-overlay {
  display: none;
}

@media (max-width: 768px) {
  .mobile-sidebar-overlay {
    display: block;
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: rgba(0,0,0,0.5);
    z-index: 999;
    opacity: 0;
    pointer-events: none;
    transition: opacity 0.3s ease;
  }
  .mobile-sidebar-overlay.is-open {
    opacity: 1;
    pointer-events: auto;
  }
  .sidebar-wrapper {
    position: fixed;
    top: 0;
    left: 0;
    height: 100%;
    z-index: 1000;
    transform: translateX(0);
    width: 280px;
    box-shadow: 2px 0 12px rgba(0,0,0,0.1);
  }
  .sidebar-wrapper.is-collapsed {
    width: 280px;
    transform: translateX(-100%);
    box-shadow: none;
  }
}

/* Make headers fade out when collapsed */
.sidebar-wrapper.is-collapsed .sidebar-menu-header,
.sidebar-wrapper.is-collapsed .history-item,
.sidebar-wrapper.is-collapsed .sidebar-menu-item span,
.sidebar-wrapper.is-collapsed .new-chat-btn span {
  display: none;
}

/* Adjust collapsed padding for buttons */
.sidebar-wrapper.is-collapsed .new-chat-btn {
  padding: 12px;
  border-radius: 50%;
  margin: 0 auto 24px auto;
  min-width: 42px;
  display: flex;
  justify-content: center;
}

.sidebar-wrapper.is-collapsed .sidebar-menu-item {
  justify-content: center;
  padding: 10px 0;
}
.sidebar-wrapper.is-collapsed .sidebar-menu-item .icon {
  margin: 0;
}
.sidebar-wrapper.is-collapsed .user-avatar {
  margin-left: -8px;
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
  color: var(--text-secondary);
  transition: background-color 0.2s;
}

.menu-btn:hover {
  background-color: var(--hover-dark);
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
  background-color: var(--surface-hover);
  border-radius: 16px;
  display: inline-flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  margin-bottom: 24px;
  width: max-content;
  color: var(--text-primary);
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
  color: var(--text-secondary);
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  margin-bottom: 8px;
  transition: background-color 0.2s;
}

.sidebar-menu-item:hover {
  background-color: var(--surface-hover);
}

.sidebar-menu-header {
  padding: 12px;
  color: var(--text-secondary);
  font-size: 13px;
  font-weight: 600;
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.sidebar-menu-header.mt-4 {
  margin-top: 16px;
}

.chat-history-list {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.history-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 12px;
  border-radius: 12px;
  color: var(--text-secondary);
  font-size: 14px;
  cursor: pointer;
  margin-bottom: 2px;
  transition: background-color 0.2s;
  position: relative;
}

.history-title {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  flex: 1;
}

.history-more-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  border-radius: 50%;
  opacity: 0;
  transition: opacity 0.2s, background-color 0.2s;
  color: var(--text-secondary);
}

.history-item:hover .history-more-btn {
  opacity: 1;
}

.history-more-btn:hover {
  background-color: var(--hover-dark);
}

.history-item:hover {
  background-color: var(--surface-hover);
}

.history-item.active {
  background-color: var(--active-bg);
  color: var(--active-text);
  font-weight: 500;
}

.sidebar-bottom {
  margin-top: auto;
  padding-top: 16px;
}

/* ===== 主聊天区 ===== */
.chat-container {
  flex: 1;
  display: flex;
  flex-direction: column;
  background-color: var(--surface-color);
  position: relative;
  overflow: hidden;
  border-radius: 16px;
  margin: 12px 12px 12px 0;
  box-shadow: 0 4px 12px rgba(0,0,0,0.05);
}

/* Top Navigation */
.top-nav {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 24px;
  background-color: transparent;
  z-index: 10;
}

.nav-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.gemini-logo {
  font-size: 20px;
  font-weight: 400;
  color: var(--text-tertiary);
}

.nav-right {
  display: flex;
  align-items: center;
  gap: 16px;
}

.upgrade-btn {
  background-color: var(--active-bg);
  color: #0b57d0;
  padding: 8px 16px;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: background-color 0.2s;
}
.upgrade-btn:hover {
  background-color: #c2d7fa;
}

.user-avatar {
  background-color: #9b72cb;
  color: white;
  font-weight: 500;
  font-size: 16px;
  cursor: pointer;
}

.chat-area {
  flex: 1;
  width: 100%;
  overflow-y: auto;
  scroll-behavior: smooth;
}

.messages-wrapper {
  padding: 40px 0 140px;
  max-width: 800px;
  margin: 0 auto;
  width: 90%;
}

/* Greeting moved to input-area */
.greeting-container {
  width: 90%;
  max-width: 800px;
  display: flex;
  flex-direction: column;
  justify-content: flex-start;
  margin-bottom: 24px;
  animation: fadeInUp 0.5s ease;
}

.greeting-hi {
  font-size: 24px;
  font-weight: 500;
  color: var(--text-primary);
  margin-bottom: 4px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.gradient-star {
  background: linear-gradient(90deg, #4285F4, #9B72CB, #D96570);
  background-clip: text;
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}

.greeting-sub {
  font-size: 32px;
  font-weight: 400;
  color: var(--text-primary);
  animation: fadeInUp 0.6s ease 0.1s both;
}

/* Suggestion Pills */
.suggestion-pills {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  justify-content: center;
  margin-top: 24px;
  margin-bottom: 8px;
  pointer-events: auto;
}

.pill {
  background: var(--bg-color);
  border-radius: 20px;
  padding: 10px 20px;
  font-size: 14px;
  color: var(--text-primary);
  cursor: pointer;
  transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
  white-space: nowrap;
  display: flex;
  align-items: center;
  gap: 6px;
  font-weight: 400;
  animation: fadeInUp 0.4s ease both;
}

.pill:hover {
  background: #dde3ea;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.08);
  transform: translateY(-2px);
}

.pill:active {
  transform: translateY(0);
}

/* Messages */
.message-row {
  display: flex;
  gap: 16px;
  margin-bottom: 32px;
  width: 100%;
  animation: fadeInUp 0.3s ease;
}

.message-row.user {
  justify-content: flex-end;
  animation: slideInRight 0.3s ease;
}

.message-row.assistant {
  animation: slideInLeft 0.3s ease;
}

.message-avatar {
  flex-shrink: 0;
  margin-top: 4px;
}

.ai-avatar {
  background: linear-gradient(135deg, #4285f4, #9b72cb);
  color: var(--surface-color);
}

.message-heading {
  margin-bottom: 4px;
}

.sender-name {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-secondary);
}

/* User Bubble */
.user .message-bubble {
  background: var(--bg-color);
  border-radius: 20px 4px 20px 20px;
  padding: 12px 20px;
  max-width: 80%;
}

/* AI Bubble */
.assistant .message-bubble {
  background: transparent;
  padding: 0;
  max-width: 100%;
}

.message-content {
  font-size: 16px;
  line-height: 1.7;
  color: var(--text-primary);
}

/* Typing Indicator */
.typing-indicator {
  display: flex;
  gap: 4px;
  padding: 8px 0;
}

.typing-indicator span {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: linear-gradient(135deg, #4285f4, #9b72cb);
  animation: typingBounce 1.4s ease-in-out infinite;
}

.typing-indicator span:nth-child(1) { animation-delay: 0s; }
.typing-indicator span:nth-child(2) { animation-delay: 0.2s; }
.typing-indicator span:nth-child(3) { animation-delay: 0.4s; }

@keyframes typingBounce {
  0%, 60%, 100% { 
    transform: translateY(0); 
    opacity: 0.4;
  }
  30% { 
    transform: translateY(-8px); 
    opacity: 1;
  }
}

/* ===== 消息附件渲染 ===== */
.msg-attachments {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  margin-bottom: 12px;
}

.att-image {
  max-width: 280px;
  border-radius: 12px;
  overflow: hidden;
  cursor: pointer;
}

.att-image img {
  width: 100%;
  display: block;
  border-radius: 12px;
  transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.att-image img:hover {
  transform: scale(1.03);
}

.att-file {
  display: flex;
  align-items: center;
  gap: 10px;
  background: var(--surface-color);
  border-radius: 12px;
  padding: 12px 16px;
  min-width: 220px;
  transition: all 0.2s;
}

.att-file:hover {
  background: var(--surface-hover);
}

.att-file-icon {
  color: var(--primary-color);
}

.att-file-info {
  display: flex;
  flex-direction: column;
  flex: 1;
}

.att-file-name {
  font-size: 14px;
  color: var(--text-primary);
  font-weight: 500;
}

.att-file-size {
  font-size: 12px;
  color: var(--text-tertiary);
}

.att-download {
  color: var(--primary-color);
  font-size: 20px;
  cursor: pointer;
  text-decoration: none;
  transition: color 0.2s;
}

.att-download:hover {
  color: #1a73e8;
}

/* 订单/商品卡片 */
.att-order,
.att-product {
  background: var(--surface-color);
  border-radius: 12px;
  padding: 14px 16px;
  min-width: 240px;
  max-width: 320px;
  border-left: 3px solid var(--primary-color);
  transition: all 0.2s;
}

.att-order:hover,
.att-product:hover {
  transform: translateY(-1px);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
}

.att-card-header {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: var(--text-secondary);
  margin-bottom: 8px;
}

.att-card-body {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.att-card-title {
  font-size: 15px;
  font-weight: 500;
  color: var(--text-primary);
}

.att-card-id {
  font-size: 12px;
  color: var(--text-tertiary);
}

.att-card-price {
  margin-top: 8px;
  font-size: 18px;
  font-weight: 600;
  color: #f59e0b;
}

/* ===== 待发送附件预览 ===== */
.pending-attachments {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  width: 90%;
  max-width: 800px;
  margin-bottom: 8px;
  pointer-events: auto;
}

.pending-item {
  display: flex;
  align-items: center;
  gap: 8px;
  background: var(--surface-color);
  border-radius: 10px;
  padding: 6px 10px;
  max-width: 260px;
  position: relative;
  animation: scaleIn 0.2s ease;
}

.pending-thumb {
  width: 40px;
  height: 40px;
  border-radius: 6px;
  object-fit: cover;
}

.pending-file-icon {
  color: var(--primary-color);
}

.pending-name {
  font-size: 13px;
  color: var(--text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 140px;
}

.pending-size {
  font-size: 11px;
  color: var(--text-tertiary);
}

.pending-remove {
  width: 20px;
  height: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  color: var(--text-secondary);
  border-radius: 50%;
  transition: all 0.2s;
}

.pending-remove:hover {
  background: rgba(0, 0, 0, 0.08);
  color: #e53935;
}

/* Transition for attachments */
.slide-up-enter-active,
.slide-up-leave-active {
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.slide-up-enter-from,
.slide-up-leave-to {
  opacity: 0;
  transform: translateY(10px);
}

.att-item-enter-active {
  transition: all 0.2s ease;
}
.att-item-leave-active {
  transition: all 0.15s ease;
}
.att-item-enter-from {
  opacity: 0;
  transform: scale(0.8);
}
.att-item-leave-to {
  opacity: 0;
  transform: scale(0.8);
}

/* Scale transition for send button */
.scale-enter-active {
  transition: all 0.2s cubic-bezier(0.34, 1.56, 0.64, 1);
}
.scale-leave-active {
  transition: all 0.15s ease;
}
.scale-enter-from,
.scale-leave-to {
  opacity: 0;
  transform: scale(0.5);
}

/* ===== 输入区域 ===== */
.input-area {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  z-index: 100;
  background: linear-gradient(to bottom, transparent 0%, var(--surface-color) 25%, var(--surface-color) 100%);
  padding-bottom: 20px;
  pointer-events: none;
  transition: all 0.5s cubic-bezier(0.4, 0, 0.2, 1);
}

.input-area.is-new-chat {
  top: 0;
  bottom: 0;
  justify-content: center;
  background: transparent;
  padding-bottom: 10vh; /* Adjust vertical centering visually */
}

.input-container {
  pointer-events: auto;
  width: 90%;
  max-width: 800px;
  background: var(--bg-color);
  border-radius: 36px;
  display: flex;
  align-items: flex-end;
  padding: 8px 12px 8px 16px;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  border: 1px solid transparent;
}

.input-area.is-new-chat .input-container {
  box-shadow: 0 1px 6px rgba(0, 0, 0, 0.08); /* subtle shadow like Gemini */
  background: var(--surface-color);
}

.input-container:focus-within {
  background: var(--surface-color);
  border-color: #c8d0d9;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.12);
  transform: translateY(-2px);
}

.input-tools {
  display: flex;
  margin-bottom: 4px;
  gap: 2px;
}

.tool-btn {
  width: 36px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-secondary);
  cursor: pointer;
  border-radius: 50%;
  transition: all 0.2s;
}

.tool-btn:hover {
  background: rgba(0, 0, 0, 0.06);
  color: var(--primary-color);
  transform: scale(1.08);
}

.tool-btn:active {
  transform: scale(0.95);
}

.chat-input {
  flex: 1;
  margin: 0 8px;
  padding-bottom: 4px;
}

:deep(.chat-input .n-input__textarea-el) {
  font-size: 16px;
  line-height: 1.5;
  font-family: inherit;
}

.input-actions {
  display: flex;
  align-items: center;
  margin-bottom: 4px;
}

.send-btn {
  width: 36px;
  height: 36px;
  background: linear-gradient(135deg, #4285f4, #1a73e8);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--surface-color);
  cursor: pointer;
  transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
}

.send-btn:hover {
  transform: scale(1.08);
  box-shadow: 0 2px 12px rgba(66, 133, 244, 0.4);
}

.send-btn:active {
  transform: scale(0.95);
}

.send-btn.sending {
  pointer-events: none;
  opacity: 0.7;
}

.send-spinner {
  width: 16px;
  height: 16px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-top-color: var(--surface-color);
  border-radius: 50%;
  animation: spin 0.6s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.disclaimer {
  margin-top: 8px;
  font-size: 12px;
  color: var(--text-tertiary);
  pointer-events: auto;
}

/* Web Search Toggle */
.input-extras {
  display: flex;
  justify-content: center;
  gap: 16px;
  margin-top: 12px;
  pointer-events: auto;
}

.web-search-toggle,
.persona-toggle {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 16px;
  background: var(--surface-color);
  border-radius: 20px;
  font-size: 13px;
  color: var(--text-secondary);
  cursor: pointer;
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
  border: 1px solid transparent;
  user-select: none;
}

.web-search-toggle:hover,
.persona-toggle:hover {
  background: var(--bg-color);
  color: var(--text-primary);
}

.web-search-toggle.active {
  background: #e8f0fe;
  color: #1a73e8;
  border-color: #d2e3fc;
}

.web-search-toggle.active n-icon {
  color: #1a73e8;
}

.persona-icon {
  font-size: 14px;
}

/* ===== Drawer 样式 ===== */
.drawer-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.drawer-item {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 16px;
  border-radius: 12px;
  background: var(--surface-color);
  cursor: pointer;
  transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
  border: 1px solid transparent;
}

.drawer-item:hover {
  background: var(--surface-hover);
  border-color: var(--primary-color);
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.06);
}

.drawer-item-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.drawer-item-name {
  font-size: 15px;
  font-weight: 500;
  color: var(--text-primary);
}

.drawer-item-bottom {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.drawer-item-id {
  font-size: 12px;
  color: var(--text-tertiary);
}

.drawer-item-price {
  font-size: 16px;
  font-weight: 600;
  color: #f59e0b;
}

.drawer-item-date {
  font-size: 12px;
  color: var(--text-tertiary);
}

/* Markdown overrides */
:deep(.message-content p) {
  margin-bottom: 16px;
}
:deep(.message-content pre) {
  background: #1E1F20;
  border-radius: 8px;
  padding: 16px;
  overflow-x: auto;
  color: #e3e3e3;
}
:deep(.message-content code) {
  font-family: 'Fira Code', 'Cascadia Code', monospace;
  font-size: 14px;
}

/* ===== 思考过程样式 ===== */
.thinking-section {
  margin-bottom: 12px;
  border-radius: 12px;
  background: rgba(66, 133, 244, 0.06);
  border-left: 3px solid;
  border-image: linear-gradient(180deg, #4285F4, #9B72CB) 1;
  overflow: hidden;
  transition: opacity 0.3s, max-height 0.4s ease;
}

.thinking-section.collapsed {
  opacity: 0.7;
}

.thinking-summary {
  cursor: pointer;
  padding: 10px 14px;
  font-size: 13px;
  color: var(--text-secondary);
  user-select: none;
  list-style: none;
  display: flex;
  align-items: center;
  gap: 6px;
}

.thinking-summary::-webkit-details-marker {
  display: none;
}

.thinking-label {
  font-weight: 500;
}

.thinking-steps {
  padding: 0 14px 12px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.thinking-step {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  animation: fadeInUp 0.3s ease both;
}

.step-icon {
  font-size: 16px;
  line-height: 1;
  flex-shrink: 0;
  margin-top: 2px;
}

.step-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.step-label {
  font-size: 13px;
  color: var(--text-secondary);
  font-weight: 500;
}

.step-content {
  font-size: 12px;
  color: var(--text-tertiary);
  word-break: break-word;
}

:deep(.code-block-wrapper) {
  background: #1e1e1e;
  border-radius: 8px;
  margin: 12px 0;
  overflow: hidden;
  color: #d4d4d4;
  font-family: 'Consolas', monospace;
}
:deep(.code-block-header) {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 16px;
  background: #2d2d2d;
  font-size: 12px;
  color: #858585;
}
:deep(.copy-code-btn) {
  background: transparent;
  border: none;
  color: #858585;
  cursor: pointer;
  font-size: 12px;
  padding: 4px 8px;
  border-radius: 4px;
  transition: all 0.2s;
}
:deep(.copy-code-btn:hover) {
  background: #3d3d3d;
  color: #d4d4d4;
}
:deep(.code-block-wrapper pre) {
  margin: 0;
  padding: 16px;
  overflow-x: auto;
}
:deep(.code-block-wrapper code) {
  font-family: inherit;
}

/* ===== 交互按钮区域 ===== */
.action-buttons-area {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-top: 14px;
  padding-top: 14px;
  border-top: 1px solid rgba(0, 0, 0, 0.06);
}

/* 订单选择卡片 */
.action-order-card {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 14px 16px;
  border: 1.5px solid #e0e0e0;
  border-radius: 14px;
  cursor: pointer;
  transition: all 0.25s ease;
  background: linear-gradient(135deg, #fafbff 0%, #f5f5ff 100%);
  min-width: 200px;
  flex: 1;
  max-width: 280px;
}
.action-order-card:hover:not(.disabled) {
  border-color: #7c4dff;
  background: linear-gradient(135deg, #f3efff 0%, #ede7ff 100%);
  box-shadow: 0 2px 12px rgba(124, 77, 255, 0.15);
  transform: translateY(-2px);
}
.action-order-card.disabled {
  opacity: 0.55;
  cursor: not-allowed;
  pointer-events: none;
}
.action-order-info {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.action-order-product {
  font-weight: 600;
  font-size: 13.5px;
  color: #1a1a2e;
}
.action-order-id {
  font-size: 11px;
  color: #888;
  font-family: 'Courier New', monospace;
}
.action-order-meta {
  display: flex;
  align-items: center;
  gap: 8px;
}
.action-order-amount {
  font-size: 14px;
  font-weight: 600;
  color: #7c4dff;
}
.action-order-btn-label {
  font-size: 12px;
  color: #7c4dff;
  font-weight: 500;
  text-align: center;
  margin-top: 4px;
  padding-top: 6px;
  border-top: 1px dashed rgba(124, 77, 255, 0.2);
}

/* 确认 / 取消按钮 */
.action-btn {
  padding: 10px 28px;
  border-radius: 24px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.25s ease;
  border: 1.5px solid #e0e0e0;
  background: var(--surface-color);
  color: #333;
  display: inline-flex;
  align-items: center;
  gap: 6px;
}
.action-btn:hover:not(.disabled) {
  transform: translateY(-1px);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}
.action-btn.primary {
  background: linear-gradient(135deg, #7c4dff 0%, #651fff 100%);
  color: white;
  border-color: transparent;
}
.action-btn.primary:hover:not(.disabled) {
  background: linear-gradient(135deg, #651fff 0%, #536dfe 100%);
  box-shadow: 0 4px 16px rgba(124, 77, 255, 0.35);
}
.action-btn.default {
  background: #f5f5f5;
  color: #555;
}
.action-btn.default:hover:not(.disabled) {
  background: #e8e8e8;
}
.action-btn.disabled {
  opacity: 0.45;
  cursor: not-allowed;
  pointer-events: none;
}

/* ===== 拖拽上传覆盖层 ===== */
.drag-overlay {
  position: absolute;
  top: 12px;
  left: 12px;
  right: 12px;
  bottom: 12px;
  background: rgba(255, 255, 255, 0.85);
  backdrop-filter: blur(4px);
  z-index: 9999;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 4px dashed #7c4dff;
  border-radius: 16px;
}

.drag-overlay-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
  color: #7c4dff;
  font-size: 20px;
  font-weight: 500;
  pointer-events: none;
}

/* ===== 消息快捷操作 ===== */
.message-actions {
  display: flex;
  gap: 4px;
  opacity: 0;
  transition: opacity 0.2s ease;
  margin-top: 4px;
}

.message-row:hover .message-actions {
  opacity: 1;
}

@media (max-width: 768px) {
  .message-actions {
    opacity: 1; /* Always show on mobile */
  }
}

.ai-actions {
  justify-content: flex-start;
  padding-left: 12px;
}

.user-actions {
  justify-content: flex-end;
  padding-right: 12px;
}

.msg-action-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border-radius: 6px;
  color: var(--text-tertiary);
  cursor: pointer;
  transition: all 0.2s ease;
}

.msg-action-btn:hover {
  background-color: var(--bg-color);
  color: #1a73e8;
}

/* ===== 回到最新消息按钮 ===== */
.scroll-bottom-btn {
  position: absolute;
  bottom: 140px;
  left: 50%;
  transform: translateX(-50%);
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: var(--surface-color);
  border: 1px solid #e0e0e0;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  color: var(--text-tertiary);
  z-index: 100;
  transition: all 0.2s;
}

.scroll-bottom-btn:hover {
  background: #f8f9fa;
  color: #1a73e8;
  transform: translateX(-50%) translateY(-2px);
  box-shadow: 0 6px 16px rgba(0, 0, 0, 0.12);
}
</style>
