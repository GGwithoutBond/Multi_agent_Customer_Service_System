<script setup lang="ts">
import { ref, onMounted, onUnmounted, nextTick, watch, computed, h } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useMessage, useDialog, NIcon, NAvatar, NInput, NTag, NDropdown, NDrawer, NDrawerContent, NModal, NRate, NCheckbox } from 'naive-ui'
import {
  SendOutline,
  ImageOutline,
  MicOutline,
  AddOutline,
  DocumentTextOutline,
  CartOutline,
  ListOutline,
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
  ArrowDownOutline,
  MenuOutline,
  CreateOutline,
  EllipsisVertical
} from '@vicons/ionicons5'
import hljs from 'highlight.js/lib/core'
import bash from 'highlight.js/lib/languages/bash'
import css from 'highlight.js/lib/languages/css'
import javascript from 'highlight.js/lib/languages/javascript'
import json from 'highlight.js/lib/languages/json'
import markdown from 'highlight.js/lib/languages/markdown'
import python from 'highlight.js/lib/languages/python'
import sql from 'highlight.js/lib/languages/sql'
import typescript from 'highlight.js/lib/languages/typescript'
import xml from 'highlight.js/lib/languages/xml'
import 'highlight.js/styles/github-dark.css'
import MarkdownIt from 'markdown-it'
import { getMessages, getMessagesHistory, uploadFile, getAvailableOrders, getAvailableProducts, submitMessageFeedback } from '@/api/chat'
import { updateConversation, getConversations, deleteConversation, updateConversationPin, batchDeleteConversations } from '@/api/conversation'
import { useUserStore } from '@/stores/user'
import { useChatStreamController } from '@/composables/useChatStreamController'
import MessageActionBar from '@/components/chat/MessageActionBar.vue'
import StreamStatusCard from '@/components/chat/StreamStatusCard.vue'
import AttachmentItemCard from '@/components/chat/AttachmentItemCard.vue'

const emit = defineEmits<{
  refresh: []
}>()

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()
const message = useMessage()
const dialog = useDialog()

hljs.registerLanguage('bash', bash)
hljs.registerLanguage('css', css)
hljs.registerLanguage('javascript', javascript)
hljs.registerLanguage('js', javascript)
hljs.registerLanguage('json', json)
hljs.registerLanguage('markdown', markdown)
hljs.registerLanguage('md', markdown)
hljs.registerLanguage('python', python)
hljs.registerLanguage('py', python)
hljs.registerLanguage('sql', sql)
hljs.registerLanguage('typescript', typescript)
hljs.registerLanguage('ts', typescript)
hljs.registerLanguage('html', xml)
hljs.registerLanguage('xml', xml)

function renderIcon(icon: any) {
  return () => h(NIcon, null, { default: () => h(icon) })
}

// Markdown 渲染

// Markdown rendering
const md = new MarkdownIt({
  html: false,
  breaks: true,
  linkify: true,
  highlight: function (str: string, lang: string) {
    const langstr = lang ? `<span class="code-lang">${lang}</span>` : ''
    let codeStr = ''
    if (lang && hljs.getLanguage(lang)) {
      try {
        codeStr = hljs.highlight(str, { language: lang, ignoreIllegals: true }).value
      } catch (__) {
        codeStr = md.utils.escapeHtml(str)
      }
    } else {
      codeStr = md.utils.escapeHtml(str)
    }

    const encodedStr = encodeURIComponent(str)

    return `<div class="code-block-wrapper">
      <div class="code-block-header">
        ${langstr}
        <button class="copy-code-btn" onclick="navigator.clipboard.writeText(decodeURIComponent('${encodedStr}')); this.innerText='已复制'; setTimeout(() => this.innerText='复制', 2000)">复制</button>
      </div>
      <pre class="hljs"><code>${codeStr}</code></pre>
    </div>`
  },
})

const renderMarkdown = (content: string) => md.render(content || '')

type StructuredKind = 'conclusion' | 'steps' | 'tips' | 'data'

interface StructuredMetric {
  label: string
  value: string
}

interface StructuredBlock {
  kind: StructuredKind
  title: string
  items: string[]
  metrics?: StructuredMetric[]
}

const STATUS_REGEX = /(delivered|shipped|processing|pending|cancelled|refunding|completed|signed|\u5df2\u7b7e\u6536|\u5df2\u53d1\u8d27|\u5904\u7406\u4e2d|\u5f85\u4ed8\u6b3e|\u9000\u6b3e\u4e2d|\u5df2\u5b8c\u6210)/gi
const DATE_REGEX = /(\d{4}[-/.]\d{1,2}[-/.]\d{1,2}(?:\s+\d{1,2}:\d{1,2})?)/g
const ORDER_REGEX = /\bORD-\d+\b/gi
const AMOUNT_REGEX = /(?:\u00a5|\uffe5|\$)\s?\d+(?:\.\d{1,2})?/g
const STATUS_PATTERN = '(?:delivered|shipped|processing|pending|cancelled|refunding|completed|signed|\u5df2\u7b7e\u6536|\u5df2\u53d1\u8d27|\u5904\u7406\u4e2d|\u5f85\u4ed8\u6b3e|\u9000\u6b3e\u4e2d|\u5df2\u5b8c\u6210)'
const ORDER_STATUS_PAIR_REGEX = new RegExp(
  `(ORD-\\d+)[\\s\\S]{0,80}?(?:\\||\uff0c|,|;|\\s)*(?:status|\\u72b6\\u6001)\\s*[:\uff1a]?\\s*[*_\\s]*(${STATUS_PATTERN})`,
  'gi',
)

const dedupe = (values: string[]) => [...new Set(values.filter(Boolean))]

const extractOrderStatusPairs = (content: string): StructuredMetric[] => {
  const pairs: StructuredMetric[] = []
  const seen = new Set<string>()
  let match: RegExpExecArray | null

  while ((match = ORDER_STATUS_PAIR_REGEX.exec(content)) !== null) {
    const orderId = (match[1] || '').toUpperCase().trim()
    const status = (match[2] || '').trim()
    if (!orderId || !status) continue
    const key = `${orderId}::${status}`
    if (seen.has(key)) continue
    seen.add(key)
    pairs.push({
      label: orderId,
      value: status,
    })
  }

  return pairs
}

const parseStructuredBlocks = (content: string): StructuredBlock[] => {
  const normalized = (content || '').replace(/\r\n/g, '\n').trim()
  if (!normalized) return []

  const lines = normalized.split('\n').map(l => l.trim()).filter(Boolean)
  if (!lines.length) return []

  const sectionMap: Record<StructuredKind, RegExp> = {
    conclusion: /(conclusion|summary|answer|result|\u7ed3\u8bba|\u603b\u7ed3|\u7b54\u6848|\u5904\u7406\u7ed3\u679c)/i,
    steps: /(steps|workflow|process|how to|\u64cd\u4f5c\u6b65\u9aa4|\u6d41\u7a0b|\u6b65\u9aa4)/i,
    tips: /(tips|note|warning|risk|\u63d0\u793a|\u6ce8\u610f|\u98ce\u9669|\u5efa\u8bae)/i,
    data: /(data|key info|details|metrics|\u5173\u952e\u4fe1\u606f|\u6570\u636e|\u660e\u7ec6|\u53c2\u6570)/i,
  }

  const titleMap: Record<StructuredKind, string> = {
    conclusion: '\u7ed3\u8bba',
    steps: '\u6b65\u9aa4',
    tips: '\u6ce8\u610f\u9879',
    data: '\u5173\u952e\u6570\u636e',
  }

  const blocks: StructuredBlock[] = []
  let currentKind: StructuredKind | null = null
  let currentItems: string[] = []
  let hasStructuredSignal = false

  const flushCurrent = () => {
    if (!currentKind || !currentItems.length) return
    blocks.push({
      kind: currentKind,
      title: titleMap[currentKind],
      items: dedupe(currentItems),
    })
    currentItems = []
  }

  for (const line of lines) {
    const headingCandidate = line.replace(/^#+\s*/, '').replace(/[:\uff1a]$/, '')
    const matchedSection = (Object.keys(sectionMap) as StructuredKind[]).find(k => sectionMap[k].test(headingCandidate))
    if (matchedSection) {
      flushCurrent()
      currentKind = matchedSection
      hasStructuredSignal = true
      continue
    }

    const isBullet = /^[-*•]\s+/.test(line)
    const isNumbered = /^\d+[.)]\s+/.test(line)
    const item = isBullet
      ? line.replace(/^[-*•]\s+/, '')
      : isNumbered
        ? line.replace(/^\d+[.)]\s+/, '')
        : line

    if (isBullet || isNumbered) {
      if (!currentKind) currentKind = 'steps'
      hasStructuredSignal = true
      currentItems.push(item)
      continue
    }

    if (!currentKind) currentKind = 'conclusion'
    currentItems.push(item)
  }
  flushCurrent()

  const metrics: StructuredMetric[] = []
  const pairedOrderStatus = extractOrderStatusPairs(normalized)
  if (pairedOrderStatus.length > 0) {
    metrics.push(...pairedOrderStatus)
  } else {
    dedupe(normalized.match(ORDER_REGEX) || []).forEach(v => metrics.push({ label: '\u8ba2\u5355\u53f7', value: v }))
    dedupe(normalized.match(STATUS_REGEX) || []).forEach(v => metrics.push({ label: '\u72b6\u6001', value: v }))
  }
  dedupe(normalized.match(AMOUNT_REGEX) || []).forEach(v => metrics.push({ label: '\u91d1\u989d', value: v }))
  dedupe(normalized.match(DATE_REGEX) || []).forEach(v => metrics.push({ label: '\u65f6\u95f4', value: v }))

  if (metrics.length) {
    blocks.push({
      kind: 'data',
      title: '\u5173\u952e\u6570\u636e',
      items: [],
      metrics: dedupe(metrics.map(m => `${m.label}:${m.value}`)).map(item => {
        const [label, ...rest] = item.split(':')
        return { label, value: rest.join(':') }
      }),
    })
    hasStructuredSignal = true
  }

  return hasStructuredSignal ? blocks : []
}

const finalizeAssistantMessage = (msg: any) => {
  if (!msg || msg.role !== 'assistant') return
  const text = (msg.content || '').trim()
  if (!text) return
  const blocks = parseStructuredBlocks(text)
  msg.structuredBlocks = blocks
  msg.renderedHtml = blocks.length ? '' : renderMarkdown(text)
}

const conversationId = ref<string>('')
const messages = ref<any[]>([])
const inputValue = ref('')
const isLoading = ref(false)
// 控制是否显示欢迎语：默认 false，仅确认是新会话后才显示
const showWelcome = ref(false)
const scrollContainerRef = ref<HTMLElement>()
const innerRef = ref()
const sending = ref(false)
const webSearchEnabled = ref(false)
const showScrollToBottom = ref(false)
const isDraggingFile = ref(false)
const activeAiMessageIndex = ref<number | null>(null)
const networkOffline = ref(typeof navigator !== 'undefined' ? !navigator.onLine : false)
const dismissOfflineNotice = ref(false)

const streamController = useChatStreamController<any>()
const showStreamRecovery = computed(
  () => streamController.canRecover.value || (networkOffline.value && !dismissOfflineNotice.value),
)

const isSidebarOpen = ref(window.innerWidth > 768)
const conversations = ref<any[]>([])
const batchMode = ref(false)
const selectedConversationIds = ref<string[]>([])
const historyHasMore = ref(false)
const historyCursor = ref<string | null>(null)
const historyLoading = ref(false)
const showFeedbackModal = ref(false)
const feedbackMessageId = ref<string>('')
const feedbackRating = ref(0)
const feedbackComment = ref('')

const normalizeMessage = (msg: any) => {
  if (msg.metadata_) {
    if (msg.metadata_.attachments) {
      msg.attachments = msg.metadata_.attachments
    }
    if (msg.metadata_.action_button_prompt) {
      msg.actionButtonPrompt = msg.metadata_.action_button_prompt
    }
    if (msg.metadata_.action_buttons) {
      msg.actionButtons = msg.metadata_.action_buttons.map((a: any) => ({ ...a, disabled: false }))
    }
  }
  finalizeAssistantMessage(msg)
  return msg
}

const fetchConversationList = async () => {
  try {
    const res: any = await getConversations()
    const items = Array.isArray(res) ? res : (res.data || [])
    conversations.value = items.sort((a: any, b: any) => Number(!!b.is_pinned) - Number(!!a.is_pinned))
    selectedConversationIds.value = selectedConversationIds.value.filter(id => conversations.value.some(c => c.id === id))
  } catch (error) {
    console.error('获取历史会话失败', error)
  }
}

const toggleSidebar = () => {
  isSidebarOpen.value = !isSidebarOpen.value
}

const handleNewChat = () => {
  batchMode.value = false
  selectedConversationIds.value = []
  router.push('/')
}

const handleSelectChat = (id: string) => {
  if (batchMode.value) {
    toggleConversationSelect(id)
    return
  }
  router.push(`/chat/${id}`)
}

// ===== 历史会话操作（更多选项） =====
const showRenameModal = ref(false)
const renameId = ref('')
const renameTitle = ref('')

const chatOptions = [
  { label: '分享会话', key: 'share', icon: renderIcon(ShareOutline) },
  { label: '置顶/取消置顶', key: 'pin', icon: renderIcon(PinOutline) },
  { label: '重命名', key: 'rename', icon: renderIcon(PencilOutline) },
  { label: '删除', key: 'delete', icon: renderIcon(TrashOutline) }
]

const toggleBatchMode = () => {
  batchMode.value = !batchMode.value
  if (!batchMode.value) {
    selectedConversationIds.value = []
  }
}

const toggleConversationSelect = (id: string) => {
  if (!batchMode.value) return
  if (selectedConversationIds.value.includes(id)) {
    selectedConversationIds.value = selectedConversationIds.value.filter(item => item !== id)
  } else {
    selectedConversationIds.value.push(id)
  }
}

const handleBatchDelete = async () => {
  if (selectedConversationIds.value.length === 0) {
    message.info('请先选择要删除的会话')
    return
  }
  const ids = [...selectedConversationIds.value]
  dialog.warning({
    title: '批量删除会话',
    content: `确认删除选中的 ${ids.length} 个会话吗？`,
    positiveText: '确认删除',
    negativeText: '取消',
    async onPositiveClick() {
      try {
        await batchDeleteConversations(ids)
        if (conversationId.value && ids.includes(conversationId.value)) {
          router.push('/')
        }
        message.success('批量删除完成')
        selectedConversationIds.value = []
        batchMode.value = false
        fetchConversationList()
      } catch (err) {
        message.error('批量删除失败，请稍后重试')
      }
    }
  })
}

const handleChatOption = async (key: string, id: string) => {
  if (key === 'share') {
    const shareUrl = `${window.location.origin}/chat/${id}`
    try {
      await navigator.clipboard.writeText(shareUrl)
      message.success('会话链接已复制')
    } catch (_err) {
      message.error('复制失败，请手动复制地址栏链接')
    }
  } else if (key === 'pin') {
    const chat = conversations.value.find(c => c.id === id)
    if (!chat) return
    const targetPinned = !chat.is_pinned
    try {
      await updateConversationPin(id, targetPinned)
      chat.is_pinned = targetPinned
      message.success(targetPinned ? '会话已置顶' : '会话已取消置顶')
      fetchConversationList()
    } catch (_err) {
      message.error('置顶状态更新失败')
    }
  } else if (key === 'rename') {
    const chat = conversations.value.find(c => c.id === id)
    if (chat) {
      renameId.value = id
      renameTitle.value = chat.title || ''
      showRenameModal.value = true
    }
  } else if (key === 'delete') {
    dialog.warning({
      title: '删除会话',
      content: '确定要删除这段会话吗？此操作不可恢复。',
      positiveText: '确认删除',
      negativeText: '取消',
      async onPositiveClick() {
        try {
          await deleteConversation(id)
          if (conversationId.value === id) {
            router.push('/')
          } else {
            fetchConversationList()
          }
          message.success('会话已删除')
        } catch (err) {
          message.error('删除失败，请稍后重试')
        }
      },
    })
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
  { label: '专业型', key: 'professional' },
  { label: '亲切型', key: 'friendly' },
  { label: '技术型', key: 'technical' }
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

interface OrderOption {
  order_id: string
  name: string
  status: string
  price: number
  date?: string
}

interface ProductOption {
  product_id: string
  name: string
  price: number
  category?: string
  image?: string
}

const pendingAttachments = ref<AttachmentItem[]>([])
const imageInputRef = ref<HTMLInputElement>()
const fileInputRef = ref<HTMLInputElement>()
const uploading = ref(false)
const showOrderDrawer = ref(false)
const showProductDrawer = ref(false)
const orderOptions = ref<OrderOption[]>([])
const productOptions = ref<ProductOption[]>([])
const loadingOrderOptions = ref(false)
const loadingProductOptions = ref(false)

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

const settingsOptions = [
  { label: '活动记录', key: 'activity', icon: renderIcon(TimeOutline) },
  { label: '对话指令设置', key: 'instructions', icon: renderIcon(PersonOutline) },
  { label: '已连接应用', key: 'apps', icon: renderIcon(AppsOutline) },
  { type: 'divider', key: 'd1' },
  { label: '公开链接', key: 'links', icon: renderIcon(LinkOutline) },
  { type: 'divider', key: 'd2' },
  { label: '主题', key: 'theme', icon: renderIcon(SunnyOutline) },
  { type: 'divider', key: 'd3' },
  { label: '订阅管理', key: 'subscriptions', icon: renderIcon(CardOutline) },
  { type: 'divider', key: 'd4' },
  { label: '笔记本', key: 'notebook', icon: renderIcon(BookOutline) },
  { type: 'divider', key: 'd5' },
  { label: '提交反馈', key: 'feedback', icon: renderIcon(ChatboxEllipsesOutline) },
  { type: 'divider', key: 'd6' },
  { label: '帮助', key: 'help', icon: renderIcon(HelpCircleOutline) },
  { type: 'divider', key: 'd7' },
  { label: '上海，中国', key: 'location', icon: renderIcon(LocationOutline) },
  { type: 'divider', key: 'd8' },
  { label: '退出登录', key: 'logout', icon: renderIcon(LogOutOutline) }
]

const handleSettingsSelect = (key: string) => {
  if (key === 'feedback') {
    const latestAssistantMessage = [...messages.value].reverse().find(msg => msg.role === 'assistant' && msg.id)
    if (!latestAssistantMessage?.id) {
      message.info('当前会话暂无可反馈的机器人回复')
      return
    }
    feedbackMessageId.value = latestAssistantMessage.id
    feedbackRating.value = 0
    feedbackComment.value = ''
    showFeedbackModal.value = true
  } else if (key === 'logout') {
    userStore.logout()
    router.push('/login')
  }
}

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

const removeAttachment = (index: number) => {
  pendingAttachments.value.splice(index, 1)
}

const selectOrder = (order: OrderOption) => {
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

const loadOrderOptions = async () => {
  loadingOrderOptions.value = true
  try {
    const res: any = await getAvailableOrders()
    orderOptions.value = Array.isArray(res) ? res : (res.data || [])
  } catch (error) {
    console.error('获取订单列表失败', error)
    orderOptions.value = []
    message.error('获取订单列表失败')
  } finally {
    loadingOrderOptions.value = false
  }
}

const copyMessage = (content: string) => {
  navigator.clipboard.writeText(content)
  message.success('内容已复制')
}

const openFeedbackForMessage = (msg: any) => {
  if (!msg?.id) {
    message.warning('该消息暂不支持反馈')
    return
  }
  feedbackMessageId.value = msg.id
  feedbackRating.value = 0
  feedbackComment.value = ''
  showFeedbackModal.value = true
}

const submitFeedback = async () => {
  if (!feedbackMessageId.value) {
    message.warning('缺少反馈目标消息')
    return
  }
  if (!feedbackRating.value) {
    message.warning('请先评分')
    return
  }

  try {
    await submitMessageFeedback({
      message_id: feedbackMessageId.value,
      rating: feedbackRating.value,
      comment: feedbackComment.value.trim() || undefined,
    })
    showFeedbackModal.value = false
    message.success('反馈已提交，感谢你的建议')
  } catch (_err) {
    message.error('反馈提交失败，请稍后重试')
  }
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
  dialog.warning({
    title: '删除消息',
    content: '确认删除这条消息吗？',
    positiveText: '删除',
    negativeText: '取消',
    onPositiveClick() {
      messages.value.splice(index, 1)
    },
  })
}

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

const selectProduct = (product: ProductOption) => {
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

const loadProductOptions = async () => {
  loadingProductOptions.value = true
  try {
    const res: any = await getAvailableProducts()
    productOptions.value = Array.isArray(res) ? res : (res.data || [])
  } catch (error) {
    console.error('获取商品列表失败', error)
    productOptions.value = []
    message.error('获取商品列表失败')
  } finally {
    loadingProductOptions.value = false
  }
}

const getStatusType = (status: string): "default" | "success" | "warning" | "error" | "info" => {
  const map: Record<string, "default" | "success" | "warning" | "error" | "info"> = {
    delivered: 'success',
    shipped: 'info',
    processing: 'warning',
    pending: 'error',
    '已签收': 'success',
    '已发货': 'info',
    '处理中': 'warning',
    '待付款': 'error',
  }
  return map[status] || 'default'
}

const scrollToBottom = () => {
  nextTick(() => {
    if (scrollContainerRef.value) {
      scrollContainerRef.value.scrollTop = scrollContainerRef.value.scrollHeight
    }
  })
}

let scrollRafPending = false
const scheduleScrollToBottom = () => {
  if (scrollRafPending) return
  scrollRafPending = true
  requestAnimationFrame(() => {
    scrollRafPending = false
    scrollToBottom()
  })
}

const handleScroll = (e: Event) => {
  const target = e.target as HTMLElement
  const isNearBottom = target.scrollHeight - target.scrollTop - target.clientHeight < 100
  showScrollToBottom.value = !isNearBottom
  if (target.scrollTop < 80) {
    loadMoreHistory()
  }
}

const fetchMessages = async () => {
  if (!conversationId.value) return
  isLoading.value = true
  try {
    const res: any = await getMessagesHistory(conversationId.value, undefined, 30)
    const payload = res.data || res
    const items = payload.items || []
    messages.value = items.map((msg: any) => normalizeMessage(msg))
    historyHasMore.value = !!payload.has_more
    historyCursor.value = payload.next_before_id || null
    scheduleScrollToBottom()
  } catch (error) {
    console.error(error)
    // 向后兼容旧接口
    try {
      const fallbackRes: any = await getMessages(conversationId.value)
      const fallbackItems = Array.isArray(fallbackRes) ? fallbackRes : (fallbackRes.data || [])
      messages.value = fallbackItems.map((msg: any) => normalizeMessage(msg))
      historyHasMore.value = false
      historyCursor.value = null
      scheduleScrollToBottom()
    } catch (fallbackError) {
      console.error(fallbackError)
    }
  } finally {
    isLoading.value = false
  }
}

const loadMoreHistory = async () => {
  if (!conversationId.value || !historyHasMore.value || historyLoading.value || !historyCursor.value) return
  if (!scrollContainerRef.value) return

  historyLoading.value = true
  const container = scrollContainerRef.value
  const previousHeight = container.scrollHeight

  try {
    const res: any = await getMessagesHistory(conversationId.value, historyCursor.value, 30)
    const payload = res.data || res
    const olderItems = (payload.items || []).map((msg: any) => normalizeMessage(msg))
    const existingIds = new Set(messages.value.map((msg: any) => msg.id))
    const deduped = olderItems.filter((msg: any) => !existingIds.has(msg.id))
    if (deduped.length > 0) {
      messages.value = [...deduped, ...messages.value]
      await nextTick()
      const newHeight = container.scrollHeight
      container.scrollTop = container.scrollTop + (newHeight - previousHeight)
    }
    historyHasMore.value = !!payload.has_more
    historyCursor.value = payload.next_before_id || null
  } catch (error) {
    console.error(error)
  } finally {
    historyLoading.value = false
  }
}

// 监听路由变化
watch(() => route.params.id, async (newId) => {
  if (newId && typeof newId === 'string') {
    if (newId === conversationId.value && messages.value.length > 0) return
    conversationId.value = newId
    historyHasMore.value = false
    historyCursor.value = null
    isLoading.value = true
    await fetchMessages()
    // 加载完成后根据消息数量决定是否显示欢迎语
    showWelcome.value = messages.value.length === 0
  } else {
    // 仅在非发送状态时清空（避免新对话发送中被清空）
    if (!sending.value) {
      messages.value = []
      conversationId.value = ''
      historyHasMore.value = false
      historyCursor.value = null
      showWelcome.value = true
    }
  }
  // 任意路由变化都刷新一次会话列表
  fetchConversationList()
})

interface SendOptions {
  content?: string
  attachments?: AttachmentItem[]
  skipUserEcho?: boolean
}

const handleSend = async (options: SendOptions = {}) => {
  const content = (options.content ?? inputValue.value).trim()
  const attachments = options.attachments ?? (pendingAttachments.value.length > 0 ? [...pendingAttachments.value] : undefined)
  if (!content && (!attachments || attachments.length === 0)) return

  if (!userStore.token) {
    message.warning('请先登录后再发送消息')
    router.push('/login')
    return
  }

  if (sending.value) return

  if (!options.skipUserEcho) {
    messages.value.push({
      role: 'user',
      content: content || '[附件]',
      attachments,
      created_at: new Date().toISOString(),
    })
  }

  inputValue.value = ''
  pendingAttachments.value = []
  scheduleScrollToBottom()
  sending.value = true

  const aiMessage = {
    role: 'assistant',
    content: '',
    loading: true,
    thinkingSteps: [] as { step: string; content?: string }[],
    thinkingDone: false,
    actionButtonPrompt: '',
    actionButtons: [] as { type: string; label: string; action: string; style?: string; order_id?: string; product?: string; status?: string; amount?: string; disabled?: boolean }[],
    structuredBlocks: [] as StructuredBlock[],
    renderedHtml: '',
    metrics: {} as Record<string, any>,
    created_at: new Date().toISOString(),
  }
  messages.value.push(aiMessage)
  const aiMessageIndex = messages.value.length - 1
  activeAiMessageIndex.value = aiMessageIndex

  let streamConversationId = conversationId.value || ''
  let pendingChunkText = ''
  let flushTimer: ReturnType<typeof setTimeout> | null = null
  let streamDone = false

  const flushChunkBuffer = () => {
    if (!pendingChunkText) return
    messages.value[aiMessageIndex].content += pendingChunkText
    pendingChunkText = ''
    scheduleScrollToBottom()
  }

  const scheduleChunkFlush = () => {
    if (flushTimer) return
    flushTimer = setTimeout(() => {
      flushTimer = null
      flushChunkBuffer()
    }, 24)
  }

  const signal = streamController.begin({
    content,
    attachments,
    conversationId: streamConversationId,
    webSearch: webSearchEnabled.value,
    personaStyle: selectedPersona.value,
  })

  try {
    const body: any = {
      message: content || '[用户发送了附件]',
      web_search: webSearchEnabled.value,
      persona_style: selectedPersona.value,
    }
    if (streamConversationId) {
      body.conversation_id = streamConversationId
    }
    if (attachments) {
      body.attachments = attachments
    }

    const response = await fetch(`/api/v1/chat/stream`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${userStore.token}`,
      },
      body: JSON.stringify(body),
      signal,
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
        if (!line.startsWith('data: ')) continue
        const dataStr = line.slice(6).trim()
        if (!dataStr || dataStr === '[DONE]') continue

        try {
          const data = JSON.parse(dataStr)

          if (data.type === 'meta') {
            if (data.conversation_id) {
              streamConversationId = data.conversation_id
              if (conversationId.value !== streamConversationId) {
                conversationId.value = streamConversationId
                router.replace(`/chat/${streamConversationId}`)
                void fetchConversationList()
              }
            }
            if (data.metrics) {
              messages.value[aiMessageIndex].metrics = data.metrics
            }
          } else if (data.type === 'thinking' || data.type === 'tool_call') {
            messages.value[aiMessageIndex].thinkingSteps.push({
              step: data.step || (data.type === 'thinking' ? '思考中...' : '调用工具...'),
              content: data.content || '',
            })
            scheduleScrollToBottom()
          } else if (data.type === 'chunk' && data.content) {
            if (!messages.value[aiMessageIndex].thinkingDone) {
              messages.value[aiMessageIndex].thinkingDone = true
            }
            pendingChunkText += data.content
            scheduleChunkFlush()
          } else if (data.type === 'done') {
            streamDone = true
            if (data.message_id) {
              messages.value[aiMessageIndex].message_id = data.message_id
            }
          } else if (data.type === 'action_buttons' && data.actions) {
            if (data.content) {
              messages.value[aiMessageIndex].actionButtonPrompt = data.content
            }
            const actions = data.actions.map((a: any) => ({ ...a, disabled: false }))
            messages.value[aiMessageIndex].actionButtons.push(...actions)
            scheduleScrollToBottom()
          } else if (data.type === 'error') {
            messages.value[aiMessageIndex].content = `错误: ${data.error || '未知错误'}`
          }
        } catch {
          // Ignore unparseable SSE line
        }
      }
    }
  } catch (error: any) {
    console.error(error)
    if (error?.name === 'AbortError') {
      if (networkOffline.value) {
        streamController.offline('网络连接中断，当前回复已停止。')
        messages.value[aiMessageIndex].content = messages.value[aiMessageIndex].content || '网络中断，响应已停止。可点击“重试上一条”。'
      } else {
        messages.value[aiMessageIndex].content = messages.value[aiMessageIndex].content || '已停止生成。你可以继续提问或重试上一条。'
      }
    } else {
      const errorMsg = error.message || '发送消息失败'
      if (networkOffline.value || !navigator.onLine) {
        streamController.offline('网络连接异常，建议点击“重试上一条”。')
      } else {
        streamController.fail(errorMsg)
      }
      message.error(errorMsg)
      messages.value[aiMessageIndex].content = '抱歉，消息发送失败，请稍后重试。'
    }
  } finally {
    if (flushTimer) {
      clearTimeout(flushTimer)
      flushTimer = null
    }
    flushChunkBuffer()

    messages.value[aiMessageIndex].loading = false
    messages.value[aiMessageIndex].thinkingDone = true
    finalizeAssistantMessage(messages.value[aiMessageIndex])

    if (!streamDone && !messages.value[aiMessageIndex].content) {
      if (streamController.state.value === 'offline') {
        messages.value[aiMessageIndex].content = '网络连接中断，回答未完成，请重试。'
      } else if (streamController.state.value === 'stopped') {
        messages.value[aiMessageIndex].content = '回答已停止生成，可点击重试继续。'
      } else {
        messages.value[aiMessageIndex].content = '抱歉，本次响应未完整返回，请重试。'
      }
    }

    if (streamDone && streamController.state.value === 'streaming') {
      streamController.finish()
    }

    sending.value = false
    activeAiMessageIndex.value = null
    scheduleScrollToBottom()
    showWelcome.value = false

    void fetchConversationList()
    emit('refresh')
  }
}

const handleStopGenerating = () => {
  if (!sending.value) return
  const stopped = streamController.stop()
  if (stopped) {
    message.info('已停止生成')
  }
}

const handleRetryLastRequest = async () => {
  const lastRequest = streamController.lastRequest.value
  if (!lastRequest || sending.value) return
  await handleSend({
    content: lastRequest.content,
    attachments: lastRequest.attachments as AttachmentItem[] | undefined,
  })
}

const handleRecoverConversation = () => {
  streamController.clearNotice()
  message.success('会话已恢复，可继续提问')
}

const dismissStreamRecovery = () => {
  if (networkOffline.value) {
    dismissOfflineNotice.value = true
    return
  }
  if (sending.value) return
  streamController.clearNotice()
}
const userName = computed(() => userStore.user?.name || '用户')

// 处理交互按钮点击（退货订单选择、确认取消）
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
const handlePlusCommand = async (key: string) => {
  if (key === 'file') handleFileSelect()
  else if (key === 'order') {
    showOrderDrawer.value = true
    await loadOrderOptions()
  } else if (key === 'product') {
    showProductDrawer.value = true
    await loadProductOptions()
  }
}

const openImagePreview = (url: string) => {
  window.open(url, '_blank')
}

const onNetworkOffline = () => {
  networkOffline.value = true
  dismissOfflineNotice.value = false
  if (!sending.value) {
    streamController.offline('当前网络不可用，恢复后可重试上一条消息。')
    return
  }
  if (streamController.canStop.value) {
    streamController.stop()
  }
  streamController.offline('网络连接中断，当前回复已停止。')
  message.warning('网络连接已断开，已暂停本次生成')
}

const onNetworkOnline = () => {
  networkOffline.value = false
  dismissOfflineNotice.value = false
  if (streamController.state.value === 'offline') {
    message.success('网络已恢复，你可以重试上一条或继续会话')
  }
}

let resizeObserver: ResizeObserver | null = null

onMounted(async () => {
  window.addEventListener('offline', onNetworkOffline)
  window.addEventListener('online', onNetworkOnline)

  fetchConversationList()
  if (route.params.id && typeof route.params.id === 'string') {
    conversationId.value = route.params.id
    isLoading.value = true
    await fetchMessages()
    // 加载完成后，如果没有消息则显示欢迎语
    showWelcome.value = messages.value.length === 0
  } else {
    // 新会话
    showWelcome.value = true
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
  window.removeEventListener('offline', onNetworkOffline)
  window.removeEventListener('online', onNetworkOnline)
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
    <!-- 侧边栏（Gemini 布局） -->
    <div class="sidebar-wrapper" :class="{ 'is-collapsed': !isSidebarOpen }">
      <div class="sidebar-header" :class="{ 'sidebar-header-compact': !isSidebarOpen }">
        <div class="menu-btn" :class="{ 'menu-btn-compact': !isSidebarOpen }" @click="toggleSidebar">
          <n-icon :size="20"><MenuOutline /></n-icon>
        </div>
        <div class="menu-btn search-menu-btn" :class="{ 'menu-btn-compact': !isSidebarOpen }" title="搜索" @click="router.push('/search')">
          <n-icon :size="18"><SearchOutline /></n-icon>
        </div>
      </div>
      
      <div class="sidebar-content" v-show="isSidebarOpen">
        <div class="sidebar-pattern"></div>
        
        <!-- Fixed Top Section inside scrollable content area -->
        <div class="sidebar-top-section">
          <!-- 第一个大按钮 -->
          <div class="new-chat-btn new-chat-btn-shift" @click="handleNewChat">
            <n-icon :size="18"><CreateOutline /></n-icon>
            <span>新建会话</span>
          </div>
          <div class="new-chat-btn new-chat-btn-shift batch-toggle-btn" @click="toggleBatchMode">
            <n-icon :size="18"><TrashOutline /></n-icon>
            <span>{{ batchMode ? '取消批删' : '批量删除' }}</span>
          </div>
          
          <div class="sidebar-menu-header">
            <span>会话列表</span>
            <span v-if="batchMode" class="batch-counter">已选 {{ selectedConversationIds.length }}</span>
          </div>
        </div>
        
        <!-- Scrollable Section -->
        <div class="chat-history-container ds-scrollbar">
          <div class="chat-history-list">
            <div
              v-for="convo in conversations"
              :key="convo.id"
              class="history-item"
              :class="{ active: convo.id === conversationId }"
              @click="batchMode ? toggleConversationSelect(convo.id) : handleSelectChat(convo.id)"
            >
              <n-checkbox
                v-if="batchMode"
                :checked="selectedConversationIds.includes(convo.id)"
                @update:checked="() => toggleConversationSelect(convo.id)"
                @click.stop
              />
              <n-icon v-if="convo.is_pinned" :size="14" class="history-pin">
                <PinOutline />
              </n-icon>
              <span class="history-title">{{ convo.title || '新会话' }}</span>
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
          <div v-if="batchMode" class="batch-action-bar">
            <button class="pill rename-save-btn" @click="handleBatchDelete">删除选中</button>
            <button class="pill" @click="toggleBatchMode">取消</button>
          </div>
        </div>
        
        <!-- Bottom Settings & Avatar -->
        <div class="sidebar-bottom">
          <div class="sidebar-menu-item sidebar-profile-item">
            <n-avatar round :size="24" class="user-avatar user-avatar-pill">{{ userName.slice(0, 1) }}</n-avatar>
            <span class="sidebar-user-name">{{ userName }}</span>
          </div>

          <n-dropdown :options="settingsOptions" placement="top-start" @select="handleSettingsSelect">
            <div class="sidebar-menu-item">
              <n-icon :size="18" class="icon"><SettingsOutline /></n-icon>
              <span>设置与帮助</span>
            </div>
          </n-dropdown>
        </div>
      </div>
    </div>

    <!-- 主聊天区 -->
    <div class="chat-container">
      <!-- 椤堕儴 Header: Hamburger toggle when sidebar is closed, Gemini logo -->
      <div class="top-nav">
        <div class="nav-left">
          <span class="gemini-logo">AI 客服助手</span>
        </div>
      </div>

      <!-- Hidden file inputs -->
      <input ref="imageInputRef" type="file" accept="image/*" multiple style="display:none" @change="onImageChange" />
      <input ref="fileInputRef" type="file" accept=".pdf,.doc,.docx,.xls,.xlsx,.txt,.csv" multiple style="display:none" @change="onFileChange" />

    <!-- 消息列表区域 -->
    <div ref="scrollContainerRef" class="chat-area ds-scrollbar" @scroll="handleScroll">
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

            <div class="message-content-wrapper" :class="{ 'message-content-wrapper-user': msg.role === 'user' }">
              <div class="message-heading" v-if="msg.role === 'assistant'">
                <span class="sender-name">客服小鹏</span>
              </div>
              <div class="message-bubble">
                <div v-if="msg.attachments && msg.attachments.length > 0" class="msg-attachments">
                  <AttachmentItemCard
                    v-for="(att, ai) in msg.attachments"
                    :key="`${index}-${ai}`"
                    :item="att"
                    mode="message"
                    @open="openImagePreview"
                  />
                </div>
                <!-- 思考过程（可折叠） -->
                <div v-if="msg.thinkingSteps && msg.thinkingSteps.length > 0" class="thinking-section" :class="{ collapsed: msg.thinkingDone }">
                  <details :open="!msg.thinkingDone">
                    <summary class="thinking-summary">
                      <span class="thinking-label">{{ msg.thinkingDone ? '分析完成' : '分析中...' }}</span>
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
                <!-- Message content -->
                <div v-if="msg.content && msg.loading" class="message-content streaming-content">{{ msg.content }}</div>
                <div v-else-if="msg.content && msg.structuredBlocks && msg.structuredBlocks.length > 0" class="structured-response">
                  <div
                    v-for="(block, bi) in msg.structuredBlocks"
                    :key="`${index}-${bi}`"
                    class="response-card"
                    :class="`kind-${block.kind}`"
                  >
                    <div class="card-title">{{ block.title }}</div>
                    <ul v-if="block.items && block.items.length > 0" class="card-list">
                      <li v-for="(item, ii) in block.items" :key="ii">{{ item }}</li>
                    </ul>
                    <div v-if="block.metrics && block.metrics.length > 0" class="metric-grid">
                      <div v-for="(metric, mi) in block.metrics" :key="mi" class="metric-item">
                        <span class="metric-label">{{ metric.label }}</span>
                        <span class="metric-value">{{ metric.value }}</span>
                      </div>
                    </div>
                  </div>
                </div>
                <div
                  v-else-if="msg.content"
                  class="message-content"
                  v-html="msg.renderedHtml || renderMarkdown(msg.content)"
                ></div>
                <!-- 交互按钮区域（退货订单选择 / 确认取消） -->
                <div v-if="msg.actionButtons && msg.actionButtons.length > 0" class="action-buttons-area">
                  <div v-if="msg.actionButtonPrompt" class="action-buttons-prompt">
                    {{ msg.actionButtonPrompt }}
                  </div>
                  <template v-for="(btn, bi) in msg.actionButtons" :key="bi">
                    <!-- 订单选择卡片 -->
                    <div v-if="btn.type === 'order_card'" class="action-order-card" :class="{ disabled: btn.disabled }" @click="handleActionClick(btn, index)">
                      <div class="action-order-info">
                        <span class="action-order-product">{{ btn.product }}</span>
                        <span class="action-order-id">{{ btn.order_id }}</span>
                      </div>
                      <div class="action-order-meta">
                        <n-tag :type="getStatusType(btn.status || '')" size="small" round>{{ btn.status }}</n-tag>
                        <span class="action-order-amount" v-if="btn.amount">¥{{ btn.amount }}</span>
                      </div>
                      <div class="action-order-btn-label">{{ btn.disabled ? '已选中，正在继续...' : '点击选择该订单' }}</div>
                    </div>
                    <!-- 确认 / 取消按钮 -->
                    <button v-else class="action-btn" :class="[btn.style || 'default', { disabled: btn.disabled }]" :disabled="btn.disabled" @click="handleActionClick(btn, index)">
                      {{ btn.label }}
                    </button>
                  </template>
                </div>
                <MessageActionBar
                  v-if="!msg.loading"
                  align="left"
                  :actions="[
                    { key: 'copy', title: '复制', icon: CopyOutline },
                    { key: 'feedback', title: '反馈', icon: ChatboxEllipsesOutline },
                    { key: 'retry', title: '重新生成', icon: RefreshOutline },
                    { key: 'delete', title: '删除', icon: TrashOutline }
                  ]"
                  @trigger="(key) => {
                    if (key === 'copy') copyMessage(msg.content)
                    else if (key === 'feedback') openFeedbackForMessage(msg)
                    else if (key === 'retry') regenerateMessage(index)
                    else if (key === 'delete') deleteMessage(index)
                  }"
                />
              </div>
            </div>

            <!-- Avatar for User -->
            <div class="message-avatar" v-if="msg.role === 'user'">
              <n-avatar :size="30" round class="user-avatar user-avatar-pill">{{ userName.slice(0, 1) }}</n-avatar>
            </div>

            <MessageActionBar
              v-if="msg.role === 'user'"
              align="right"
              :actions="[
                { key: 'edit', title: '编辑并重发', icon: PencilOutline },
                { key: 'delete', title: '删除', icon: TrashOutline }
              ]"
              @trigger="(key) => {
                if (key === 'edit') editMessage(index)
                else if (key === 'delete') deleteMessage(index)
              }"
            />
          </div>
        </template>

        <!-- 欢迎语（当没有消息时显示在消息区域中间） -->
        <div v-if="showWelcome && messages.length === 0" class="greeting-container">
          <div class="greeting-hi"><span class="gradient-star">✨</span> 你好，{{ userName }}</div>
          <div class="greeting-sub">有什么我可以帮助你的？</div>
        </div>

        <!-- 快捷短语（当没有消息时显示） -->
        <div class="suggestion-pills" v-if="showWelcome && messages.length === 0">
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
      </div>

      <!-- Scroll to bottom button -->
      <Transition name="fade">
        <div v-if="showScrollToBottom" class="scroll-bottom-btn" @click="scrollToBottom">
          <n-icon :size="20"><ArrowDownOutline /></n-icon>
        </div>
      </Transition>
    </div>

    <!-- 输入区域 -->
    <div class="input-area">
      <!-- 待发送附件预览 -->
      <Transition name="slide-up">
        <div v-if="pendingAttachments.length > 0" class="pending-attachments">
          <TransitionGroup name="att-item">
            <AttachmentItemCard
              v-for="(att, idx) in pendingAttachments"
              :key="`${att.type}-${idx}`"
              class="pending-item"
              :item="att"
              mode="pending"
              removable
              @remove="removeAttachment(idx)"
              @open="openImagePreview"
            />
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
          placeholder="请输入你的问题"
          :bordered="false"
          class="chat-input"
          @keydown.enter.exact.prevent="handleSend"
        />
        
        <div class="input-actions">
          <div class="tool-btn" v-if="!inputValue && pendingAttachments.length === 0">
            <n-icon :size="20"><MicOutline /></n-icon>
          </div>
          <button
            v-if="sending"
            type="button"
            class="stop-btn"
            @click="handleStopGenerating"
          >
            停止生成
          </button>
          <Transition name="scale">
            <div
              v-if="!sending && (inputValue || pendingAttachments.length > 0)"
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
            <span>风格: {{ personaOptions.find(o => o.key === selectedPersona)?.label || '默认' }}</span>
          </div>
        </n-dropdown>
      </div>

      <StreamStatusCard
        v-if="showStreamRecovery"
        :state="networkOffline ? 'offline' : streamController.state.value"
        :reason="streamController.reason.value || (networkOffline ? '网络不可用，恢复后可重试上一条消息。' : '')"
        :can-retry="!!streamController.lastRequest.value && !sending"
        @retry="handleRetryLastRequest"
        @recover="handleRecoverConversation"
        @dismiss="dismissStreamRecovery"
      />
      
      <div class="disclaimer">客服小鹏可能会产生不准确的信息，请核实重要内容。</div>
    </div>

    <!-- 订单选择抽屉 -->
    <n-drawer v-model:show="showOrderDrawer" :width="400" placement="right">
      <n-drawer-content title="选择订单">
        <div class="drawer-list">
          <div v-if="loadingOrderOptions" class="drawer-empty-state">正在加载订单数据...</div>
          <div v-else-if="orderOptions.length === 0" class="drawer-empty-state">暂无可选订单数据</div>
          <div v-for="order in orderOptions" v-else :key="order.order_id" class="drawer-item" @click="selectOrder(order)">
            <div class="drawer-item-top">
              <span class="drawer-item-name">{{ order.name }}</span>
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

    <!-- 商品选择抽屉 -->
    <n-drawer v-model:show="showProductDrawer" :width="400" placement="right">
      <n-drawer-content title="选择商品">
        <div class="drawer-list">
          <div v-if="loadingProductOptions" class="drawer-empty-state">正在加载商品数据...</div>
          <div v-else-if="productOptions.length === 0" class="drawer-empty-state">暂无可选商品数据</div>
          <div v-for="product in productOptions" v-else :key="product.product_id" class="drawer-item" @click="selectProduct(product)">
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

    <!-- 閲嶅懡鍚?Modal -->
    <n-modal v-model:show="showRenameModal" preset="dialog" title="重命名会话">
      <div class="rename-input-wrap">
        <n-input v-model:value="renameTitle" placeholder="请输入新的会话标题" @keydown.enter="submitRename" />
      </div>
      <template #action>
        <div class="rename-actions">
          <button class="pill" @click="showRenameModal = false">取消</button>
          <button class="pill rename-save-btn" @click="submitRename">保存</button>
        </div>
      </template>
    </n-modal>

    <n-modal v-model:show="showFeedbackModal" preset="dialog" title="提交反馈">
      <div class="feedback-form">
        <div class="feedback-label">满意度评分</div>
        <n-rate v-model:value="feedbackRating" />
        <div class="feedback-label mt-3">补充说明（可选）</div>
        <n-input
          v-model:value="feedbackComment"
          type="textarea"
          :autosize="{ minRows: 3, maxRows: 5 }"
          placeholder="请告诉我们哪里可以做得更好"
        />
      </div>
      <template #action>
        <div class="rename-actions">
          <button class="pill" @click="showFeedbackModal = false">取消</button>
          <button class="pill rename-save-btn" @click="submitFeedback">提交</button>
        </div>
      </template>
    </n-modal>
  </div>
  </div>
</template>

<style scoped>
/* App Layout Container */


.app-layout {
  --bg-color: var(--ds-bg-page);
  --surface-color: var(--ds-bg-surface);
  --text-primary: var(--ds-text-primary);
  --text-secondary: var(--ds-text-secondary);
  --text-tertiary: var(--ds-text-tertiary);
  --surface-hover: var(--ds-bg-elevated);
  --active-bg: var(--ds-brand-soft);
  --active-text: var(--ds-brand-hover);
  --hover-dark: #d8e2f9;
  --primary-color: var(--ds-brand);

  display: flex;
  height: 100vh;
  width: 100vw;
  overflow: hidden;
  background-color: var(--bg-color);
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

.sidebar-header-compact {
  flex-direction: column;
  gap: 12px;
  align-items: center;
  padding: 16px 0;
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

.search-menu-btn {
  margin-left: 4px;
}

.menu-btn-compact {
  margin: 0;
}

.sidebar-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  padding: 0 16px 16px 16px;
  overflow: hidden; /* Prevent sidebar itself from scrolling */
  position: relative;
}

.sidebar-pattern {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  opacity: 0.03;
  pointer-events: none;
  background-image: radial-gradient(var(--ds-brand) 0.5px, transparent 0.5px);
  background-size: 10px 10px;
  z-index: 0;
}

.sidebar-top-section {
  position: relative;
  z-index: 1;
  flex-shrink: 0;
}

.chat-history-container {
  flex: 1;
  overflow-y: auto;
  margin: 0 -8px;
  padding: 0 8px;
  position: relative;
  z-index: 1;
}

.chat-history-container::-webkit-scrollbar {
  width: 4px;
}
.chat-history-container::-webkit-scrollbar-thumb {
  background: rgba(0, 0, 0, 0.1);
  border-radius: 10px;
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
  border-top: 1px solid rgba(0, 0, 0, 0.05);
  position: relative;
  z-index: 1;
  background-color: var(--bg-color); /* Ensure it's opaque over scrolling content if needed */
}

/* ===== 主聊天区 ===== */
.chat-container {
  display: flex;
  flex-direction: column;
  flex: 1;
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
  color: var(--ds-brand-hover);
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
  background-color: #7b4fff;
  color: white;
  font-weight: 500;
  font-size: 16px;
  cursor: pointer;
}

.chat-area {
  flex: 1;
  min-height: 0;
  width: 100%;
  overflow-y: auto;
  scroll-behavior: smooth;
}

.messages-wrapper {
  padding: 40px 0 60px;
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
  justify-content: center;
  margin: 20vh auto 0;
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
  background: linear-gradient(90deg, #4285F4, #7b4fff, #D96570);
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
  width: 90%;
  max-width: 800px;
  margin: 24px auto 8px;
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
  background: linear-gradient(135deg, #4285f4, #7b4fff);
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

.streaming-content {
  white-space: pre-wrap;
  background: linear-gradient(180deg, #f9fbff, #f4f7ff);
  border: 1px solid #e7eefc;
  border-radius: 14px;
  padding: 12px 14px;
}

.structured-response {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-top: 2px;
}

.response-card {
  border-radius: 14px;
  border: 1px solid #e6e9ef;
  background: linear-gradient(180deg, #ffffff 0%, #f8fafc 100%);
  padding: 12px 14px;
}

.response-card.kind-conclusion {
  border-left: 4px solid var(--ds-brand);
}

.response-card.kind-steps {
  border-left: 4px solid #0f9d58;
}

.response-card.kind-tips {
  border-left: 4px solid #f29900;
}

.response-card.kind-data {
  border-left: 4px solid #6f42c1;
}

.card-title {
  font-size: 13px;
  letter-spacing: 0.02em;
  text-transform: uppercase;
  font-weight: 700;
  color: var(--text-secondary);
  margin-bottom: 8px;
}

.card-list {
  margin: 0;
  padding-left: 20px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.card-list li {
  color: var(--text-primary);
  line-height: 1.65;
}

.metric-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;
}

.metric-item {
  display: flex;
  flex-direction: column;
  background: #f5f8ff;
  border: 1px solid #e0e8ff;
  border-radius: 10px;
  padding: 8px 10px;
}

.metric-label {
  font-size: 11px;
  color: var(--text-tertiary);
}

.metric-value {
  margin-top: 2px;
  font-size: 14px;
  font-weight: 600;
  color: var(--ds-brand-hover);
}

@media (max-width: 768px) {
  .metric-grid {
    grid-template-columns: 1fr;
  }
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
  background: linear-gradient(135deg, #4285f4, #7b4fff);
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
  color: var(--ds-brand);
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
  animation: scaleIn 0.2s ease;
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
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  z-index: 100;
  background: var(--surface-color);
  padding-bottom: 24px;
  transition: all 0.5s cubic-bezier(0.4, 0, 0.2, 1);
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
  background: linear-gradient(135deg, #4285f4, var(--ds-brand));
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
  color: var(--ds-brand);
  border-color: #d2e3fc;
}

.web-search-toggle.active n-icon {
  color: var(--ds-brand);
}

.persona-icon {
  font-size: 14px;
}

/* ===== 抽屉样式 ===== */
.drawer-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.drawer-empty-state {
  padding: 28px 16px;
  border-radius: 12px;
  text-align: center;
  color: var(--text-tertiary);
  background: var(--surface-color);
  border: 1px dashed #d9d9d9;
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
  border-image: linear-gradient(180deg, #4285F4, #7b4fff) 1;
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

.action-buttons-prompt {
  width: 100%;
  font-size: 13px;
  line-height: 1.6;
  color: var(--text-secondary);
  margin-bottom: 2px;
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
  border-color: var(--ds-brand);
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
  color: var(--ds-brand);
}
.action-order-btn-label {
  font-size: 12px;
  color: var(--ds-brand);
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
  background: linear-gradient(135deg, var(--ds-brand) 0%, var(--ds-brand-hover) 100%);
  color: white;
  border-color: transparent;
}
.action-btn.primary:hover:not(.disabled) {
  background: linear-gradient(135deg, var(--ds-brand-hover) 0%, #536dfe 100%);
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
  border: 4px dashed var(--ds-brand);
  border-radius: 16px;
}

.drag-overlay-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
  color: var(--ds-brand);
  font-size: 20px;
  font-weight: 500;
  pointer-events: none;
}

.new-chat-btn-shift {
  margin-left: -4px;
}

.sidebar-profile-item {
  padding-left: 8px;
}

.sidebar-user-name {
  font-weight: 500;
  color: var(--text-primary);
}

.user-avatar-pill {
  background: linear-gradient(135deg, #4e75ff, #7b4fff);
  color: #fff;
  font-weight: 700;
}

.message-content-wrapper-user {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
}

.stop-btn {
  border: none;
  border-radius: 999px;
  padding: 9px 14px;
  font-size: 13px;
  font-weight: 600;
  color: #fff;
  background: linear-gradient(135deg, #f29900, #ff7a59);
  cursor: pointer;
}

.stop-btn:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(242, 153, 0, 0.35);
}

.rename-input-wrap {
  margin-top: 16px;
}

.rename-actions {
  display: flex;
  gap: 12px;
}

.rename-save-btn {
  background: var(--ds-brand);
  color: #fff;
}

.batch-toggle-btn {
  margin-top: 8px;
}

.batch-counter {
  margin-left: auto;
  font-size: 12px;
  color: var(--text-tertiary);
}

.history-pin {
  color: var(--ds-brand);
  margin-right: 4px;
}

.batch-action-bar {
  display: flex;
  gap: 8px;
  padding: 8px 6px 0;
}

.feedback-form {
  margin-top: 10px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.feedback-label {
  font-size: 13px;
  color: var(--text-secondary);
  font-weight: 600;
}

/* ===== 回到底部按钮 ===== */
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
  color: var(--ds-brand);
  transform: translateX(-50%) translateY(-2px);
  box-shadow: 0 6px 16px rgba(0, 0, 0, 0.12);
}
</style>

